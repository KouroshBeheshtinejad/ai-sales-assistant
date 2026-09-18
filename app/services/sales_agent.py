from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.services.sales_intent import SalesIntent, detect_intent
from app.services.sales_tools import search_products
from app.services.tool_registry import SalesTool, ToolRegistry
from app.services.chat_retrieval import (
    RetrievedContext,
    format_context,
    normalize_for_search,
    retrieve_store_context,
)
from app.services.llm_provider import (
    SYSTEM_PROMPT,
    LLMProvider,
    LLMProviderError,
)

logger = logging.getLogger(__name__)


_RECOMMENDATION_TERMS = (
    "پیشنهاد",
    "پیشنهاد می",
    "recommend",
    "recommendation",
    "suggest",
    "best",
)

_AMBIGUOUS_QUESTIONS = (
    "راهنمایی می کنید",
    "کمک می کنید",
    "میشه راهنمایی کنید",
    "می توانید راهنمایی کنید",
    "can you help",
    "help me",
)


class SalesAgentService:
    """Central service for sales-assistant orchestration."""

    def __init__(
        self,
        db: Session,
        provider: LLMProvider,
        tool_registry: ToolRegistry | None = None,
    ):
        self.db = db
        self.provider = provider
        self.tool_registry = tool_registry or ToolRegistry()

        if not self.tool_registry.list_tools():
            self._register_tools()
        
    def _register_tools(self) -> None:
        self.tool_registry.register(
            SalesTool(
                name="search_products",
                description=(
                    "Search active products in the current store by "
                    "name or description."
                ),
                handler=lambda store_id, query: search_products(
                    self.db,
                    store_id,
                    query,
                ),
            )
        )

    @staticmethod
    def is_prompt_injection(question: str) -> bool:
        normalized = normalize_for_search(question)

        tries_to_ignore_rules = (
            (
                "ignore" in normalized
                and any(
                    word in normalized
                    for word in ("previous", "rule", "instruction")
                )
            )
            or (
                "نادیده" in normalized
                and any(
                    word in normalized
                    for word in ("دستور", "قانون", "قبلی")
                )
            )
        )

        tries_to_reveal_prompt = (
            any(
                word in normalized
                for word in ("reveal", "show", "افشا", "نمایش", "بگو")
            )
            and any(
                word in normalized
                for word in (
                    "system prompt",
                    "prompt",
                    "دستور سیستم",
                    "پرامپت",
                )
            )
        )

        return tries_to_ignore_rules or tries_to_reveal_prompt

    @staticmethod
    def _answer_guidance(
        question: str,
        context: RetrievedContext,
        formatted_context: str,
    ) -> str:
        normalized_question = normalize_for_search(question)

        if any(
            phrase in normalized_question
            for phrase in _AMBIGUOUS_QUESTIONS
        ):
            return (
                "The question is ambiguous. "
                "Ask one short, polite clarifying question."
            )

        if context.is_empty:
            return (
                "No relevant store data was retrieved. Clearly say that "
                "sufficient information is not available and suggest "
                "contacting the seller."
            )

        if "Data quality notice:" in formatted_context:
            return (
                "The retrieved records conflict. State the uncertainty "
                "clearly; do not select, average, or infer a value."
            )

        if any(
            term in normalized_question
            for term in _RECOMMENDATION_TERMS
        ):
            return (
                "This is a product recommendation request. Offer only "
                "the retrieved products, with a brief reason grounded "
                "in their listed details."
            )

        if context.products:
            return (
                "Answer directly about the retrieved product or products "
                "using their listed details."
            )

        return (
            "Answer the policy or store-information question directly "
            "from the retrieved records."
        )

    @staticmethod
    def _build_prompt(
        question: str,
        context: str,
        answer_guidance: str,
    ) -> str:
        retrieved_data = context or "No matching information was found."

        return (
            f"Customer question:\n{question}\n\n"
            f"Response guidance:\n{answer_guidance}\n\n"
            f"Retrieved store data:\n{retrieved_data}"
        )

    def respond(
        self,
        store_id: int,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        if self.is_prompt_injection(question):
            return "فقط می‌توانم دربارهٔ محصولات و قوانین همین فروشگاه پاسخ بدهم."

        intent = detect_intent(question)
        logger.info(
            "Sales agent detected intent=%s for store_id=%s",
            intent.value,
            store_id,
        )

        if intent in {
            SalesIntent.CART_ADD,
            SalesIntent.CART_VIEW,
            SalesIntent.CHECKOUT,
            SalesIntent.ORDER_CREATE,
            SalesIntent.ORDER_STATUS,
        }:
            logger.info(
                "Transactional intent=%s is detected but no tool is registered yet",
                intent.value,
            )
            
            return "فقط می‌توانم دربارهٔ محصولات و قوانین همین فروشگاه پاسخ بدهم."

        retrieval_question = question
        if history:
            previous_turns = " ".join(
                message["content"]
                for message in history[-6:]
                if message.get("role") == "user" and message.get("content")
            )
            retrieval_question = f"{previous_turns} {question}".strip()

        try:
            context = retrieve_store_context(
                self.db,
                store_id,
                retrieval_question,
            )
        except Exception:
            logger.exception(
                "Sales agent retrieval failed for store_id=%s",
                store_id,
            )
            raise

        if context is None:
            raise LookupError("Store not found")

        formatted_context = format_context(context)

        history_context = ""
        if history:
            history_context = "\n\nConversation history:\n" + "\n".join(
                f"{message['role']}: {message['content']}"
                for message in history[-20:]
                if message.get("role") in {"user", "assistant"}
                and message.get("content")
            )

        try:
            answer = self.provider.complete(
                SYSTEM_PROMPT,
                self._build_prompt(
                    question,
                    formatted_context + history_context,
                    self._answer_guidance(
                        question,
                        context,
                        formatted_context,
                    ),
                ),
            )
        except LLMProviderError:
            logger.exception(
                "Sales agent provider failed for store_id=%s",
                store_id,
            )
            raise

        if not isinstance(answer, str) or not answer.strip():
            raise LLMProviderError("LLM provider returned an empty response")

        return answer.strip()
