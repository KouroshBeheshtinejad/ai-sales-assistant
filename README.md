# ai-sales-assistant
AI-powered sales assistant for small businesses and online stores.

## Public Store Chat MVP

Each store has a public, read-only chat page at `/public/stores/{store_id}` and a
JSON endpoint at `POST /public/stores/{store_id}/chat`. The request body is:

```json
{"question": "Do you have this product in stock?"}
```

The response contains `success` and `answer`. Retrieval is deliberately simple:
it searches active FAQs, Knowledge Base entries, and products belonging only to
the requested store. Product price and stock come directly from the database.
No chat history, embeddings, RAG, or customer account is used.

### Chat provider configuration

Chat is disabled by default and does not prevent the application from starting.
Set these environment variables only when enabling a provider:

- `AI_CHAT_PROVIDER=mock` enables the deterministic local provider for tests and demos.
- `AI_CHAT_PROVIDER=openai` enables an OpenAI-compatible chat endpoint.
- `AI_CHAT_API_KEY` contains the provider key and must never be committed or logged.
- `AI_CHAT_MODEL` defaults to `gpt-4o-mini`.
- `AI_CHAT_ENDPOINT` defaults to `https://api.openai.com/v1/chat/completions`.
- `AI_CHAT_TIMEOUT_SECONDS` defaults to `8`.

If the provider is disabled or unavailable, the endpoint returns a safe generic
error and does not expose provider details. Existing stores are treated as public
in this MVP because the current schema has no publication flag; adding one is a
separate product decision and migration.

This MVP does not include distributed rate limiting. It limits question length,
retrieved context size, and provider timeout, but production abuse protection
should be added before exposing the endpoint at scale.

The initial in-memory rate-limit settings are `20` requests per direct client
address and store per `60` seconds. They can be changed with
`AI_CHAT_RATE_LIMIT_REQUESTS`, `AI_CHAT_RATE_LIMIT_WINDOW_SECONDS`, and
`AI_CHAT_RATE_LIMIT_MAX_KEYS`. The limiter does not trust forwarded headers and
is process-local, so it is not shared across workers or instances.

The current Store schema has no publication or visibility field. Consequently,
existing and new stores are public to the read-only chat page by design in this
MVP. Making a store private requires a separate reviewed schema migration and a
default policy for existing stores; no such migration is applied here.

`SECRET_KEY` must be set to a strong environment value in any deployed
environment. The longer development fallback only prevents weak-key warnings;
it is not suitable for production and does not preserve tokens if the configured
secret changes.

Run all tests with:

```bash
pytest -q
```
