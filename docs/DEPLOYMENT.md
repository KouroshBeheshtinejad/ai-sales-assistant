# استقرار و تحویل

## محلی / Docker

فایل `.env.example` را به `.env` تبدیل کنید و مقادیر امن بدهید، سپس `docker compose up -d --build` را اجرا کنید. سرویس application قبل از startup، `alembic upgrade head` را اجرا می‌کند. برای اجرای مستقیم برنامه: `uvicorn app.main:app --host 0.0.0.0 --port 8000`. برای production از `Dockerfile` بدون reload و پشت reverse proxy با HTTPS استفاده کنید.

## کنترل‌های production

`APP_ENV=production`، `DATABASE_URL`، `SECRET_KEY` قوی و `APP_ALLOWED_HOSTS` را الزامی کنید. پورت PostgreSQL را عمومی نکنید، provider key را فقط در secret manager/environment قرار دهید، لاگ‌ها را بدون password/API key نگه دارید و health checkهای `/health/live` و `/health/ready` را monitor کنید.

## migration و backup

Migrationها در release step جداگانه با `alembic upgrade head` اجرا شوند. قبل از migration یا release از PostgreSQL dump بگیرید. دامنه، HTTPS، cookie امن و محدودیت rate در reverse proxy باید فعال باشد.

این مخزن در محیط فعلی به اینترنت deploy نشده است و وضعیت آن `READY FOR DEPLOYMENT` است.
