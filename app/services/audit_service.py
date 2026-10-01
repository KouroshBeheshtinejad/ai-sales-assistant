from datetime import date, datetime
from decimal import Decimal
import hashlib
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog, FAQ, KnowledgeBaseEntry, User


_SENSITIVE_KEY_PARTS = ("password", "token", "secret", "credential", "api_key", "hash", "authority")


def _safe_state(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _safe_state(item)
            for key, item in value.items()
            if not any(part in str(key).casefold() for part in _SENSITIVE_KEY_PARTS)
        }
    if isinstance(value, (list, tuple)):
        return [_safe_state(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def record_audit_log(
    db: Session,
    *,
    actor: User | None,
    action: str,
    resource_type: str,
    resource_id: int | str | None,
    store_id: int | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        store_id=store_id,
        before_state=_safe_state(before_state),
        after_state=_safe_state(after_state),
        metadata_json=_safe_state(metadata),
        ip_address=ip_address,
    )
    db.add(entry)
    return entry


def content_audit_state(record: FAQ | KnowledgeBaseEntry) -> dict[str, Any]:
    label = record.question if isinstance(record, FAQ) else record.title
    content = record.answer if isinstance(record, FAQ) else record.content
    return {
        "label": label,
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "is_active": record.is_active,
    }


def record_content_audit(
    db: Session,
    *,
    actor: User,
    action: str,
    record: FAQ | KnowledgeBaseEntry,
    before_state: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    return record_audit_log(
        db,
        actor=actor,
        action=action,
        resource_type="faq" if isinstance(record, FAQ) else "knowledge_entry",
        resource_id=record.id,
        store_id=record.store_id,
        before_state=before_state,
        after_state=content_audit_state(record) if action.endswith(("created", "updated")) else None,
        ip_address=ip_address,
    )