# پشتیبان‌گیری و بازیابی

## Backup

روی میزبان PostgreSQL:

```bash
pg_dump --format=custom --file=nava-$(date +%F).dump "$DATABASE_URL"
```

فایل dump را خارج از سرور اصلی و با دسترسی محدود نگه دارید. `.env` را در مخزن commit نکنید؛ secretها را جداگانه و امن نگه دارید.

## Restore

یک دیتابیس خالی بسازید و dump را بازیابی کنید:

```bash
pg_restore --clean --if-exists --dbname="$DATABASE_URL" nava-YYYY-MM-DD.dump
alembic upgrade head
```

بازیابی را دوره‌ای روی محیط staging تمرین کنید و پس از restore، `/health/ready` و یک smoke test عمومی/فروشنده را اجرا کنید.
