from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.db.models import Product

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
                description="Search active products in the current store by name or description.",
                handler=lambda store_id, query: search_products(
                    self.db,
                    store_id,
                    query,
                ),
            )
        )

    def _llm_tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Product search query.",
                            }
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                },
            }
            for tool in self.tool_registry.list_tools()
        ]

    def _execute_tool_call(
        self,
        store_id: int,
        tool_call: dict,
    ) -> object:
        function = tool_call.get("function", {})
        tool_name = function.get("name")

        if not isinstance(tool_name, str) or not tool_name:
            raise LLMProviderError("AI tool call has no valid tool name")

        tool = self.tool_registry.get(tool_name)
        if tool is None:
            raise LLMProviderError(
                f"AI requested an unregistered tool: {tool_name}"
            )

        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            import json

            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise LLMProviderError(
                    f"AI tool call has invalid arguments: {tool_name}"
                ) from exc

        if not isinstance(arguments, dict):
            raise LLMProviderError(
                f"AI tool call arguments must be an object: {tool_name}"
            )

        if tool_name == "search_products":
            query = arguments.get("query")

            if not isinstance(query, str) or not query.strip():
                raise LLMProviderError(
                    "search_products requires a non-empty query"
                )

            return tool.handler(
                store_id,
                query.strip(),
            )

        raise LLMProviderError(
            f"No execution contract exists for tool: {tool_name}"
        )

    def _complete_with_tools(
        self,
        store_id: int,
        question: str,
    ) -> str:
        tools = self._llm_tools()

        result = self.provider.complete(
            SYSTEM_PROMPT,
            question,
            tools=tools,
        )

        if isinstance(result, str):
            return result.strip()

        if not isinstance(result, dict):
            raise LLMProviderError(
                "AI provider returned an unsupported response type"
            )

        tool_calls = result.get("tool_calls") or []

        if not tool_calls:
            content = result.get("content", "")
            if not isinstance(content, str) or not content.strip():
                raise LLMProviderError(
                    "AI provider returned neither content nor tool calls"
                )
            return content.strip()

        tool_messages = []

        for tool_call in tool_calls:
            tool_result = self._execute_tool_call(
                store_id,
                tool_call,
            )

            tool_call_id = tool_call.get("id")
            function = tool_call.get("function", {})
            tool_name = function.get("name")

            if not isinstance(tool_call_id, str) or not tool_call_id:
                raise LLMProviderError(
                    "AI tool call has no valid tool call id"
                )

            if not isinstance(tool_name, str) or not tool_name:
                raise LLMProviderError(
                    "AI tool call has no valid tool name"
                )

            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False,
                    ),
                }
            )

        assistant_message = {
            "role": "assistant",
            "content": result.get("content") or "",
            "tool_calls": tool_calls,
        }

        final_result = self.provider.complete(
            SYSTEM_PROMPT,
            (
                "Using the tool results above, answer the customer's "
                "original request. Use only the returned tool data."
            ),
            messages=[
                {"role": "user", "content": question},
                assistant_message,
                *tool_messages,
            ],
        )

        if isinstance(final_result, dict):
            final_content = final_result.get("content", "")
        else:
            final_content = final_result

        if not isinstance(final_content, str) or not final_content.strip():
            raise LLMProviderError(
                "AI provider returned an empty final response"
            )

        return final_content.strip()

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

    def _resolve_product_from_history(
        self,
        store_id: int,
        history: list[dict[str, str]] | None,
    ) -> Product | None:
        if not history:
            return None

        products = (
            self.db.query(Product)
            .filter(
                Product.store_id == store_id,
                Product.is_active.is_(True),
            )
            .all()
        )

        if not products:
            return None

        for message in reversed(history):
            if message.get("role") != "user":
                continue

            content = normalize_for_search(
                message.get("content", "")
            )

            for product in products:
                product_name = normalize_for_search(product.name)
                if product_name and product_name in content:
                    return product

        return None

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

        if intent == SalesIntent.PRODUCT_SEARCH:
            try:
                return self._complete_with_tools(
                    store_id=store_id,
                    question=question,
                )
            except LLMProviderError:
                logger.exception(
                    "Product search tool flow failed for store_id=%s",
                    store_id,
                )
                raise

        retrieval_question = question

        if history:
            product = self._resolve_product_from_history(
                store_id,
                history,
            )
            if product is not None:
                retrieval_question = f"{product.name} {question}"

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

        try:
            answer = self.provider.complete(
                SYSTEM_PROMPT,
                self._build_prompt(
                    question,
                    formatted_context,
                    self._answer_guidance(
                        question,
                        context,
                        formatted_context,
                    ),
                ),
                messages=history,
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
