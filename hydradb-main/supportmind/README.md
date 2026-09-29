# SupportMind

SupportMind is an AI customer-support workspace that carries customer context between conversations. A FastAPI agent recalls customer-scoped experiences from Hindsight Cloud, reflects on relevant history, generates a response with Groq, persists ticket messages, and retains the interaction for future support.

## Problem

Support agents often ask customers to repeat their environment, previous troubleshooting steps, and results. Without durable, isolated history, an agent may repeat failed advice or miss a fix that worked before.

## Solution

SupportMind uses Hindsight persistent memory to recall earlier customer experiences across support interactions. Every retained memory is tagged to its customer, and recall requests use an exact customer tag so one customer's history is not returned for another.

## Architecture

```text
React + Vite frontend
        |
        v
FastAPI backend and JWT authentication
        |
        v
Agent orchestration: customer, ticket, messages, memory, reflection, response
        |                                  |
        v                                  v
Hindsight Cloud                       Groq API
        |
        v
SQLite by default; SQLAlchemy supports configured relational databases
```

### Agent workflow

1. Validate the selected customer and, when provided, that the ticket belongs to that customer.
2. Load recent SQL conversation history and recall customer-tagged context from Hindsight.
3. Reflect over returned memories and include relevant context in the Groq prompt.
4. Persist the customer and agent messages, then retain the interaction in Hindsight for later conversations.
5. Record local memory events and successful Hindsight retrieval events for operational analytics.

The demo's no-memory request explicitly skips recall; it does not fabricate a baseline response. It still uses the configured agent and retention flow. A successful retention is reported only when Hindsight confirms the request.

### Hindsight memory

- Retention uses `POST /v1/default/banks/{bank_id}/memories`.
- Semantic recall uses `POST /v1/default/banks/{bank_id}/memories/recall`.
- Both requests use the configured Hindsight URL and bearer credential on the backend only.
- Memories include a `customer:{external_customer_id}` tag. Recall requests require an exact matching customer tag.
- Reflection summarizes returned Hindsight records; unavailable Hindsight is reported as unavailable, never as a successful local-memory fallback.

### Ticket workflow

Tickets and messages are stored in the application database. Ticket lists can be filtered by status, priority, and customer. Message creation and agent chat validate customer/ticket ownership; ticket status changes update the resolution timestamp.

## Setup

Copy `backend/.env.example` to `backend/.env` and fill in the values for your environment. Do not commit `.env`; `.gitignore` excludes environment files, local databases, Python environments, dependency folders, and generated builds.

Configure these variables in `backend/.env`:

- `DATABASE_URL`: SQLAlchemy connection URL; SQLite is the local default.
- `GROQ_API_KEY` and `GROQ_MODEL`: server-side response generation.
- `HINDSIGHT_URL`, `HINDSIGHT_API_KEY`, and `HINDSIGHT_DEFAULT_BANK`: server-side persistent memory.
- `JWT_SECRET`: a unique, long random signing secret.
- `ADMIN_EMAIL` and `ADMIN_PASSWORD`: credentials used to provision the initial admin user when the database is empty.
- `FRONTEND_URL`: browser origin allowed by the API's CORS configuration.

The app does not create a default administrator when admin credentials are absent. Keep all real values in the ignored `.env` file or your deployment secret manager. If a credential has been placed in a shared or committed example file, rotate it before deployment.

### Backend

From the repository root on Windows PowerShell:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive API documentation is at `/docs` and the schema is at `/openapi.json`.

### Frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend uses `http://localhost:8000` by default. Set `VITE_API_BASE_URL` at build time to use another backend origin. Sign in with the admin credentials provisioned through the backend environment.

## Demo flow

1. Sign in and open **Demo Mode**. The customer selector is populated from `GET /api/customers`; Rahul is preselected only if that real customer record exists.
2. Enter a support issue and run the agent once without memory. The request skips Hindsight recall and shows the actual agent response.
3. Ask a related follow-up with Hindsight enabled. The UI reports real recall availability, memory count, references, and confirmed retention status.
4. Start another comparison or open Memory Inspector to recall or reflect over Hindsight records for a selected customer.
5. Compare two customers with a similar query to demonstrate that their exact tags isolate returned memories.

Live Hindsight and Groq behavior requires valid backend configuration and a running API. The automated suite uses a controlled Hindsight HTTP transport and a mocked Groq response; it verifies request paths, exact customer tags, isolation, and persistence across separate requests, but does not replace live Cloud verification.

## API endpoints

All routes except login, health, and the root status endpoint require a bearer access token.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/login` | Authenticate and receive a token |
| `GET` | `/api/health` | Backend, database, and integration configuration status |
| `GET` | `/api/customers` | List customers |
| `GET` | `/api/customers/{customer_id}` | Customer profile |
| `GET` | `/api/customers/{customer_id}/tickets` | Customer ticket history |
| `GET` | `/api/customers/{customer_id}/memory` | Hindsight recall for that customer |
| `GET` | `/api/tickets` | Ticket list; optional `status`, `priority`, `customer_id` filters |
| `POST` | `/api/tickets` | Create a ticket |
| `GET` | `/api/tickets/{ticket_id}` | Ticket detail |
| `PATCH` | `/api/tickets/{ticket_id}` | Update ticket fields or status |
| `GET` | `/api/tickets/{ticket_id}/messages` | Ticket message history |
| `POST` | `/api/tickets/{ticket_id}/messages` | Add a customer-owned ticket message |
| `POST` | `/api/agent/chat` | Run the support agent; `use_memory` defaults to true |
| `POST` | `/api/memory/{customer_id}/retain` | Retain a customer-scoped memory |
| `POST` | `/api/memory/{customer_id}/recall` | Recall Hindsight memories |
| `POST` | `/api/memory/{customer_id}/reflect` | Recall and summarize Hindsight context |
| `GET` | `/api/analytics/dashboard` | Database-derived dashboard and analytics metrics |
| `GET` | `/api/analytics` | Compatibility analytics endpoint |

## Testing

```powershell
cd backend
python -m compileall -q app
python -m pytest -q
```

The tests use an isolated SQLite database and do not need real Hindsight or Groq credentials. For live integration verification, start the backend with valid secrets, then exercise the agent, recall, retention, and reflection routes.