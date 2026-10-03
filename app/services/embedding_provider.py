"""Configurable embedding providers used by the optional hybrid retrieval layer."""

from __future__ import annotations

import hashlib
import json
import math
import os
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Mapping, Protocol, Sequence
from urllib import error, request


DEFAULT_EMBEDDING_DIMENSION = 384
DEFAULT_LOCAL_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


class EmbeddingProvider(Protocol):
    dimension: int

    def embed_query(self, text: str) -> list[float]:
        ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class EmbeddingProviderError(RuntimeError):
    pass


def _normalize_key(value: str) -> str:
    translation = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "\u200c": " "})
    return " ".join(
        unicodedata.normalize("NFKC", value).translate(translation).casefold().split()
    )


def _validate_vector(vector: Sequence[float], dimension: int) -> list[float]:
    if len(vector) != dimension:
        raise EmbeddingProviderError(
            f"Embedding dimension {len(vector)} does not match configured dimension {dimension}"
        )
    try:
        result = [float(item) for item in vector]
    except (TypeError, ValueError) as exc:
        raise EmbeddingProviderError("Embedding provider returned a non-numeric vector") from exc
    if not all(math.isfinite(item) for item in result):
        raise EmbeddingProviderError("Embedding provider returned a non-finite vector")
    return result


def _hash_embedding(text: str, dimension: int) -> list[float]:
    """Return a deterministic unit vector for tests and offline mock operation."""
    values: list[float] = []
    counter = 0
    while len(values) < dimension:
        digest = hashlib.sha256(f"{_normalize_key(text)}:{counter}".encode("utf-8")).digest()
        values.extend((byte / 127.5) - 1 for byte in digest)
        counter += 1
    values = values[:dimension]
    magnitude = math.sqrt(sum(value * value for value in values))
    return [value / magnitude for value in values]


def _hashing_embedding(text: str, dimension: int) -> list[float]:
    """Offline, deterministic *semantic-ish* vector (no model download needed).

    Feature hashing of stemmed words, domain synonym groups/concepts, word
    bigrams and character trigrams.  Texts that share vocabulary, inflections,
    typos or domain synonyms get a high cosine similarity, so hybrid retrieval
    works meaningfully even without a neural embedding model.
    """
    from app.services.text_utils import content_tokens, trigrams

    vector = [0.0] * dimension

    def add(feature: str, weight: float) -> None:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        number = int.from_bytes(digest, "big")
        sign = 1.0 if (number >> 63) & 1 else -1.0
        vector[number % dimension] += sign * weight

    tokens = content_tokens(text)
    for token in tokens:
        add(f"w:{token}", 1.0)
        for gram in trigrams(token):
            add(f"g:{gram}", 0.25)
    for left, right in zip(tokens, tokens[1:]):
        add(f"b:{left}_{right}", 0.5)
    try:  # domain synonyms (گوشی ↔ phone, ارسال ↔ delivery ...)
        from app.services.chat_retrieval import concepts_in, synonym_groups_in

        for name in synonym_groups_in(tokens):
            add(f"s:{name}", 1.5)
        for name in concepts_in(text, tokens):
            add(f"c:{name}", 1.5)
    except ImportError:  # pragma: no cover - circular import safety
        pass
    magnitude = math.sqrt(sum(value * value for value in vector))
    if not magnitude:
        return _hash_embedding(text, dimension)
    return [value / magnitude for value in vector]


class UnavailableEmbeddingProvider:
    dimension = DEFAULT_EMBEDDING_DIMENSION

    def embed_query(self, text: str) -> list[float]:
        raise EmbeddingProviderError("Embedding provider is not configured")

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbeddingProviderError("Embedding provider is not configured")


@dataclass(frozen=True)
class MockEmbeddingProvider:
    """Deterministic provider with optional vectors for semantic retrieval tests."""

    vectors: Mapping[str, Sequence[float]] = field(default_factory=dict)
    dimension: int = DEFAULT_EMBEDDING_DIMENSION

    def _embed(self, text: str) -> list[float]:
        vector = self.vectors.get(_normalize_key(text))
        if vector is None:
            return _hashing_embedding(text, self.dimension)
        return _validate_vector(vector, self.dimension)


    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]


@dataclass(frozen=True)
class HashingEmbeddingProvider:
    """Production-safe offline embeddings (no network, no model download)."""

    dimension: int = DEFAULT_EMBEDDING_DIMENSION

    def embed_query(self, text: str) -> list[float]:
        return _hashing_embedding(text, self.dimension)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [_hashing_embedding(text, self.dimension) for text in texts]


@lru_cache(maxsize=2)
def _load_local_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingProviderError(
            "Local embeddings require the sentence-transformers dependency"
        ) from exc
    try:
        return SentenceTransformer(model_name)
    except Exception as exc:
        raise EmbeddingProviderError("Local embedding model could not be loaded") from exc


@dataclass(frozen=True)
class LocalEmbeddingProvider:
    model: str = DEFAULT_LOCAL_EMBEDDING_MODEL
    dimension: int = DEFAULT_EMBEDDING_DIMENSION

    def _embed(self, texts: Sequence[str], prefix: str) -> list[list[float]]:
        model = _load_local_model(self.model)
        model_inputs = [f"{prefix}{text}" if "e5" in self.model.casefold() else text for text in texts]
        try:
            vectors = model.encode(model_inputs, normalize_embeddings=True)
        except Exception as exc:
            raise EmbeddingProviderError("Local embedding generation failed") from exc
        return [_validate_vector(vector, self.dimension) for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "query: ")[0]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, "passage: ")


@dataclass(frozen=True)
class OpenAICompatibleEmbeddingProvider:
    api_key: str
    model: str
    endpoint: str
    timeout_seconds: float
    dimension: int = DEFAULT_EMBEDDING_DIMENSION

    def _embed(self, inputs: Sequence[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.model, "input": list(inputs)}).encode("utf-8")
        http_request = request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
            items = response_data["data"]
            if not isinstance(items, list) or len(items) != len(inputs):
                raise EmbeddingProviderError("Embedding provider returned an incomplete response")
            ordered_items = sorted(items, key=lambda item: item["index"])
            return [_validate_vector(item["embedding"], self.dimension) for item in ordered_items]
        except EmbeddingProviderError:
            raise
        except (
            error.URLError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            json.JSONDecodeError,
        ) as exc:
            raise EmbeddingProviderError("External embedding request failed") from exc

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts)


def rag_is_enabled() -> bool:
    return os.getenv("AI_RAG_ENABLED", "false").casefold() in {"1", "true", "yes", "on"}


def get_embedding_provider() -> EmbeddingProvider:
    provider_name = os.getenv("AI_RAG_EMBEDDING_PROVIDER", "disabled").casefold()
    if provider_name in {"hashing", "offline"}:
        return HashingEmbeddingProvider()
    if provider_name == "mock":
        return MockEmbeddingProvider()
    if provider_name == "local":
        return LocalEmbeddingProvider(
            model=os.getenv("AI_RAG_EMBEDDING_MODEL", DEFAULT_LOCAL_EMBEDDING_MODEL)
        )
    if provider_name == "openai":
        api_key = os.getenv("AI_RAG_EMBEDDING_API_KEY")
        if not api_key:
            return UnavailableEmbeddingProvider()
        try:
            timeout_seconds = max(1.0, float(os.getenv("AI_RAG_EMBEDDING_TIMEOUT_SECONDS", "8")))
        except ValueError:
            timeout_seconds = 8.0
        return OpenAICompatibleEmbeddingProvider(
            api_key=api_key,
            model=os.getenv("AI_RAG_EMBEDDING_MODEL", "text-embedding-3-small"),
            endpoint=os.getenv(
                "AI_RAG_EMBEDDING_ENDPOINT",
                "https://api.openai.com/v1/embeddings",
            ),
            timeout_seconds=timeout_seconds,
        )
    return UnavailableEmbeddingProvider()
