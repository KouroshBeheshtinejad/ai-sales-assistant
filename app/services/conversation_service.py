from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import Conversation, Message


class ConversationService:
    """Service responsible for conversation lifecycle and identity."""

    @staticmethod
    def generate_guest_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def get_or_create_conversation(
        db: Session,
        *,
        store_id: int,
        user_id: int | None = None,
        guest_token: str | None = None,
    ) -> tuple[Conversation, str | None]:
        if user_id is None and guest_token is None:
            guest_token = ConversationService.generate_guest_token()

        query = db.query(Conversation).filter(
            Conversation.store_id == store_id,
            Conversation.status == "active",
        )

        if user_id is not None:
            conversation = query.filter(
                Conversation.user_id == user_id,
            ).order_by(
                Conversation.updated_at.desc(),
            ).first()

            if conversation is not None:
                return conversation, None

        else:
            conversation = query.filter(
                Conversation.guest_token == guest_token,
            ).first()

            if conversation is not None:
                return conversation, guest_token

        conversation = ConversationService.create_conversation(
            db,
            store_id=store_id,
            user_id=user_id,
        )

        return conversation, conversation.guest_token


    @staticmethod
    def add_message(
        db: Session,
        *,
        conversation_id: int,
        role: str,
        content: str,
    ) -> Message:
        if role not in {"user", "assistant", "tool"}:
            raise ValueError(f"Unsupported message role: {role}")

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )

        db.add(message)

        conversation = db.get(Conversation, conversation_id)
        if conversation is not None:
            conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        db.flush()

        return message

    @staticmethod
    def get_history(
        db: Session,
        *,
        conversation_id: int,
        limit: int = 20,
    ) -> list[Message]:
        if limit <= 0:
            return []

        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .limit(limit)
            .all()
        )

        return messages

    @staticmethod
    def create_conversation(
        db: Session,
        *,
        store_id: int,
        user_id: int | None = None,
    ) -> Conversation:
        guest_token = None

        if user_id is None:
            guest_token = ConversationService.generate_guest_token()

        conversation = Conversation(
            store_id=store_id,
            user_id=user_id,
            guest_token=guest_token,
            status="active",
        )

        db.add(conversation)
        db.flush()

        return conversation
