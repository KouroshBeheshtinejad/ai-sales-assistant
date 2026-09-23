from __future__ import annotations

import logging
import json

from sqlalchemy.orm import Session

from app.services.sales_intent import detect_intent
from app.services import sales_tools
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
        definitions = [
            ("search_products", "Search active products in the current store.", {"query": {"type": "string"}}, sales_tools.search_products),
            ("get_product", "Get one active product from the current store.", {"product_id": {"type": "integer"}}, sales_tools.get_product),
            ("get_product_stock", "Get current available stock for one product.", {"product_id": {"type": "integer"}}, sales_tools.get_product_stock),
            ("add_to_cart", "Add a product to the current customer's cart.", {"product_id": {"type": "integer"}, "quantity": {"type": "integer", "minimum": 1, "maximum": 100}}, sales_tools.add_to_cart),
            ("update_cart_quantity", "Set a cart item quantity.", {"product_id": {"type": "integer"}, "quantity": {"type": "integer", "minimum": 1, "maximum": 100}}, sales_tools.update_cart_quantity),
            ("remove_from_cart", "Remove a product from the current customer's cart.", {"product_id": {"type": "integer"}}, sales_tools.remove_from_cart),
            ("get_cart", "Read the current customer's cart.", {}, sales_tools.get_cart),
            ("clear_cart", "Clear the current customer's cart.", {}, sales_tools.clear_cart),
            ("start_checkout", "Start checkout for the current customer's cart.", {}, sales_tools.start_checkout),
            ("get_order", "Read an order owned by the current customer.", {"order_id": {"type": "integer"}}, sales_tools.get_order),
            ("get_order_status", "Read status for an owned order.", {"order_id": {"type": "integer"}}, sales_tools.get_order_status),
            ("get_tracking_information", "Read tracking information for an owned order.", {"order_id": {"type": "integer"}}, sales_tools.get_tracking_information),
        ]
        for name, description, properties, handler in definitions:
            required = list(properties)
            tool_handler = self._make_tool_handler(name, handler)
            self.tool_registry.register(SalesTool(
                name=name,
                description=description,
                parameters={"type": "object", "properties": properties, "required": required, "additionalProperties": False},
                handler=tool_handler,
            ))

    def _make_tool_handler(self, name, handler):
        def execute(*, context, **arguments):
            if name == "search_products":
                return handler(self.db, context["store_id"], arguments["query"])
            if name in {"get_product", "get_product_stock"}:
                return handler(self.db, context["store_id"], arguments["product_id"])
            if name in {"get_order", "get_order_status", "get_tracking_information"}:
                return handler(self.db, arguments["order_id"], context)
            if name in {"get_cart", "clear_cart", "start_checkout"}:
                return handler(self.db, context["store_id"], context)
            return handler(self.db, context["store_id"], context=context, **arguments)
        return execute

    def _call_read_tool(self, handler, context: dict, arguments: dict):
        if handler is sales_tools.search_products:
            return handler(self.db, context["store_id"], arguments["query"])
        if handler is sales_tools.get_product:
            return handler(self.db, context["store_id"], arguments["product_id"])
        if handler is sales_tools.get_order:
            return handler(self.db, arguments["order_id"], context)
        return handler(self.db, context["store_id"], context)

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
        context: dict | None = None,
    ) -> str:
        if self.is_prompt_injection(question):
            return "فقط می‌توانم دربارهٔ محصولات و قوانین همین فروشگاه پاسخ بدهم."

        intent = detect_intent(question)
        logger.info(
            "Sales agent detected intent=%s for store_id=%s",
            intent.value,
            store_id,
        )

        retrieval_question = question
        if history:
            previous_turns = " ".join(
                message["content"]
                for message in history[-6:]
                if message.get("role") == "user" and message.get("content")
            )
            retrieval_question = f"{previous_turns} {question}".strip()

        try:
            retrieved_context = retrieve_store_context(
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

        if retrieved_context is None:
            raise LookupError("Store not found")

        formatted_context = format_context(retrieved_context)

        history_context = ""
        if history:
            history_context = "\n\nConversation history:\n" + "\n".join(
                f"{message['role']}: {message['content']}"
                for message in history[-20:]
                if message.get("role") in {"user", "assistant"}
                and message.get("content")
            )

        try:
            tool_schemas = [tool.schema() for tool in self.tool_registry.list_tools()]
            agent_context = {"store_id": store_id, **(context or {})}
            answer = self.provider.complete(
                SYSTEM_PROMPT,
                self._build_prompt(
                    question,
                    formatted_context + history_context,
                    self._answer_guidance(
                        question,
                        retrieved_context,
                        formatted_context,
                    ),
                ),
                messages=history[-20:] if history else None,
                tools=tool_schemas,
            )
        except LLMProviderError:
            logger.exception(
                "Sales agent provider failed for store_id=%s",
                store_id,
            )
            raise

        for _ in range(4):
            if not isinstance(answer, dict) or not answer.get("tool_calls"):
                break
            tool_messages = []
            assistant_tool_message = {
                "role": "assistant",
                "content": answer.get("content", ""),
                "tool_calls": answer["tool_calls"],
            }
            for tool_call in answer["tool_calls"]:
                function = tool_call.get("function", {})
                result = self.tool_registry.execute(
                    function.get("name", ""),
                    function.get("arguments", "{}"),
                    agent_context,
                )
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "content": json.dumps(result, ensure_ascii=False),
                })
            answer = self.provider.complete(
                SYSTEM_PROMPT,
                "Continue with the customer's request using the verified tool results.",
                messages=(history or []) + [assistant_tool_message] + tool_messages,
                tools=tool_schemas,
            )

        if not isinstance(answer, str) or not answer.strip():
            raise LLMProviderError("LLM provider returned an empty response")

        return answer.strip()
