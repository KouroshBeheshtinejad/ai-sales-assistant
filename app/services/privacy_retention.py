from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import Message


def purge_expired_conversation_messages(db: Session, retention_days: int) -> int:
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=retention_days)
    result = db.execute(delete(Message).where(Message.created_at < cutoff))
    db.commit()
    return int(result.rowcount or 0)
