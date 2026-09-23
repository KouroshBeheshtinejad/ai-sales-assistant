import os

from app.db.database import SessionLocal
from app.services.privacy_retention import purge_expired_conversation_messages


retention_days = int(os.getenv("CONVERSATION_RETENTION_DAYS", "90"))
with SessionLocal() as db:
    deleted = purge_expired_conversation_messages(db, retention_days)
print(f"Purged {deleted} expired conversation messages")
