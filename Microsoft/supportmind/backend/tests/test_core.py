import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.security import hash_password
from app.services.seed import seed_demo_data


class SafeFixtureData(dict):
    def __repr__(self):
        return '<redacted test fixture data>'


@pytest.fixture
def client(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'JWT_SECRET', 'test-only-jwt-secret')
    monkeypatch.setattr(settings, 'ADMIN_EMAIL', '')
    monkeypatch.setattr(settings, 'ADMIN_PASSWORD', '')
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestingSession() as db:
        seed_demo_data(db)
        db.add(User(
            name='Test Admin',
            email='test@supportmind.local',
            password_hash=hash_password('test-only-password'),
            role='ADMIN',
        ))
        db.commit()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def auth_headers(client):
    response = client.post(
        '/api/auth/login',
        json={'email': 'test@supportmind.local', 'password': 'test-only-password'},
    )
    assert response.status_code == 200
    return SafeFixtureData(Authorization=f"Bearer {response.json()['access_token']}")


@pytest.fixture
def hindsight_cloud(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'HINDSIGHT_URL', 'https://hindsight.invalid')
    monkeypatch.setattr(settings, 'HINDSIGHT_API_KEY', 'test-only-key')
    stored_items = []
    requests = []

    def post(url, json=None, headers=None, timeout=None):
        requests.append({'url': url, 'payload': json, 'headers': headers})
        if url.endswith('/memories'):
            stored_items.extend(json['items'])
            result = {'accepted': len(json['items'])}
        elif url.endswith('/memories/recall'):
            tag = json['tags'][0]
            assert json['tags_match'] == 'exact'
            results = [
                {
                    'id': f'memory-{index}',
                    'type': 'experience',
                    'text': item['content'],
                    'context': item['context'],
                    'mentioned_at': item['timestamp'],
                    'score': 0.87,
                }
                for index, item in enumerate(stored_items)
                if tag in item['tags']
            ]
            result = {'results': results}
        else:
            raise AssertionError(f'Unexpected Hindsight endpoint: {url}')
        return httpx.Response(200, json=result, request=httpx.Request('POST', url))

    monkeypatch.setattr('app.services.hindsight.httpx.post', post)
    return SafeFixtureData(requests=requests, stored_items=stored_items)


def test_health_login_and_real_customers(client, auth_headers):
    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.json()['backend'] == 'ok'
    assert health.json()['database'] == 'ok'
    schema = client.get('/openapi.json').json()
    assert '/api/tickets' in schema['paths']
    assert '/api/analytics/dashboard' in schema['paths']

    customers = client.get('/api/customers', headers=auth_headers)
    assert customers.status_code == 200
    assert len(customers.json()) == 3
    customer_id = customers.json()[0]['id']
    detail = client.get(f'/api/customers/{customer_id}', headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()['external_customer_id']


def test_customer_memory_uses_hindsight_and_returns_real_shape(client, auth_headers, hindsight_cloud):
    customer = client.get('/api/customers', headers=auth_headers).json()[0]
    response = client.get(f"/api/customers/{customer['id']}/memory", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload['customer_id'] == customer['id']
    assert payload['customer']['name'] == customer['name']
    assert payload['memory_count'] == len(payload['memories']) == 0
    assert payload['hindsight_available'] is True
    assert hindsight_cloud['requests'][0]['url'].endswith('/memories/recall')


def test_hindsight_recall_caps_records_and_summary_size(client, auth_headers, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'HINDSIGHT_URL', 'https://hindsight.invalid')
    monkeypatch.setattr(settings, 'HINDSIGHT_API_KEY', 'test-only-key')
    long_text = 'Relevant customer history. ' * 100
    results = [{'id': f'memory-{index}', 'text': long_text, 'type': 'experience'} for index in range(12)]

    def mock_post(url, **kwargs):
        return httpx.Response(200, json={'results': results}, request=httpx.Request('POST', url))

    monkeypatch.setattr('app.services.hindsight.httpx.post', mock_post)
    customer = client.get('/api/customers', headers=auth_headers).json()[0]
    response = client.post(f"/api/memory/{customer['id']}/recall", headers=auth_headers, json={'query': 'relevant customer history'})
    assert response.status_code == 200
    assert response.json()['memory_count'] == 6
    assert all(len(memory['summary']) <= 1203 for memory in response.json()['memories'])


def test_hindsight_unavailable_is_not_reported_as_retained(client, auth_headers, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'HINDSIGHT_URL', '')
    monkeypatch.setattr(settings, 'HINDSIGHT_API_KEY', '')
    customer = client.get('/api/customers', headers=auth_headers).json()[0]
    retained = client.post(f"/api/memory/{customer['id']}/retain", headers=auth_headers, json={
        'summary': 'A real interaction that could not reach Hindsight.',
        'event_type': 'CHAT',
    })
    assert retained.status_code == 200
    assert retained.json()['hindsight_saved'] is False
    assert retained.json()['local_event_saved'] is True
    recalled = client.post(f"/api/memory/{customer['id']}/recall", headers=auth_headers, json={'query': 'previous support interaction'})
    assert recalled.json()['hindsight_available'] is False
    assert recalled.json()['memories'] == []


def test_ticket_list_filters_messages_and_customer_ownership(client, auth_headers):
    customers = client.get('/api/customers', headers=auth_headers).json()
    rahul_id, priya_id = [customer['id'] for customer in customers[:2]]
    created = client.post('/api/tickets', headers=auth_headers, json={
        'customer_id': rahul_id,
        'title': 'Connectivity drops after reconnect',
        'category': 'NETWORK',
        'priority': 'HIGH',
    })
    assert created.status_code == 200
    ticket_id = created.json()['id']

    listing = client.get('/api/tickets?status=open&priority=high', headers=auth_headers)
    assert listing.status_code == 200
    assert [ticket['id'] for ticket in listing.json()] == [ticket_id]
    assert client.get(f'/api/tickets/{ticket_id}', headers=auth_headers).json()['customer_id'] == rahul_id
    customer_tickets = client.get(f'/api/customers/{rahul_id}/tickets', headers=auth_headers)
    assert [ticket['id'] for ticket in customer_tickets.json()] == [ticket_id]

    message = client.post(f'/api/tickets/{ticket_id}/messages', headers=auth_headers, json={
        'customer_id': rahul_id,
        'sender_type': 'CUSTOMER',
        'content': 'A valid message for this ticket.',
    })
    assert message.status_code == 200
    assert client.get(f'/api/tickets/{ticket_id}/messages', headers=auth_headers).json()[0]['content'] == 'A valid message for this ticket.'

    mismatch = client.post(f'/api/tickets/{ticket_id}/messages', headers=auth_headers, json={
        'customer_id': priya_id,
        'sender_type': 'CUSTOMER',
        'content': 'This message belongs to a different customer.',
    })
    assert mismatch.status_code == 400
    assert client.get('/api/tickets/999999/messages', headers=auth_headers).status_code == 404

    updated = client.patch(f'/api/tickets/{ticket_id}', headers=auth_headers, json={'status': 'RESOLVED'})
    assert updated.status_code == 200
    assert updated.json()['status'] == 'RESOLVED'
    assert updated.json()['resolved_at'] is not None


def test_hindsight_customer_isolation_and_persistence(client, auth_headers, hindsight_cloud):
    customers = client.get('/api/customers', headers=auth_headers).json()
    rahul = next(customer for customer in customers if customer['external_customer_id'] == 'rahul-001')
    priya = next(customer for customer in customers if customer['external_customer_id'] == 'priya-002')
    detail = 'The customer reports intermittent reconnects; restarting the access point restored service.'

    retained = client.post(f"/api/memory/{rahul['id']}/retain", headers=auth_headers, json={
        'summary': detail,
        'event_type': 'CHAT',
    })
    assert retained.status_code == 200
    assert retained.json()['hindsight_saved'] is True

    rahul_recall = client.post(f"/api/memory/{rahul['id']}/recall", headers=auth_headers, json={'query': 'reconnect issue and what restored service'})
    priya_recall = client.post(f"/api/memory/{priya['id']}/recall", headers=auth_headers, json={'query': 'reconnect issue and what restored service'})
    assert rahul_recall.json()['hindsight_available'] is True
    assert detail in rahul_recall.json()['memories'][0]['summary']
    assert priya_recall.json()['memories'] == []
    assert hindsight_cloud['requests'][0]['url'].endswith('/memories')
    assert all('/v1/default/banks/' in item['url'] for item in hindsight_cloud['requests'])
    assert all(item['url'].endswith(('/memories', '/memories/recall')) for item in hindsight_cloud['requests'])


def test_reflect_returns_hindsight_context(client, auth_headers, hindsight_cloud):
    customer = client.get('/api/customers', headers=auth_headers).json()[0]
    client.post(f"/api/memory/{customer['id']}/retain", headers=auth_headers, json={
        'summary': 'A documented preference for concise troubleshooting steps.',
        'event_type': 'CHAT',
    })
    reflected = client.post(f"/api/memory/{customer['id']}/reflect", headers=auth_headers, json={'query': 'customer communication preference'})
    assert reflected.status_code == 200
    assert reflected.json()['hindsight_available'] is True
    assert 'concise troubleshooting' in reflected.json()['summary']


def test_agent_chat_persists_and_recalls_across_interactions(client, auth_headers, hindsight_cloud, monkeypatch):
    monkeypatch.setattr('app.services.llm.GroqProvider.generate', lambda self, system, prompt: 'A response grounded in the current support request.')
    customer = client.get('/api/customers', headers=auth_headers).json()[0]
    first = client.post('/api/agent/chat', headers=auth_headers, json={
        'customer_id': customer['id'],
        'message': 'The replacement adapter restored the connection after the first adapter failed.',
    })
    assert first.status_code == 200, first.text
    first_data = first.json()
    assert first_data['memory_retained'] is True

    second = client.post('/api/agent/chat', headers=auth_headers, json={
        'customer_id': customer['id'],
        'ticket_id': first_data['ticket_id'],
        'message': 'The connection dropped again; which adapter worked last time?',
    })
    assert second.status_code == 200, second.text
    second_data = second.json()
    assert second_data['memory_used'] is True
    assert second_data['memory_available'] is True
    assert second_data['memory_count'] >= 1
    assert 'replacement adapter restored' in second_data['memory_references'][0]
    assert len(hindsight_cloud['stored_items']) == 2
    assert len([request for request in hindsight_cloud['requests'] if request['url'].endswith('/memories/recall')]) == 2


def test_agent_rejects_ticket_owned_by_another_customer(client, auth_headers, monkeypatch):
    monkeypatch.setattr('app.services.llm.GroqProvider.generate', lambda self, system, prompt: 'Response')
    customers = client.get('/api/customers', headers=auth_headers).json()
    ticket = client.post('/api/tickets', headers=auth_headers, json={
        'customer_id': customers[0]['id'], 'title': 'Owned ticket', 'category': 'GENERAL', 'priority': 'LOW',
    }).json()
    response = client.post('/api/agent/chat', headers=auth_headers, json={
        'customer_id': customers[1]['id'], 'ticket_id': ticket['id'], 'message': 'Check this ticket.',
    })
    assert response.status_code == 404


def test_agent_reports_unavailable_provider_without_fabricated_response(client, auth_headers, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'GROQ_API_KEY', '')
    monkeypatch.setattr(settings, 'HINDSIGHT_URL', '')
    monkeypatch.setattr(settings, 'HINDSIGHT_API_KEY', '')
    customer = client.get('/api/customers', headers=auth_headers).json()[0]
    response = client.post('/api/agent/chat', headers=auth_headers, json={
        'customer_id': customer['id'],
        'message': 'A real question that needs the language model.',
    })
    assert response.status_code == 503
    assert 'temporarily unavailable' in response.json()['detail']


def test_agent_failure_still_returns_actual_hindsight_memory(client, auth_headers, hindsight_cloud, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'GROQ_API_KEY', '')
    customer = client.get('/api/customers', headers=auth_headers).json()[0]
    actual_memory = 'A previous modem restart restored this customer connection.'
    retained = client.post(f"/api/memory/{customer['id']}/retain", headers=auth_headers, json={
        'summary': actual_memory,
        'event_type': 'CHAT',
    })
    assert retained.json()['hindsight_saved'] is True

    response = client.post('/api/agent/chat', headers=auth_headers, json={
        'customer_id': customer['id'],
        'message': 'The connection failed again. What helped before?',
    })
    assert response.status_code == 503
    status = response.json()['memory_status']
    assert status['available'] is True
    assert status['used'] is True
    assert actual_memory in status['references'][0]


def test_dashboard_analytics_are_database_derived(client, auth_headers):
    customer_id = client.get('/api/customers', headers=auth_headers).json()[0]['id']
    client.post('/api/tickets', headers=auth_headers, json={
        'customer_id': customer_id, 'title': 'Measured ticket', 'category': 'GENERAL', 'priority': 'MEDIUM',
    })
    dashboard = client.get('/api/analytics/dashboard', headers=auth_headers)
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data['total_customers'] == 3
    assert data['total_tickets'] == 1
    assert data['open_tickets'] == 1
    assert data['resolved_tickets'] == 0
    assert data['average_tickets_per_customer'] == pytest.approx(1 / 3, abs=0.01)
