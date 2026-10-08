<div align="center">

# 🛍️ NAVA — AI Sales Assistant for Online Stores

**A conversational-commerce platform where an AI assistant answers from your own catalog, fills the cart, takes the order, and hands you a paid, invoiced, trackable sale — with 14 selectable UI locales, around the clock.**

[![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-React%2018-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![Database](https://img.shields.io/badge/database-PostgreSQL%20%2B%20pgvector-4169E1?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-See%20LICENSE-lightgrey)](#-license)
[![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)](#-testing)

**Proprietary software. Copyright (c) Kourosh Beheshtinejad. All rights reserved. See [LICENSE](LICENSE).**

[Features](#-features) · [Architecture](#-architecture) · [Quick start](#-quick-start) · [Configuration](#-configuration) · [API reference](#-api-reference) · [Testing](#-testing) · [Deployment](#-deployment)

</div>

---

## 📖 Overview

NAVA turns a store's product catalog, FAQs, and policies into a **grounded AI shopping assistant**. Customers chat with it the way they'd talk to a knowledgeable shop assistant — asking about stock, sizes, prices, delivery times — and the assistant can add items to their cart and place the order without ever leaving the conversation.

The critical design decision: **the language model never invents a price, a stock level, or an order total.** Every number the assistant says comes straight from the database at the moment of the answer; the model only writes the wording of the reply. Everything else — the storefront, seller dashboard, guest checkout, invoicing, and order tracking — works even if the AI provider is disabled or unreachable.

> 📌 **Status:** actively developed MVP. Existing stores are public by design (no publish/unpublish flag yet — see [Configuration](#-configuration)).

---

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### For shoppers
- 💬 Ask about products, prices, sizes, and stock in plain language
- 🛒 Chat-assisted shopping with secure cart checkout and payment confirmation
- 👤 **Guest checkout** — no account required, secured by a private session token
- 📦 Track any order with its 10-digit tracking number
- 🧾 Download a PDF invoice for any order
- 🌍 **14 selectable UI locales** with right-to-left layout for Persian and Arabic; translation coverage varies and missing messages fall back to English

</td>
<td width="50%" valign="top">

### For sellers
- 🏪 Create a store in minutes — no developer required
- 📋 **49 ready-made product templates** (clothing, cafés, pharmacies, electronics, services, and more), each with its own attribute set
- 🧠 Teach the assistant with FAQs and free-form knowledge base entries
- 📊 A real seller panel: products, orders, conversations, low-stock alerts
- 💬 Read every conversation to learn what customers actually ask
- 🖼️ Product images via Cloudinary, with validated dimensions and size limits

</td>
</tr>
</table>

### Under the hood

| | |
|---|---|
| 🔒 **Security-first** | CSRF protection on cookie-authenticated routes, trusted-host enforcement, rate limiting on auth/chat/tracking, idempotent checkout, argon2 password hashing, verified accounts (email + optional SMS) |
| 🧮 **Grounded retrieval** | Lexical search by default over each store's own products/FAQs/knowledge base; optional hybrid semantic search via `pgvector` and pluggable embedding providers |
| 🧾 **Persian-correct PDF invoices** | Invoices embed the Vazirmatn font and run all Persian text through proper Arabic/Persian shaping + bidi reordering — no "black square" glyph fallbacks |
| 💳 **Payments** | Optional server-verified ZarinPal integration; a development-only mock is available for demos |
| 🗑️ **Privacy by default** | Scheduled purge script for old conversation messages, configurable retention window |
| 🧩 **Provider-agnostic AI** | Chat and embedding providers are abstracted behind interfaces (`mock` / `openai`-compatible / `local`); the app starts and runs fully even with AI disabled |
| ✅ **Automated test suite** | Route tests, service-level tests, security hardening tests, and concurrency tests |

---

## 🏗️ Architecture

```
┌───────────────────────┐      HTTPS       ┌───────────────────────────────────┐
│     React 18 SPA       │ ───────────────▶ │             FastAPI                │
│  (Vite build, RTL/LTR,  │                  │                                     │
│   14 locale choices)   │ ◀─────────────── │  routes/  → auth, stores, products, │
└───────────────────────┘   JSON over /api  │  cart, orders, chat, dashboard,     │
                                             │  faqs, knowledge base, payments,    │
        Same-origin,                        │  seller orders, business types      │
   server-rendered public                   │                                     │
   store pages + SEO meta                   │  services/ → sales agent, cart,     │
                                             │  order, invoice (PDF), retrieval,   │
                                             │  embeddings, payments, guest        │
                                             │  commerce identity, verification    │
                                             └────────────┬────────────────────────┘
                                                           │ SQLAlchemy
                                                           ▼
                                    ┌────────────────────────────────────────┐
                                    │      PostgreSQL 17 + pgvector            │
                                    │  users · stores · products · orders      │
                                    │  carts · conversations · faqs            │
                                    │  knowledge base · semantic documents     │
                                    └────────────────────────────────────────┘
```

**Backend:** FastAPI + SQLAlchemy + Alembic migrations, served by Uvicorn.
**Frontend:** React 18 + React Router 7, built with Vite; ships as static assets served by FastAPI in production.
**Database:** PostgreSQL with the `pgvector` extension (SQLite is used automatically in local development when `DATABASE_URL` is unset).
**AI:** provider-abstracted chat + embeddings, disabled by default, safe to enable per environment.

<details>
<summary><strong>📁 Project layout</strong></summary>

```
app/
├── main.py                  # FastAPI app, routing, server-rendered public pages
├── core/                    # config, security, CSRF, business type catalog
├── db/                      # SQLAlchemy models and session management
├── routes/                  # one module per resource (auth, stores, cart, chat, …)
├── services/                # business logic: sales agent, invoices, payments, …
├── assets/fonts/            # Vazirmatn font, bundled for Persian PDF invoices
└── templates/                # Jinja2 templates for server-rendered pages

frontend/src/
├── pages/                    # route-level views, incl. seller/ dashboard
├── components/               # shared UI (layout, cart drawer, chat dock, …)
├── lib/                      # api client, auth, i18n engine, hooks
│   └── locales/              # 14 selectable locale catalogs
└── styles/                   # design-token based CSS

alembic/versions/             # one migration per schema change
tests/                        # 20 test modules, pytest
scripts/                      # seeding, backups, retention purge
docs/                         # architecture, deployment, backup, demo notes
```
</details>

---

## 🚀 Quick start

### Option A — Docker Compose (recommended)

```bash
# 1. Copy the environment template and fill in the required values
cp .env.example .env
#    at minimum, set SECRET_KEY and POSTGRES_PASSWORD

# 2. Start the database
docker compose up -d db

# 3. Apply migrations
docker compose run --rm migrate

# 4. Start the app
docker compose up -d app
```

The app is now on **http://localhost:8000**.

### Option B — Local development

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

docker compose up -d db            # or leave DATABASE_URL unset to use local SQLite
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                        # Vite dev server, proxies /api to :8000
```

### Seed demo data

```bash
python scripts/seed_demo.py
```

This creates a demo seller account and a fully stocked Persian storefront, so the landing page's live "stores" and "products" sections, the chat assistant, and checkout all have real data to show. See [docs/DEMO.md](docs/DEMO.md) for a scripted walkthrough.

---

## ⚙️ Configuration

All configuration is environment-driven — see [`.env.example`](.env.example) for the full list. A few groups worth knowing about:

<details>
<summary><strong>Core / security</strong></summary>

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` locally; `production` enables strict startup validation (`DATABASE_URL`, `SECRET_KEY`, `APP_ALLOWED_HOSTS` become mandatory) |
| `SECRET_KEY` | **Must** be set to a strong, stable value in any deployed environment — session tokens don't survive a key rotation |
| `APP_ALLOWED_HOSTS` | Comma-separated public hostnames (trusted-host protection) |
| `GOD_USER_EMAIL` | Email of the single verified platform God account; role elevation is server-managed and cannot be assigned through registration or the role API |
| `LOG_VERIFICATION_CODES` | Set to `true` to write email/SMS verification codes to application logs for deployment debugging. Disabled by default because log access exposes active OTPs; restrict access and retention when enabled |
| `SESSION_COOKIE_SECURE` / `SESSION_COOKIE_SAMESITE` | Production cookies are always `Secure` + `HttpOnly` + `SameSite=Lax`; `SameSite=None` is rejected unless secure cookies are enabled |
| `AUTH_RATE_LIMIT_REQUESTS` / `_WINDOW_SECONDS` | Login/registration rate limiting |

</details>

<details>
<summary><strong>AI chat &amp; retrieval</strong></summary>

Chat is **disabled by default** and never blocks the app from starting.

| Variable | Purpose |
|---|---|
| `AI_CHAT_PROVIDER` | `disabled`/`offline`/`mock` (built-in grounded assistant, no model needed) · `openai`, `openrouter`, `groq`, `together`, `deepseek`, `gemini`, `mistral` (OpenAI-compatible) · `ollama`, `lmstudio`, `custom` (local/self-hosted) · `anthropic` |
| `AI_CHAT_API_KEY` / `_MODEL` / `_ENDPOINT` / `_TIMEOUT_SECONDS` | Provider credentials and behavior |
| `AI_CHAT_RATE_LIMIT_REQUESTS` / `_WINDOW_SECONDS` / `_MAX_KEYS` | Per-client chat rate limiting (process-local; add a shared gateway/Redis policy for multi-worker deployments) |
| `AI_RAG_ENABLED` | Enables the optional hybrid semantic retrieval index (pgvector) |
| `AI_RAG_EMBEDDING_PROVIDER` | `hashing` (offline, no download) · `mock` · `local` (`sentence-transformers`) · `openai` |

If the chat provider is disabled, misconfigured, slow or returns something ungrounded, the assistant still answers: the built-in grounded assistant writes the reply from the store's real data (Persian or English). Provider details are never leaked.

Backfill semantic documents after enabling RAG:

```bash
alembic upgrade head
AI_RAG_ENABLED=true AI_RAG_EMBEDDING_PROVIDER=mock python -m app.services.semantic_index
```

</details>

<details>
<summary><strong>Payments, notifications &amp; storage</strong></summary>

| Variable | Purpose |
|---|---|
| `PAYMENT_PROVIDER` | Legacy platform default only; new payments use the provider selected per Store. `disabled` is the default; `mock` is development-only. |
| `PAYMENT_SECRET_<REFERENCE>` / `PAYMENT_API_URL` | Server-only provider secrets resolved by a Store credential reference, plus the ZarinPal API base URL. Do not commit these values. |
| `PAYMENT_CALLBACK_URL` | Public backend URL for ZarinPal returns, typically `https://your-domain/api/payments/callback`; a Store's ZarinPal account must also have a matching secret reference. |
| Marketplace settlement | NAVA selects a Store-specific adapter/account but does not split, escrow, or manually transfer proceeds. The selected provider must route and settle to the connected merchant. |
| `SMTP_*` | Outgoing email (verification codes, password reset) |
| `SMS_PROVIDER` / `SMS_WEBHOOK_URL` | Optional SMS verification channel |
| `CLOUDINARY_*` | Product image hosting |
| `CONVERSATION_RETENTION_DAYS` | How long chat messages are kept before `scripts/purge_conversation_messages.py` removes them |

</details>

> ⚠️ **Note on store visibility:** the current schema has no publish/unpublish flag — every store is public to the chat page and storefront by design in this MVP. Making stores private is a deliberate, separate schema migration.

---

## 🔌 API reference

The full interactive schema is always available at **`/docs`** (Swagger UI) and **`/redoc`** once the server is running. High-level map:

| Prefix | Covers |
|---|---|
| `/api/auth` | Register, login, email/SMS verification, password reset |
| `/api/stores`, `/api/store-management` | Store CRUD, business-type-driven product schema |
| `/api/products` | Seller product management |
| `/api/business-types` | The 49 built-in business templates and their attribute schemas |
| `/api/faqs`, `/api/knowledge-base` | Content the assistant answers from |
| `/api/cart`, `/api/orders` | Guest and authenticated cart/checkout |
| `/api/seller/orders`, `/api/dashboard` | Seller-side order management and overview stats |
| `/api/conversations` | Seller access to chat transcripts |
| `/api/payments` | Payment initiation and callback handling |
| `/public/stores/{id}`, `/public/stores/{id}/catalog` | Public storefront data |
| `/public/stores/{id}/chat` | The AI assistant endpoint (`POST {"question": "..."}`) |
| `/public/showcase` | Random live stores/products, used by the landing page |
| `/health/live`, `/health/ready`, `/health/db` | Liveness, readiness, and (authenticated) DB diagnostics |

**Guest commerce**, in short: a cryptographically random conversation token is the store-scoped identity for a guest's cart and orders. Public cart APIs accept `X-Guest-Token`; guest checkout additionally requires an `Idempotency-Key` header; guest order lookup verifies both the token and the store. The chat assistant executes cart/checkout/order actions deterministically through these same code paths — the AI provider never controls a price, a stock level, or whether an order gets created.

---

## 🧪 Testing

```bash
# Backend — full suite
pytest -q

# Backend — a single module
pytest tests/test_invoice_service.py -q

# Backend — skip tests that need a real PostgreSQL database
pytest -q -m "not postgres"

# Static sanity check
python -m compileall -q app tests

# Frontend
cd frontend
npm test
```

The suite spans 20 modules covering routes, services, security hardening (CSRF, rate limits, idempotency), guest-commerce isolation, PDF invoice rendering, and PostgreSQL-specific concurrency behavior.

---

## 📦 Deployment

- Build the production image with the included `Dockerfile` (multi-stage: builds the frontend with Node 22, then installs the backend on `python:3.12-slim`, running as a non-root user).
- Run database migrations as a **separate, controlled release step** (`alembic upgrade head`) — don't rely on the app auto-migrating in production.
- Put the app behind an HTTPS reverse proxy; it trusts `X-Forwarded-*` headers only from `FORWARDED_ALLOW_IPS`.
- The chat and auth rate limiters are process-local by default — for multiple workers/instances, enforce a shared limit at the reverse proxy or API gateway.
- `docker-compose.yml` as shipped starts the database (bound to loopback) plus an `app`/`migrate` pair; it's meant for local development, not a complete production topology.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full checklist and [docs/BACKUP.md](docs/BACKUP.md) for the PostgreSQL backup script.

---

## 🌍 Internationalization

The language selector offers **14 locales**: Persian, English, Spanish, German, French, Russian, Arabic, Chinese, Portuguese, Korean, Japanese, Dutch, Turkish, and Hindi. Persian and Arabic use right-to-left direction; the others use left-to-right. Translation coverage differs between catalogs, and missing messages fall back to English. Locale metadata and catalogs live in `frontend/src/lib/i18n.jsx` and `frontend/src/lib/locales/`.

---

## 📚 Further reading

| Doc | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design notes |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment checklist |
| [docs/BACKUP.md](docs/BACKUP.md) | PostgreSQL backup/restore procedure |
| [docs/DEMO.md](docs/DEMO.md) | Reproducible sales/demo walkthrough |
| [docs/SALES.md](docs/SALES.md) | Buyer-facing positioning notes |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | Third-party assets and dependency license handling |
| [SECURITY.md](SECURITY.md) | Private vulnerability reporting |
| [docs/COMMERCIAL_TRANSFER.md](docs/COMMERCIAL_TRANSFER.md) | Sale, assignment, and secure project handover checklist |
| [docs/GITHUB_PROTECTION.md](docs/GITHUB_PROTECTION.md) | Repository access and branch protection checklist |

---

## 🤝 Contributing

This is proprietary software. Do not submit code, assets, or documentation unless you have first agreed in writing with the copyright holder on contribution and intellectual-property terms. A pull request or public discussion alone does not transfer copyright or grant permission to use this project. Do not submit material copied from third parties unless its license and required notices have been reviewed.

For authorized contributors, run these checks before submitting:

```bash
pytest -q
python -m compileall -q app tests
cd frontend && npm test && npm run build
```

## 📄 License

NAVA's original code, documentation, branding, and project-created assets are proprietary and **all rights are reserved** by Kourosh Beheshtinejad, subject to proof of chain of title and any written agreements. No permission to use, copy, modify, distribute, host, sublicense, or commercialize those materials is granted by this repository. See the root [LICENSE](LICENSE) for the notice and limitations.

Third-party dependencies and assets are not relicensed by NAVA's proprietary terms. They remain governed by their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), the dependency manifests/lockfiles, and the bundled [Vazirmatn OFL 1.1 license](app/assets/fonts/LICENSE.txt). The custom proprietary notice may not be automatically recognized by GitHub's license detector; the root `LICENSE` file is authoritative. Public repository visibility exposes source code and is not a technical copy-prevention measure. Keep the repository private if source access must be restricted, and configure GitHub protections as described in [docs/GITHUB_PROTECTION.md](docs/GITHUB_PROTECTION.md).

This notice is not a substitute for legal advice or a signed agreement. A sale or transfer of the project requires a separately executed written agreement describing exactly which copyrights, trademarks, domains, data, accounts, and third-party rights are included.

---

<div align="center">

Built for stores that would rather talk to their customers than make them dig through menus.

</div>
