import json
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.models.analytics_event import AnalyticsEvent
from app.models.customer import Customer
from app.models.memory_event import MemoryEvent

settings = get_settings()
MAX_RECALL_MEMORIES = 6
MAX_MEMORY_TEXT_LENGTH = 1200


class HindsightService:
    def __init__(self, db):
        self.db = db
        self.last_recall_available = False

    def bank_id_for_customer(self, customer: Customer) -> str:
        return settings.HINDSIGHT_DEFAULT_BANK

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.HINDSIGHT_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _customer_tag(self, customer: Customer) -> str:
        return f"customer:{customer.external_customer_id}"

    def recall(
        self,
        customer_id: int,
        query: str,
        ticket_id: int | None = None,
    ):
        customer = (
            self.db.query(Customer)
            .filter(Customer.id == customer_id)
            .first()
        )

        if not customer:
            return []

        if not settings.HINDSIGHT_URL or not settings.HINDSIGHT_API_KEY:
            return []

        bank_id = self.bank_id_for_customer(customer)

        customer_tag = self._customer_tag(customer)

        recall_query = (
            f"Customer: {customer.name}. "
            f"Customer ID: {customer.external_customer_id}. "
            f"Current issue: {query}. "
            "Retrieve relevant previous support interactions, "
            "known issues, successful fixes, failed troubleshooting steps, "
            "environment details, and customer preferences."
        )

        payload = {
            "query": recall_query,
            "types": [
                "world",
                "experience",
                "observation",
            ],
            "tags": [
                customer_tag,
            ],
            "tags_match": "exact",
        }

        try:
            response = httpx.post(
                (
                    f"{settings.HINDSIGHT_URL.rstrip('/')}"
                    f"/v1/default/banks/{bank_id}/memories/recall"
                ),
                json=payload,
                headers=self._headers(),
                timeout=20,
            )

            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])[:MAX_RECALL_MEMORIES]
            self.last_recall_available = True

            memories = []

            for item in results:
                if not isinstance(item, dict):
                    continue

                summary = (
                    item.get("text")
                    or item.get("summary")
                    or item.get("memory")
                    or item.get("details")
                    or str(item)
                )
                if len(summary) > MAX_MEMORY_TEXT_LENGTH:
                    summary = summary[:MAX_MEMORY_TEXT_LENGTH] + "..."

                memories.append(
                    {
                        "id": item.get("id"),
                        "type": item.get("type", "memory"),
                        "summary": summary,
                        "source": item.get("context", ""),
                        "date": item.get("mentioned_at") or item.get("created_at") or item.get("timestamp"),
                        "relevance": item.get("score") or item.get("relevance"),
                    }
                )

            self.db.add(AnalyticsEvent(
                customer_id=customer_id,
                ticket_id=ticket_id,
                event_type="HINDSIGHT_RETRIEVAL",
                metadata_json=json.dumps({"memory_count": len(memories)}),
            ))
            self.db.commit()
            return memories

        except httpx.HTTPStatusError as exc:
            self.last_recall_available = False
            print("Hindsight recall failed with status", exc.response.status_code)
            return []

        except Exception as exc:
            self.last_recall_available = False
            print("Hindsight recall failed:", type(exc).__name__)
            return []

    def retain(
        self,
        customer_id: int,
        ticket_id: int | None,
        event_type: str,
        summary: str,
        bank_id: str | None = None,
    ):
        customer = (
            self.db.query(Customer)
            .filter(Customer.id == customer_id)
            .first()
        )

        if not customer:
            return None

        actual_bank_id = (
            bank_id
            or self.bank_id_for_customer(customer)
        )

        customer_tag = self._customer_tag(customer)

        memory_content = (
            f"Customer ID: {customer.external_customer_id}. "
            f"Customer name: {customer.name}. "
            f"Ticket ID: {ticket_id}. "
            f"Event type: {event_type}. "
            f"Support interaction: {summary}"
        )

        hindsight_success = False

        if settings.HINDSIGHT_URL and settings.HINDSIGHT_API_KEY:
            try:
                response = httpx.post(
                    (
                        f"{settings.HINDSIGHT_URL.rstrip('/')}"
                        f"/v1/default/banks/{actual_bank_id}/memories"
                    ),
                    json={
                        "items": [
                            {
                                "content": memory_content,
                                "context": f"supportmind:{event_type}",
                                "timestamp": datetime.now(
                                    timezone.utc
                                ).isoformat(),
                                "tags": [
                                    customer_tag,
                                ],
                            }
                        ]
                    },
                    headers=self._headers(),
                    timeout=20,
                )

                response.raise_for_status()

                hindsight_success = True

                print("Hindsight memory retained")

            except httpx.HTTPStatusError as exc:
                print(
                    "Hindsight retain HTTP error:",
                    exc.response.status_code,
                )

            except Exception as exc:
                print("Hindsight retain failed:", type(exc).__name__)

        record = MemoryEvent(
            customer_id=customer_id,
            ticket_id=ticket_id,
            event_type=event_type,
            hindsight_bank_id=actual_bank_id,
            metadata_json=json.dumps(
                {
                    "summary": summary,
                    "customer_tag": customer_tag,
                    "hindsight_success": hindsight_success,
                }
            ),
        )

        self.db.add(record)
        self.db.commit()

        return record

    def reflect(
        self,
        customer_id: int,
        memories: list[dict[str, Any]],
    ):
        if not memories:
            return (
                "No relevant historical customer memory "
                "was retrieved."
            )

        summary_parts = []

        for item in memories[:6]:
            if isinstance(item, dict):
                summary = (
                    item.get("summary")
                    or item.get("memory")
                    or item.get("details")
                    or str(item)
                )

                if summary:
                    summary_parts.append(
                        str(summary)
                    )
            else:
                summary_parts.append(
                    str(item)
                )

        return (
            "Relevant remembered customer context: "
            + " | ".join(summary_parts)
        )