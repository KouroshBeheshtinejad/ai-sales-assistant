# معماری NAVA

FastAPI مسیرهای HTTP و قالب‌های Jinja را ارائه می‌کند. SQLAlchemy مدل‌های User، Store، Product، FAQ، Knowledge Base، Conversation، Cart و Order را مدیریت می‌کند و Alembic تغییرات schema را version می‌کند.

جریان چت: ورودی عمومی -> rate limit -> ConversationService -> SalesAgentService -> تشخیص intent -> retrieval محدود به `store_id` -> provider abstraction -> ذخیره Message. قیمت و موجودی از متن مدل گرفته نمی‌شوند و باید از سرویس‌های تراکنشی خوانده شوند.

جریان سفارش: CartService مالکیت فروشگاه/محصول، active بودن و stock را بررسی می‌کند؛ OrderService مبلغ را از قیمت trusted محصول محاسبه و price snapshot را در OrderItem نگه می‌دارد؛ SellerOrderService مالکیت seller را قبل از مشاهده یا تغییر status بررسی می‌کند.

برای چند فروشگاه، همه‌ی queryهای عمومی و فروشنده باید با `store_id` یا مالک فروشگاه محدود شوند. Semantic index فقط index غیرمرجع است و PostgreSQL/pgvector اختیاری است.

## Guest commerce

برای مشتری مهمان، همان token تصادفی conversation به cart و order منتقل می‌شود.
درخواست‌های عمومی token را در `X-Guest-Token` می‌فرستند. Cart و Order هم‌زمان
با `user_id` یا `guest_token` شناسه دارند و قیود store-scoped مانع دسترسی متقاطع
می‌شوند. conversation دارای stateهای `idle`، `awaiting_customer`,
`awaiting_confirmation` و `completed` است. فقط state تأییدشده اجازه‌ی ساخت order
می‌دهد و کلید idempotency از ثبت تکراری جلوگیری می‌کند.
