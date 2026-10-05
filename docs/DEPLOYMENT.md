# استقرار و تحویل

## محلی / Docker

فایل `.env.example` را به `.env` تبدیل کنید و مقادیر امن بدهید، سپس `docker compose up -d --build` را اجرا کنید. سرویس `migrate` قبل از application، `alembic upgrade head` را اجرا می‌کند و application تا موفقیت آن منتظر می‌ماند. برای اجرای مستقیم برنامه: `uvicorn app.main:app --host 0.0.0.0 --port 8000`. برای production از `Dockerfile` بدون reload و پشت reverse proxy با HTTPS استفاده کنید.

## کنترل‌های production

`APP_ENV=production`، `DATABASE_URL`، `SECRET_KEY` قوی و `APP_ALLOWED_HOSTS` را الزامی کنید. پورت PostgreSQL را عمومی نکنید، provider key را فقط در secret manager/environment قرار دهید، لاگ‌ها را بدون password/API key نگه دارید و health checkهای `/health/live` و `/health/ready` را monitor کنید.

برای دسترسی سراسری God، `GOD_USER_EMAIL` را در secret manager روی ایمیل حساب تأییدشده‌ی خودتان تنظیم کنید. این نقش در API قابل واگذاری نیست؛ God می‌تواند از `/api/admin/users` نقش `support` یا `seller` را مدیریت کند. نقش Support فقط فهرست سفارش‌های نهایی‌شده را می‌خواند. آدرس بازگشت درگاه را روی `/api/payments/callback` تنظیم کنید. ساعت فاکتور فارسی همیشه تهران و شمسی است؛ چهار زبان دیگر از timezone مرورگر خریدار استفاده می‌کنند.

پرداخت بر اساس تنظیم هر Store انتخاب می‌شود. Merchant ID زرین‌پال از پنل Store دریافت و با `PAYMENT_CREDENTIAL_ENCRYPTION_KEY` در دیتابیس رمز می‌شود؛ این کلید را فقط در secret manager نگه دارید، بین replicaها یکسان تنظیم کنید و بدون برنامه مهاجرت تغییر ندهید. دستور ساخت کلید در `.env.example` است. `PAYMENT_CALLBACK_URL` باید عمومی و HTTPS باشد. Merchant ID از API به frontend برنمی‌گردد؛ referenceهای قدیمی `PAYMENT_SECRET_<REFERENCE>` فقط برای سازگاری پشتیبانی می‌شوند و نمی‌توانند بین Storeها مشترک باشند. ZarinPal create، inquiry و verify از credential snapshot همان Store/Payment استفاده می‌کنند. Inquiry فقط وضعیت را می‌خواند و `PAID` نیز برای نهایی‌شدن باید server-side verify شود؛ `unknown` pending می‌ماند. Reverse فقط برگشت کامل تا ۳۰ دقیقه را پشتیبانی می‌کند؛ partial/late refund انجام نمی‌شود. `PAYMENT_PROVIDER=mock` فقط برای توسعه است و adapterهای بین‌المللی فعال نیستند.

برای ثبت کدهای تأیید email/SMS در log محیط deploy، `LOG_VERIFICATION_CODES=true` را تنظیم کنید. این گزینه به‌طور پیش‌فرض خاموش است؛ با روشن‌کردنش OTP فعال وارد log می‌شود، بنابراین دسترسی به logها را محدود کنید و retention کوتاه داشته باشید.

اعلان سفارش از مرز `notification_service` عبور می‌کند. مقدار پیش‌فرض
`CONVERSATION_RETENTION_DAYS=90` روز با job زیر پاک می‌شوند. سوابق سفارش و invoice
برای نیازهای قانونی/عملیاتی حذف نمی‌شوند:

```bash
CONVERSATION_RETENTION_DAYS=90 python scripts/purge_conversation_messages.py
```
`SMS_PROVIDER=disabled` است؛ تا زمان انتخاب vendor واقعی، هیچ credential یا API
فرضی اضافه نشده و شکست اعلان روی تراکنش سفارش اثر نمی‌گذارد.

## migration و backup

Migrationها در release step جداگانه با `alembic upgrade head` اجرا شوند. قبل از migration یا release از PostgreSQL dump بگیرید. دامنه، HTTPS، cookie امن و محدودیت rate در reverse proxy باید فعال باشد.

این مخزن در محیط فعلی به اینترنت deploy نشده است؛ قبل از production باید credentialهای provider، backup/restore و migration smoke test محیط مقصد تأیید شوند.
