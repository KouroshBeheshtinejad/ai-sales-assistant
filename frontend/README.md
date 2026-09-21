# NAVA Frontend

React 18 + Vite 5 + React Router 6. Persian (RTL) by default, English available. No UI framework, no state library.

## اجرا

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxy to FastAPI on :8000)
npm run build      # output: frontend/dist, served by FastAPI
```

Environment (optional): `VITE_BACKEND_URL` (dev proxy target, default `http://127.0.0.1:8000`), `VITE_DEMO_STORE_ID` (store linked from the landing page, default `1`).

## Routes (match the paths `app/main.py` serves `index.html` for)

| Path | Page |
| --- | --- |
| `/`, `/landing` | Landing |
| `/login`, `/register` | Sign in, sign up, OTP verification, password reset (steps inside the page) |
| `/track` | Order tracking by 10-digit number |
| `/store/:id`, `/store/:id/product/:productId` | Storefront, product page, cart drawer, checkout, payment, assistant |
| `/seller` | Overview and store settings |
| `/seller/orders`, `/seller/order/:id` | Orders and status transitions |
| `/seller/conversations`, `/seller/conversation/:id` | Assistant conversations |
| `/seller/products` | Products, with fields generated from the store's business type |
| `/seller/knowledge` | Knowledge entries and FAQs (tabs) |

## Layout

```
src/lib        api.js (fetch + error parsing), session/auth (JWT), guest (per-store token),
               useShop (catalog + guest cart), i18n (fa/en, formatting), hooks, orders
src/components ui (buttons, fields, modal, toast...), Layout, ChatDock, CartDrawer, ProductCard
src/pages      Landing, Auth, Track, StoreShell/StoreHome/ProductPage, seller/*
```

## How it talks to the backend

- **Guest identity**: a guest token is the token of a store-scoped `Conversation`, so it is kept per store in `localStorage` (`nava_guest_token_{storeId}`, the same key the server-rendered page uses). The API only creates one through the chat endpoint, so the first cart action sends the deterministic "view cart" message, which needs no LLM call.
- **Checkout**: one `Idempotency-Key` per checkout attempt; retries cannot create duplicate orders. Payment uses `payment_url` when the gateway returns one, otherwise the sandbox confirm step.
- **Seller session**: Bearer JWT in `localStorage`, expiry read from the token; any 401 signs the seller out and redirects to `/login?next=...`.
- Timestamps from the API are naive UTC; they are parsed as UTC before formatting.

## Backend gaps noticed (not changed)

1. `app/main.py` lists SPA routes one by one. Any new frontend route needs a matching entry, or a single catch-all registered after all routers:
   ```python
   @app.get("/{path:path}", include_in_schema=False)
   def spa_fallback(path: str):
       if path.startswith(("auth/", "stores/", "products/", "cart/", "orders/", "payments/", "public/", "seller/orders/", "seller/conversations/", "business-types", "health")):
           raise HTTPException(status_code=404)
       return FileResponse(frontend_dist / "index.html")
   ```
2. There is no "resend verification code" endpoint: an account whose code expired (10 min) cannot be verified.
3. A guest session can only be created through `/public/stores/{id}/chat`; a dedicated `POST /public/stores/{id}/session` would be cleaner.
4. `ConversationService.get_history` orders ascending and then applies `limit`, so it returns the *first* 20 messages, not the latest.
