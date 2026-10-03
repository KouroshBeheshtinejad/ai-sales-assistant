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

## مجوزهای فروشگاهی و ممیزی

`User.role` نقش پلتفرمی را نگه می‌دارد؛ مجوزهای هر فروشگاه از `StoreMembership.role`
و وضعیت `approved` همان membership محاسبه می‌شوند. مالک واقعی `Store.owner_id` در
همان فروشگاه اختیار کامل دارد و God از policy پلتفرمی عبور می‌کند. نگاشت نقش به
permission در `app/security/permissions.py` و query scope مشترک در
`app/security/policies.py` قرار دارد. نقش‌های `store_manager` و `store_viewer` در
همان policy قابل استفاده‌اند، اما ایجاد و مدیریت membership آن‌ها باید از مسیر
مالک/ادمین مجاز انجام شود.

تغییر نقش و approval کاربر، تصمیم عضویت فروشگاه، حذف محصول، تغییر وضعیت سفارش،
ساخت/ویرایش store و product، تغییر لوگو/تصویر، تغییرات FAQ/Knowledge و workflow پشتیبانی در `audit_logs` ثبت می‌شوند. متن خام
پاسخ FAQ و دانش در log ذخیره نمی‌شود؛ hash محتوا نگهداری می‌شود. داشبورد God فقط
از entityها و فیلدهای allowlist‌شده برای جست‌وجو و مشاهده استفاده می‌کند؛ query
SQL آزاد و CRUD عمومی روی ORM در دسترس UI نیست. رکوردهای store، product، order،
membership، FAQ و knowledge از داشبورد God به ویرایشگرهای domain موجود هدایت
می‌شوند تا audit، permission و invariantهای پرداخت، موجودی و روابط رکوردها حفظ شود.
چرخه membership شامل افزودن حساب ثبت‌شده، approval/rejection، تغییر نقش، تعلیق،
لغو و فعال‌سازی مجدد است؛ تغییرهای privileged، `token_version` کاربر را افزایش
می‌دهند و نشست‌های قبلی را باطل می‌کنند.

انتقال مالکیت store فقط توسط God و به حساب verified/active انجام می‌شود؛ مالک
قبلی و مالک جدید نشست تازه می‌خواهند و انتقال در audit ثبت می‌شود. God system
overview از شمارش واقعی user/store/order/payment/support و probe پایگاه داده ساخته
می‌شود. مدیریت داده از طریق ویرایشگرهای domain موجود انجام می‌شود؛ ویرایش خام
payment/order یا اجرای SQL عمداً ارائه نشده است.

## پشتیبانی

درخواست‌های پشتیبانی نوعی از `Conversation` موجود هستند و از `Message` مشترک
استفاده می‌کنند. وضعیت‌های صف شامل `new`، `assigned`، `waiting_customer`,
`waiting_support`، `resolved` و `closed` هستند. مشتری فقط گفتگوهای خودش را می‌بیند؛
agent باید ticket را به‌شکل اتمیک claim کند تا پاسخ یا تغییر وضعیت بدهد. تغییرهای
JSON با cookie session در همه‌ی routeها و aliasهای API به `X-CSRF-Token` و CSRF
cookie نیاز دارند؛ endpointهای ورود/ثبت‌نام/تأیید/بازیابی گذرواژه با اعتبارسنجی
مستقل خودشان کار می‌کنند و token نشست دسترسی همچنان HttpOnly است. مدیر فروشگاه
نیز با permission `support.contact` می‌تواند از shell مشترک به پشتیبانی پیام دهد.
owner/adminهای همان فروشگاه می‌توانند یک thread پشتیبانی مشترک را ببینند و پاسخ
دهند؛ دسترسی از `support.contact` همان membership می‌آید و کارکنان فروشگاه دیگر
به آن thread دسترسی ندارند. شمارنده‌ی header از ticketهای واقعی نیازمند اقدام
برای همان user/agent محاسبه می‌شود.

## محدودکننده نرخ

محدودکننده‌های login، chat و tracking از Redis در صورت پیکربندی `REDIS_URL` استفاده
می‌کنند. توسعه بدون Redis به حافظه‌ی همان process برمی‌گردد؛ production وجود Redis
را الزامی می‌کند و fallback توزیع‌شده محسوب نمی‌شود.


## معماری دستیار هوش مصنوعی (نسخهٔ جدید)

1. `chat_flow.py` — سبد خرید، تسویه و پیگیری سفارش به‌صورت قطعی (بدون مدل) اجرا می‌شود.
2. `sales_agent.py` — تشخیص تزریق پرامپت → intent → retrieval → فراخوانی مدل با ابزارها (حداکثر ۴ دور) → بررسی «زمینه‌دار بودن» اعداد → در صورت هر مشکل، پاسخ آفلاین.
3. `chat_retrieval.py` — RAG ترکیبی: BM25F با وزن عنوان، تحمل غلط املایی، مترادف‌های فارسی/انگلیسی، مفاهیم (ارسال/مرجوعی/گارانتی/...)، بودجه («زیر ۳ میلیون»)، بیشترین/کمترین قیمت، پرسش‌های ادامه‌دار («قیمتش؟»)، قطعه‌بندی متن‌های بلند و ادغام اختیاری با جست‌وجوی معنایی.
4. `grounded_responder.py` — «مغز آفلاین»: پاسخ روان از دادهٔ واقعی؛ پایهٔ `MockLLMProvider` و شبکهٔ اطمینان برای همهٔ مدل‌ها.
5. `llm_provider.py` — OpenAI-compatible (OpenAI، OpenRouter، Groq، DeepSeek، Gemini، Ollama، ...) و Anthropic با retry و circuit breaker.
