"""Create the reproducible Persian fashion demo store.

Run after migrations: python scripts/seed_demo.py
"""
from decimal import Decimal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.db.models import FAQ, KnowledgeBaseEntry, Product, Store, User

PRODUCTS = [
    ("کتونی مشکی آریا", "کتونی سبک روزمره با زیره مقاوم", "مشکی", "۴۲،۴۳،۴۴", 2450000, 12),
    ("کتونی سفید پارس", "مناسب استفاده روزانه و استایل مینیمال", "سفید", "۴۰،۴۱،۴۲", 2190000, 8),
    ("هودی زغالی پاییز", "هودی گرم و نرم با فرم آزاد", "زغالی", "M،L،XL", 1350000, 15),
    ("شلوار جین کلاسیک", "جین آبی تیره با دوخت بادوام", "آبی تیره", "۳۰،۳۲،۳۴", 1790000, 10),
    ("کاپشن کوتاه نوآ", "کاپشن سبک ضدباد برای استفاده شهری", "سبز زیتونی", "M،L،XL", 3290000, 6),
    ("تی‌شرت پنبه‌ای ساده", "پارچه پنبه‌ای خنک و مناسب استفاده روزمره", "کرم", "M،L", 690000, 20),
    ("کوله پشتی شهری", "کوله سبک با محفظه لپ‌تاپ", "خاکستری", "یک سایز", 1890000, 7),
    ("شال بافت زمستانی", "بافت نرم و گرم برای روزهای سرد", "آجری", "یک سایز", 590000, 14),
    ("کمربند چرم طبیعی", "چرم طبیعی با سگک فلزی مات", "قهوه‌ای", "فری‌سایز", 850000, 9),
    ("عینک آفتابی فریم‌مشکی", "فریم سبک با لنز UV400", "مشکی", "یک سایز", 1120000, 5),
]


def main():
    db = SessionLocal()
    try:
        email = "demo@nava.example.com"
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email, password_hash=hash_password("NavaDemo123!"))
            db.add(user)
            db.flush()
        store = db.query(Store).filter(Store.owner_id == user.id, Store.name == "بوتیک ناوا").first()
        if store is None:
            store = Store(name="بوتیک ناوا", description="فروشگاه پوشاک و اکسسوری شهری با ارسال به سراسر ایران.", business_type="clothing", owner_id=user.id)
            db.add(store)
            db.flush()
        if not store.products:
            for name, description, color, size, price, stock in PRODUCTS:
                db.add(Product(name=name, description=description, color=color, size=size, price=Decimal(price), stock=stock, store_id=store.id, is_active=True))
            db.add_all([
                FAQ(store_id=store.id, question="ارسال سفارش چقدر طول می‌کشد؟", answer="ارسال تهران یک تا دو روز کاری و شهرهای دیگر دو تا چهار روز کاری زمان می‌برد."),
                FAQ(store_id=store.id, question="شرایط مرجوعی چیست؟", answer="تا هفت روز پس از تحویل، کالا با حفظ شرایط اولیه و فاکتور قابل مرجوعی است."),
                KnowledgeBaseEntry(store_id=store.id, title="پرداخت", content="پرداخت هنگام ثبت سفارش هماهنگ می‌شود و پشتیبانی فروشگاه پاسخ‌گوی روش‌های پرداخت است."),
                KnowledgeBaseEntry(store_id=store.id, title="راهنمای انتخاب", content="برای انتخاب سایز کفش، سایز معمول خود را اعلام کنید؛ برای هودی و تی‌شرت، اندازه آزاد پیشنهاد می‌شود."),
            ])
        db.commit()
        print(f"Demo store ready: id={store.id}, url=/public/stores/{store.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
