# ai-sales-assistant
AI-powered sales assistant for small businesses and online stores.

## Public Store Chat MVP

Each store has a public, read-only chat page at `/public/stores/{store_id}` and a
JSON endpoint at `POST /public/stores/{store_id}/chat`. The request body is:

```json
{"question": "Do you have this product in stock?"}
```

The response contains `success` and `answer`. Retrieval searches active FAQs,
Knowledge Base entries, and products belonging only to the requested store. It
uses lexical matching by default and can optionally use the hybrid embedding
index described below. Product price and stock always come directly from the
database. No chat history or customer account is used.

### Optional hybrid retrieval

The semantic document index is created by the latest Alembic migration and uses
the pgvector-enabled Docker image. It is disabled by default, so lexical
retrieval remains available when no embedding provider is configured.

- `AI_RAG_ENABLED=true` enables semantic retrieval and indexing.
- `AI_RAG_EMBEDDING_PROVIDER=mock` enables deterministic vectors for tests.
- `AI_RAG_EMBEDDING_PROVIDER=local` uses `sentence-transformers` with the
	`intfloat/multilingual-e5-small` model; install that optional dependency first.
- `AI_RAG_EMBEDDING_PROVIDER=openai` uses an OpenAI-compatible embeddings endpoint.
- `AI_RAG_EMBEDDING_API_KEY`, `AI_RAG_EMBEDDING_MODEL`, and
	`AI_RAG_EMBEDDING_ENDPOINT` configure the external provider.

After applying migrations, backfill records created before RAG was enabled with:

```bash
alembic upgrade head
AI_RAG_ENABLED=true AI_RAG_EMBEDDING_PROVIDER=mock \
	python -m app.services.semantic_index
```

Use the provider and credentials for the target environment instead of `mock`.
The command also removes semantic documents whose source records no longer exist.

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

## Configuration and hardening

Configuration is read from environment variables. `APP_ENV=production` enables
strict startup checks: `DATABASE_URL`, `SECRET_KEY`, and `APP_ALLOWED_HOSTS`
must all be configured or the process exits before accepting traffic. Development defaults to a local
SQLite database when `DATABASE_URL` is absent; use a separate local environment
file based on `.env.example` when working with PostgreSQL.

Production cookies are always `Secure`, `HttpOnly`, and `SameSite=Lax`. In a
local HTTP environment, set `APP_ENV=development`; `SESSION_COOKIE_SECURE` can
be enabled when testing HTTPS locally. `SameSite=None` is rejected unless secure
cookies are enabled.

Server-rendered form submissions use CSRF tokens. JSON API routes that require
an `Authorization: Bearer` header are not cookie-authenticated and are outside
that form-CSRF mechanism.

The application uses trusted-host protection. Set `APP_ALLOWED_HOSTS` to the
comma-separated public host names for production. CORS is not enabled because
the current web application is same-origin; add only explicit origins when a
separate browser client is introduced.

## Running locally

Set the required local environment variables, start the database if needed,
apply migrations, then run the development server:

```bash
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Run verification with:

```bash
pytest -q
python -m compileall -q app tests
```

## Production and staging

Build the application image with the included `Dockerfile`. Its command runs
Uvicorn without `--reload` and as a non-root user. Supply configuration through
the deployment environment, run migrations as a separate controlled release
step, and place the application behind an HTTPS reverse proxy.

The included Compose file intentionally starts only the database for local
development and binds it to loopback. It requires database variables from the
environment and is not a complete production deployment definition.

Health endpoints are `/health/live` for process liveness and `/health/ready`
for database readiness. The existing `/health/db` endpoint remains available
for database diagnostics.

The chat limiter remains process-local by design. For multiple workers or
instances, enforce a shared limit at the reverse proxy or API gateway first; a
shared store such as Redis requires separate approval and infrastructure work.
