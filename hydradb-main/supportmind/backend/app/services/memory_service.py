from app.services.hindsight import HindsightService


class MemoryService:
    def __init__(self, db):
        self.db = db
        self.hindsight = HindsightService(db)

    def recall_context(self, customer_id: int, issue: str, ticket_id: int | None = None):
        memories = self.hindsight.recall(customer_id, issue, ticket_id=ticket_id)
        summary = self.hindsight.reflect(customer_id, memories)
        return {
            'memories': memories,
            'summary': summary,
            'hindsight_available': self.hindsight.last_recall_available,
        }

    def retain_context(self, customer_id: int, ticket_id: int | None, event_type: str, summary: str):
        return self.hindsight.retain(customer_id, ticket_id, event_type, summary)
