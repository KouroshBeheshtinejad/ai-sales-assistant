from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.services import grounded_responder as responder
from app.services import sales_tools
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
    is_offline_provider,
)
from app.services.sales_intent import SalesIntent, is_ambiguous_request
from app.services.text_utils import detect_language, numbers_in
from app.services.tool_registry import SalesTool, ToolRegistry

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 4
MAX_HISTORY_MESSAGES = 14
MAX_HISTORY_CHARS = 700
MIN_GROUNDED_NUMBER = 100  # smaller numbers (quantities, days) are not price claims

INJECTION_REFUSAL_FA = "فقط می‌توانم دربارهٔ محصولات و قوانین همین فروشگاه پاسخ بدهم."
INJECTION_REFUSAL_EN = "I can only help with this store's products and policies."

_INJECTION_PATTERNS = [
    r"ignore\b.{0,40}\b(previous|prior|above|all|earlier|your)\b.{0,30}\b(rule|instruction|prompt|direction)s?",
    r"disregard\b.{0,40}\b(rule|instruction|prompt|previous)s?",
    r"forget\b.{0,30}\b(everything|all|rules?|instructions?|previous)",
    r"(reveal|show|print|display|repeat|leak|tell me)\b.{0,40}\b(system|hidden|initial|internal)\b.{0,20}\b(prompt|instruction|message|rule)s?",
    r"\bsystem prompt\b",
    r"\b(developer|dan|jailbreak|god) mode\b",
    r"you are now\b.{0,40}\b(dan|unrestricted|unfiltered|jailbroken|developer)\b",
    r"\bact as\b.{0,30}\b(unrestricted|unfiltered|jailbroken|admin|developer)\b",
    r"(نادیده|فراموش)\s*(بگیر|کن)\w*.{0,40}(دستور|قانون|قبلی|قواعد)",
    r"(دستور|قانون|قواعد|دستورات)\s*(های|ها)?\s*(قبلی|بالا|سیستم)\w*.{0,30}(نادیده|فراموش|کنار)",
    r"(پرامپت|دستور سیستم|دستورات سیستم|پرومپت)\w*",
    r"(افشا|فاش|نمایش|نشان)\s*(بده|کن|بدهید)?.{0,30}(پرامپت|پرومپت|دستور سیستم|دستورات داخلی)",
    r"حالت\s*(توسعه\s*دهنده|ادمین|بدون\s*محدودیت)",
]
_INJECTION_RE = re.compile("|".join(f"(?:{p})" for p in _INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL)

_TOOL_DEFINITIONS: list[tuple[str, str, dict[str, Any], Any]] = [
    (
        "search_products",
        "Search this store's active products by name, type, color, size or description. "
        "Use an empty query to list the catalog. Returns ids, prices and live stock.",
        {"query": {"type": "string", "description": "What the customer is looking for"}},
        sales_tools.search_products,
    ),
    (
        "search_knowledge",
        "Look up store FAQs and policies (delivery, returns, warranty, hours, payment, contact).",
        {"query": {"type": "string", "description": "The policy question in the customer's words"}},
        sales_tools.search_knowledge,
    ),
    (
        "get_product",
        "Get full details of one active product by id.",
        {"product_id": {"type": "integer"}},
        sales_tools.get_product,
    ),
    (
        "get_product_stock",
        "Get the live available stock of one product.",
        {"product_id": {"type": "integer"}},
        sales_tools.get_product_stock,
    ),
    (
        "compare_products",
        "Compare 2-4 products side by side (price, stock, attributes).",
        {"product_ids": {"type": "array", "items": {"type": "integer"}, "maxItems": 4}},
        sales_tools.compare_products,
    ),
    (
        "get_store_info",
        "Get the store's name, description, business type and categories.",
        {},
        sales_tools.get_store_info,
    ),
    (
        "add_to_cart",
        "Add a product to the customer's cart. Only call when the customer clearly asked to buy it "
        "and the product id is known.",
        {"product_id": {"type": "integer"}, "quantity": {"type": "integer", "minimum": 1, "maximum": 100}},
        sales_tools.add_to_cart,
    ),
    (
        "update_cart_quantity",
        "Set the quantity of a product already in the cart.",
        {"product_id": {"type": "integer"}, "quantity": {"type": "integer", "minimum": 1, "maximum": 100}},
        sales_tools.update_cart_quantity,
    ),
    (
        "remove_from_cart",
        "Remove a product from the cart.",
        {"product_id": {"type": "integer"}},
        sales_tools.remove_from_cart,
    ),
    ("get_cart", "Read the customer's cart with line totals.", {}, sales_tools.get_cart),
    ("clear_cart", "Remove everything from the cart.", {}, sales_tools.clear_cart),
    (
        "start_checkout",
        "Begin checkout: the assistant then collects name, phone and address. Does NOT place or pay for the order.",
        {},
        sales_tools.start_checkout,
    ),
    ("get_order", "Read an order owned by the current customer.", {"order_id": {"type": "integer"}}, sales_tools.get_order),
    (
        "get_order_status",
        "Read status for an owned order.",
        {"order_id": {"type": "integer"}},
        sales_tools.get_order_status,
    ),
    (
        "get_tracking_information",
        "Read tracking information for an owned order.",
        {"order_id": {"type": "integer"}},
        sales_tools.get_tracking_information,
    ),
    (
        "track_order",
        "Look up an order by the customer's 10-digit tracking number.",
        {"tracking_number": {"type": "string", "maxLength": 20}},
        sales_tools.track_order,
    ),
]


@dataclass
class AgentMeta:
    source: str = "model"  # model | offline | fallback | guard
    intent: str = SalesIntent.GENERAL.value
    degraded_reason: str | None = None
    tool_calls: list[str] = field(default_factory=list)


class SalesAgentService:
    """Central service for sales-assistant orchestration.

    Flow: injection check → intent → store-scoped retrieval (RAG) → model call
    with tools (loop) → grounding guard → offline grounded fallback.  Whatever
    happens with the external model, the customer receives a useful answer
    built from the store's real data.
    """

    def __init__(
        self,
        db: Session,
        provider: LLMProvider,
        tool_registry: ToolRegistry | None = None,
    ):
        self.db = db
        self.provider = provider
        self.tool_registry = tool_registry or ToolRegistry()
        self.last_meta = AgentMeta()

        if not self.tool_registry.list_tools():
            self._register_tools()

    # ------------------------------------------------------------------ tools

    def _register_tools(self) -> None:
        for name, description, properties, handler in _TOOL_DEFINITIONS:
            self.tool_registry.register(
                SalesTool(
                    name=name,
                    description=description,
                    parameters={
                        "type": "object",
                        "properties": properties,
                        "required": list(properties),
                        "additionalProperties": False,
                    },
                    handler=self._make_tool_handler(name, handler),
                )
            )

    def _make_tool_handler(self, name, handler):
        def execute(*, context, **arguments):
            store_id = context["store_id"]
            if name in {"search_products", "search_knowledge"}:
                return handler(self.db, store_id, arguments["query"])
            if name in {"get_product", "get_product_stock"}:
                return handler(self.db, store_id, arguments["product_id"])
            if name == "compare_products":
                return handler(self.db, store_id, arguments["product_ids"])
            if name == "get_store_info":
                return handler(self.db, store_id)
            if name == "track_order":
                return handler(self.db, store_id, arguments["tracking_number"])
            if name in {"get_order", "get_order_status", "get_tracking_information"}:
                return handler(self.db, arguments["order_id"], context)
            if name in {"get_cart", "clear_cart", "start_checkout"}:
                return handler(self.db, store_id, context)
            return handler(self.db, store_id, context=context, **arguments)

        return execute

    # --------------------------------------------------------------- safeguards

    @staticmethod
    def is_prompt_injection(question: str) -> bool:
        normalized = normalize_for_search(question)
        return bool(_INJECTION_RE.search(normalized))

    @staticmethod
    def _answer_guidance(question: str, context: RetrievedContext, formatted_context: str) -> str:
        if context.mode == "none" and is_ambiguous_request(question):
            return "The question is ambiguous. Ask one short, polite clarifying question."
        if is_ambiguous_request(question):
            return "The question is ambiguous. Ask one short, polite clarifying question."
        if context.intent == SalesIntent.GREETING:
            return "Greet the customer warmly, introduce yourself briefly and offer help."
        if context.intent == SalesIntent.THANKS:
            return "Reply briefly and politely; offer further help."
        if context.is_empty:
            return (
                "No relevant store data was retrieved. Clearly say that sufficient information "
                "is not available and suggest contacting the seller."
            )
        if "Data quality notice:" in formatted_context:
            return (
                "The retrieved records conflict. State the uncertainty clearly; do not select, "
                "average, or infer a value."
            )
        if context.intent == SalesIntent.RECOMMENDATION:
            return (
                "This is a product recommendation request. Offer only the retrieved products, "
                "with a brief reason grounded in their listed details."
            )
        if context.intent == SalesIntent.COMPARE:
            return "Compare the retrieved products on price, stock and listed details; stay factual."
        if context.mode == "listing":
            return "List the retrieved products briefly with price and availability; invite a choice."
        if context.mode == "focus":
            return (
                "The customer is following up on the product discussed earlier; answer about that "
                "product using its listed details."
            )
        if context.products:
            return "Answer directly about the retrieved product or products using their listed details."
        return "Answer the policy or store-information question directly from the retrieved records."

    @staticmethod
    def _build_prompt(question: str, context: str, answer_guidance: str) -> str:
        retrieved_data = context or "No matching information was found."
        return (
            f"Customer question:\n{question}\n\n"
            f"Response guidance:\n{answer_guidance}\n\n"
            f"Retrieved store data:\n{retrieved_data}"
        )

    @staticmethod
    def _prepare_history(history: list[dict[str, str]] | None) -> list[dict[str, str]]:
        prepared: list[dict[str, str]] = []
        for message in (history or [])[-MAX_HISTORY_MESSAGES:]:
            role, content = message.get("role"), (message.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            if len(content) > MAX_HISTORY_CHARS:
                content = content[:MAX_HISTORY_CHARS].rsplit(" ", 1)[0] + " …"
            prepared.append({"role": role, "content": content})
        return prepared

    @staticmethod
    def _allowed_numbers(*texts: str) -> set[int]:
        allowed: set[int] = set()
        for text in texts:
            allowed |= numbers_in(text)
        # Simple arithmetic on listed prices (line totals) is legitimate.
        prices = [n for n in allowed if n >= MIN_GROUNDED_NUMBER]
        for price in prices[:40]:
            for quantity in range(2, 101):
                allowed.add(price * quantity)
        for index, first in enumerate(prices[:25]):
            for second in prices[index + 1 : 25]:
                allowed.add(first + second)
                allowed.add(abs(first - second))
        return allowed

    @classmethod
    def is_grounded(cls, answer: str, *source_texts: str) -> bool:
        claimed = {n for n in numbers_in(answer) if n >= MIN_GROUNDED_NUMBER}
        if not claimed:
            return True
        allowed = cls._allowed_numbers(*source_texts)
        # Years / phone-number-like long digits are not price claims.
        claimed = {n for n in claimed if not (1300 <= n <= 1500 or 1990 <= n <= 2100 or n >= 10**9 and False)}
        return claimed <= allowed

    # ------------------------------------------------------------------ respond

    def _offline_answer(self, prompt: str, history: list[dict[str, str]]) -> str:
        return responder.compose_answer(responder.parse_prompt(prompt), history)

    def respond(
        self,
        store_id: int,
        question: str,
        history: list[dict[str, str]] | None = None,
        context: dict | None = None,
    ) -> str:
        meta = AgentMeta()
        self.last_meta = meta

        if self.is_prompt_injection(question):
            meta.source = "guard"
            return INJECTION_REFUSAL_EN if detect_language(question) == "en" else INJECTION_REFUSAL_FA

        prepared_history = self._prepare_history(history)

        try:
            retrieved_context = retrieve_store_context(self.db, store_id, question, prepared_history)
        except Exception:
            logger.exception("Sales agent retrieval failed for store_id=%s", store_id)
            raise

        if retrieved_context is None:
            raise LookupError("Store not found")

        meta.intent = retrieved_context.intent.value
        formatted_context = format_context(retrieved_context)
        prompt = self._build_prompt(
            question,
            formatted_context,
            self._answer_guidance(question, retrieved_context, formatted_context),
        )
        logger.info(
            "Sales agent intent=%s mode=%s store_id=%s results=%s",
            meta.intent, retrieved_context.mode, store_id, len(retrieved_context.matches),
        )

        # Cheap, exact cases never need a model.
        if retrieved_context.intent in {SalesIntent.GREETING, SalesIntent.THANKS} or is_ambiguous_request(question):
            return self._finish_offline(prompt, prepared_history, meta, "shortcut", question)

        agent_context = {"store_id": store_id, **(context or {})}
        tool_schemas = [tool.schema() for tool in self.tool_registry.list_tools()]
        tool_texts: list[str] = []

        try:
            answer = self.provider.complete(
                SYSTEM_PROMPT, prompt, messages=prepared_history or None, tools=tool_schemas
            )
            conversation = list(prepared_history) + [{"role": "user", "content": prompt}]
            for _ in range(MAX_TOOL_ROUNDS):
                if not isinstance(answer, dict) or not answer.get("tool_calls"):
                    break
                assistant_message = {
                    "role": "assistant",
                    "content": answer.get("content", "") or "",
                    "tool_calls": answer["tool_calls"],
                }
                tool_messages = []
                for tool_call in answer["tool_calls"]:
                    function = tool_call.get("function", {})
                    name = function.get("name", "")
                    meta.tool_calls.append(name)
                    outcome = self.tool_registry.execute_safely(
                        name, function.get("arguments", "{}"), agent_context
                    )
                    serialized = json.dumps(outcome, ensure_ascii=False, default=str)
                    tool_texts.append(serialized)
                    tool_messages.append(
                        {"role": "tool", "tool_call_id": tool_call.get("id", ""), "content": serialized}
                    )
                conversation += [assistant_message] + tool_messages
                answer = self.provider.complete(SYSTEM_PROMPT, "", messages=conversation, tools=tool_schemas)

            if isinstance(answer, dict):  # still asking for tools after the limit
                answer = answer.get("content", "") or ""
            if not isinstance(answer, str) or not answer.strip():
                raise LLMProviderError("LLM provider returned an empty response")
        except Exception as exc:  # noqa: BLE001 - the customer must still get an answer
            reason = "empty" if "empty response" in str(exc).lower() else type(exc).__name__
            if isinstance(exc, LLMProviderError):
                logger.warning("Sales agent provider failed for store_id=%s: %s", store_id, exc)
            else:
                logger.exception("Unexpected chat response-generation failure for store_id=%s", store_id)
            if tool_texts:
                # Actions already happened; report their real result.
                tool_only = [{"role": "tool", "content": text} for text in tool_texts[-2:]]
                meta.source, meta.degraded_reason = "fallback", reason
                return responder.compose_tool_answer(tool_only, question)
            return self._finish_offline(prompt, prepared_history, meta, reason, question)

        answer = answer.strip()
        if not is_offline_provider(self.provider) and not self.is_grounded(
            answer, prompt, question, " ".join(m["content"] for m in prepared_history), *tool_texts
        ):
            logger.warning("Ungrounded numbers in model answer for store_id=%s; using grounded answer", store_id)
            if tool_texts:
                meta.source, meta.degraded_reason = "guard", "ungrounded"
                return responder.compose_tool_answer([{"role": "tool", "content": t} for t in tool_texts[-2:]], question)
            return self._finish_offline(prompt, prepared_history, meta, "ungrounded", question)

        meta.source = "offline" if is_offline_provider(self.provider) else "model"
        return answer

    def _finish_offline(self, prompt, history, meta: AgentMeta, reason: str, question: str) -> str:
        meta.source = "offline" if reason == "shortcut" else "fallback"
        meta.degraded_reason = None if reason == "shortcut" else reason
        answer = self._offline_answer(prompt, history)
        if not answer.strip():
            answer = responder._TEXT[detect_language(question)]["not_found"]
        return answer.strip()
