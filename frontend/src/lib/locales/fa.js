import { parseCatalog } from './parse'

export default parseCatalog(`
# ---- core
brand = ناوا
loading = در حال بارگذاری…
retry = تلاش دوباره
close = بستن
copy = کپی
copied = کپی شد
cancel = انصراف
create = ایجاد
save = ذخیره
saved = ذخیره شد
edit = ویرایش
delete = حذف
deleted = حذف شد
yes = بله
no = خیر
show = نمایش
hide = پنهان
select = انتخاب کنید…
active = فعال
inactive = غیرفعال
optional = اختیاری
a11y.skip = پرش به محتوا
confirm.sure = مطمئن هستید؟
crash.title = مشکلی پیش آمد
notfound.title = صفحه پیدا نشد
notfound.home = بازگشت به صفحه اصلی

# ---- errors
err.generic = مشکلی پیش آمد. لطفاً دوباره تلاش کنید.
err.network = خطای شبکه. اتصال اینترنت را بررسی کنید و دوباره تلاش کنید.
err.rate = تعداد درخواست‌ها زیاد است. کمی صبر کنید و دوباره تلاش کنید.
err.auth = لطفاً دوباره وارد شوید.
err.notFound = چیزی که دنبالش بودید پیدا نشد.
err.server = سرور با مشکل روبه‌رو شد. لطفاً بعداً دوباره تلاش کنید.
err.m.invalidCredentials = ایمیل یا رمز عبور اشتباه است.
err.m.emailTaken = این ایمیل قبلاً ثبت شده است.
err.m.invalidCode = کد نامعتبر است یا منقضی شده است.
err.m.invalidReset = توکن بازیابی نامعتبر است یا منقضی شده است.
err.m.needVerify = ابتدا حساب خود را تأیید کنید.
err.m.sessionExpired = نشست شما منقضی شده است. دوباره وارد شوید.
err.m.stock = موجودی این محصول کافی نیست.
err.m.cartEmpty = سبد خرید شما خالی است.
err.m.inactive = این محصول در دسترس نیست.
err.m.qty = تعداد باید بین ۱ تا ۱۰۰ باشد.
err.m.image = تصویر پشتیبانی نمی‌شود یا حجمش زیاد است.
err.m.paid = این سفارش قبلاً پرداخت شده است.
err.m.notPending = فقط سفارش‌های در انتظار قابل پرداخت هستند.
err.m.guest = نشست خرید شما منقضی شده است. لطفاً دوباره تلاش کنید.

# ---- navigation and header
nav.main = منوی اصلی
nav.features = امکانات
nav.how = نحوه کار
nav.stores = فروشگاه‌ها
nav.demo = دموی زنده
nav.faq = سوالات متداول
nav.track = پیگیری سفارش
nav.login = ورود
nav.register = شروع کنید
nav.panel = پنل فروشنده
nav.langName = زبان
nav.menu = منو
nav.openMenu = باز کردن منو
nav.closeMenu = بستن منو
nav.home = صفحه اصلی ناوا

# ---- landing: hero
landing.badge = تجارت گفتگومحور با هوش مصنوعی
landing.title = بازدیدکننده فروشگاه را با یک گفتگو به مشتری تبدیل کنید
landing.lead = ناوا دستیار فروش هوشمند فروشگاه‌های آنلاین است. از کاتالوگ و قوانین خود فروشگاه پاسخ می‌دهد، سبد خرید را پر می‌کند، سفارش را ثبت می‌کند و فاکتور همراه با کد رهگیری صادر می‌کند؛ به پنج زبان و شبانه‌روز.
landing.cta = فروشگاه دمو را امتحان کنید
landing.ctaSeller = فروشگاه خود را بسازید
landing.b1 = قیمت و موجودی همیشه مستقیم از پایگاه داده می‌آید
landing.b2 = خرید مهمان بدون نیاز به حساب کاربری
landing.b3 = پنج زبان آماده استفاده
landing.q1 = هودی مشکی سایز L دارید؟
landing.a1 = بله، هودی مشکی سایز L موجود است (۳ عدد مانده) و قیمتش ۸۹۰٬۰۰۰ تومان است. به سبد خریدتان اضافه کنم؟
landing.q2 = بله، اضافه کن.
landing.a2 = انجام شد. سبد خرید شما ۱ کالا دارد و جمع کل ۸۹۰٬۰۰۰ تومان است. برای ثبت سفارش نام، شماره تماس و آدرستان را بفرستید.
landing.chipStock = موجود
landing.chipOrder = سفارش تأیید شد
landing.chipTracking = کد رهگیری صادر شد

# ---- landing: stats
landing.stat.stores = فروشگاه فعال
landing.stat.products = کالای آماده فروش
landing.stat.types = قالب کسب‌وکار
landing.stat.languages = زبان

# ---- landing: how it works
landing.how = نحوه کار
landing.howLead = از اولین پرسش تا تحویل سفارش، در چهار قدم.
landing.h1 = کاتالوگ را وصل کنید
landing.d1 = محصولات، سوالات متداول و دانش فروشگاه را از پنل فروشنده اضافه کنید. دستیار فقط چیزی را می‌داند که شما به او بدهید.
landing.h2 = مشتری می‌پرسد
landing.d2 = خریداران درباره محصول، سایز، قیمت و قوانین گفتگو می‌کنند؛ بدون نیاز به ثبت‌نام.
landing.h3 = دستیار می‌فروشد
landing.d3 = دستیار محصول مناسب را پیدا می‌کند، سبد را پر می‌کند و اطلاعات تحویل را می‌گیرد؛ قیمت و موجودی را هر بار از پایگاه داده می‌خواند.
landing.h4 = شما ارسال می‌کنید
landing.d4 = سفارش‌ها با فاکتور و کد رهگیری به پنل شما می‌رسند. آن‌ها را از «در انتظار» تا «تحویل شد» پیش ببرید.

# ---- landing: features
landing.features = هر آنچه فروشگاه برای فروش از راه گفتگو نیاز دارد
landing.featuresLead = یک پلتفرم برای دستیار، ویترین و پشت‌صحنه فروشگاه.
landing.f1.t = پاسخ از داده‌های خود شما
landing.f1.d = جست‌وجو فقط میان محصولات، سوالات متداول و پایگاه دانش همان فروشگاه انجام می‌شود و هرگز به فروشگاه دیگری نمی‌رسد. جست‌وجوی معنایی اختیاری، پرسش‌های بازنویسی‌شده را هم می‌فهمد.
landing.f2.t = قیمت و موجودی قابل اعتماد
landing.f2.d = مدل زبانی هیچ‌وقت قیمت یا موجودی نمی‌سازد. هر دو در لحظه پاسخ از پایگاه داده خوانده می‌شوند.
landing.f3.t = سبد خرید و پرداخت در چت
landing.f3.d = افزودن، تغییر و حذف کالا، تأیید اطلاعات تحویل و ثبت سفارش، بدون خروج از گفتگو.
landing.f4.t = سفارش، فاکتور، رهگیری
landing.f4.d = برای هر سفارش فاکتور PDF و کد رهگیری ۱۰ رقمی صادر می‌شود که مشتری هر زمان می‌تواند پیگیری کند.
landing.f5.t = پنل فروشنده واقعی
landing.f5.d = محصولات، موجودی، سفارش‌ها و گفتگوها را مدیریت کنید و با خواندن چت‌ها بفهمید مشتری‌ها واقعاً چه می‌پرسند.
landing.f6.t = قالب برای {n} نوع کسب‌وکار
landing.f6.d = پوشاک، کافه، داروخانه، لوازم برقی، خدمات و بیشتر. فرم محصول با نوع کسب‌وکار شما تطبیق پیدا می‌کند.
landing.f7.t = پنج زبان
landing.f7.d = کل رابط به فارسی، انگلیسی، اسپانیایی، آلمانی و فرانسوی در دسترس است و چیدمان راست‌به‌چپ هم پشتیبانی می‌شود.
landing.f8.t = ساخته‌شده با ملاحظات امنیتی
landing.f8.d = محدودیت نرخ درخواست، حفاظت CSRF، ثبت سفارش بدون تکرار، حساب‌های تأییدشده و حذف خودکار پیام‌های قدیمی گفتگو.

# ---- landing: assistant
landing.assistant = فروشنده‌ای که هرگز نمی‌خوابد
landing.assistantBody = دستیار مثل بهترین فروشنده مغازه رفتار می‌کند: گوش می‌دهد، قفسه را نگاه می‌کند و بعد پاسخ می‌دهد.
landing.can1 = بر اساس نیاز، سایز، رنگ یا بودجه محصول پیشنهاد می‌دهد
landing.can2 = پیش از پاسخ، موجودی و قیمت را زنده بررسی می‌کند
landing.can3 = به پرسش‌های ارسال و بازگشت کالا از روی سوالات متداول شما پاسخ می‌دهد
landing.can4 = پس از تأیید مشتری سفارش را ثبت می‌کند
landing.q3 = ارسال چند روز طول می‌کشد؟
landing.a3 = طبق سوالات متداول این فروشگاه، سفارش‌ها ظرف دو روز کاری ارسال می‌شوند و معمولاً سه تا پنج روزه به دست مشتری می‌رسند.
landing.q4 = سفارش ۴۸۲۱۹۰۳۳۵۷ من کجاست؟
landing.a4 = سفارش ۴۸۲۱۹۰۳۳۵۷ ارسال شده است. هر زمان می‌توانید آن را در صفحه پیگیری دنبال کنید.

# ---- landing: showcase
landing.stores = فروشگاه‌های ناوا
landing.storesLead = مجموعه‌ای تصادفی از فروشگاه‌های فعال. برای دیدن فروشگاه‌های دیگر، دکمه را بزنید.
landing.shuffle = نمایش موارد دیگر
landing.visit = مشاهده فروشگاه
landing.productsCount = {n} محصول
landing.storesEmpty = هنوز فروشگاهی ثبت نشده است. اولین فروشگاه را شما بسازید.
landing.products = تازه از قفسه‌ها
landing.productsLead = محصولاتی تصادفی از فروشگاه‌ها، مستقیم از پایگاه داده.
landing.productsEmpty = به‌محض اینکه فروشگاه‌ها محصول اضافه کنند، اینجا نمایش داده می‌شود.
landing.by = از {store}

# ---- landing: business types
landing.types = برای هر نوع کسب‌وکاری ساخته شده
landing.typesLead = یک پلتفرم، {n} قالب آماده برای محصولات.
landing.typesMore = +{n} مورد دیگر

# ---- landing: sellers and buyers
landing.sellers = برای فروشندگان
landing.sellersBody = بدون استخدام نیرو، برای هر بازدیدکننده یک فروشنده باتجربه داشته باشید.
landing.s1 = در چند دقیقه فروشگاه بسازید؛ بدون نیاز به برنامه‌نویس
landing.s2 = با سوالات متداول و مطالب دانشی به دستیار آموزش بدهید
landing.s3 = همه سفارش‌ها، گفتگوها و هشدار کمبود موجودی را یک‌جا ببینید
landing.buyers = برای خریداران
landing.buyersBody = مثل مغازه بپرسید و پاسخ روشن بگیرید.
landing.y1 = درباره محصول، سایز و قیمت به زبان خودتان بپرسید
landing.y2 = به‌صورت مهمان خرید کنید و سفارش را با کد رهگیری پیگیری کنید
landing.y3 = فاکتور خود را به‌صورت PDF دریافت کنید

# ---- landing: faq
landing.faq = سوالات متداول
faq.q1 = ناوا چیست؟
faq.a1 = ناوا یک دستیار فروش هوشمند و ویترین برای فروشگاه‌های آنلاین است. مشتری با دستیار گفتگو می‌کند، سبد را پر می‌کند و سفارش می‌دهد و فروشنده محصولات، سفارش‌ها و گفتگوها را از پنل مدیریت می‌کند.
faq.q2 = آیا مشتری باید حساب کاربری بسازد؟
faq.a2 = خیر. خریداران به‌صورت مهمان خرید می‌کنند. سبد و سفارش آن‌ها به یک توکن نشست خصوصی وصل است و سفارش را با کد رهگیری ۱۰ رقمی پیگیری می‌کنند.
faq.q3 = آیا دستیار می‌تواند قیمت را تغییر دهد یا موجودی بسازد؟
faq.a3 = خیر. قیمت، موجودی و مبلغ سفارش همیشه توسط برنامه از پایگاه داده خوانده می‌شود. مدل زبانی فقط متن پاسخ را می‌نویسد.
faq.q4 = چه زبان‌هایی پشتیبانی می‌شود؟
faq.a4 = رابط کاربری به فارسی، انگلیسی، اسپانیایی، آلمانی و فرانسوی موجود است. زبان را از انتخاب‌گر بالای صفحه یا پایین صفحه عوض کنید.
faq.q5 = چطور شروع کنم؟
faq.a5 = حساب فروشنده بسازید، فروشگاه ایجاد کنید، چند محصول و پرسش متداول اضافه کنید و پیوند فروشگاه را به اشتراک بگذارید. فروشگاه دموی زنده همان چیزی را نشان می‌دهد که مشتری می‌بیند.
faq.q6 = اگر سرویس هوش مصنوعی در دسترس نباشد چه می‌شود؟
faq.a6 = دستیار با یک پیام عمومی و امن پاسخ می‌دهد و جزئیات سرویس‌دهنده را فاش نمی‌کند. ویترین، سبد خرید و پرداخت بدون آن هم کار می‌کنند.

# ---- landing: final call to action
landing.ctaTitle = آماده‌اید فروشگاهتان خودش حرف بزند؟
landing.ctaBody = فروشگاه بسازید، چند محصول اضافه کنید و پیوند آن را به اشتراک بگذارید. فقط چند دقیقه طول می‌کشد.

# ---- footer
footer.tagline = دستیار فروش هوشمند فروشگاه‌های آنلاین؛ از اولین پرسش تا تحویل سفارش.
footer.product = محصول
footer.sellers = برای فروشندگان
footer.customers = برای خریداران
footer.language = زبان
footer.types = انواع کسب‌وکار
footer.rights = © {year} ناوا. همه حقوق محفوظ است.
footer.top = بازگشت به بالا
footer.trust1.t = خرید امن
footer.trust1.d = ثبت سفارش بدون تکرار و آماده اتصال به درگاه پرداخت.
footer.trust2.t = پیگیری سفارش
footer.trust2.d = هر سفارش را با کد رهگیری ۱۰ رقمی پیدا کنید.
footer.trust3.t = فاکتور PDF
footer.trust3.d = برای هر سفارش فاکتور قابل دانلود صادر می‌شود.
footer.trust4.t = پاسخ مستند
footer.trust4.d = قیمت و موجودی مستقیم از پایگاه داده.

# ---- auth
auth.loginTitle = ورود
auth.registerTitle = ساخت حساب فروشنده
auth.email = ایمیل
auth.password = رمز عبور
auth.passwordHint = حداقل ۸ نویسه.
auth.phone = تلفن همراه
auth.phoneHint = برای دریافت کد تأیید پیامکی استفاده می‌شود.
auth.loginSubmit = ورود
auth.registerSubmit = ساخت حساب
auth.forgot = رمز عبور را فراموش کرده‌اید؟
auth.noAccount = حساب کاربری ندارید؟
auth.haveAccount = قبلاً ثبت‌نام کرده‌اید؟
auth.backToLogin = بازگشت به ورود
auth.verifyTitle = تأیید حساب
auth.verifyLead = یک کد ۸ رقمی به {email} فرستادیم.
auth.emailCode = کد تأیید ایمیل
auth.phoneCode = کد تأیید پیامک
auth.verifySubmit = تأیید و ادامه
auth.unverified = حساب شما هنوز تأیید نشده است. کدی را که فرستادیم وارد کنید.
auth.verified = حساب شما تأیید شد. اکنون می‌توانید وارد شوید.
auth.devHint = حالت توسعه: کد تأیید در لاگ سرور چاپ می‌شود.
auth.forgotTitle = بازیابی رمز عبور
auth.forgotLead = ایمیل خود را وارد کنید تا توکن بازیابی برایتان ارسال شود.
auth.forgotSubmit = ارسال توکن بازیابی
auth.forgotSent = اگر این ایمیل ثبت شده باشد، توکن بازیابی ارسال شده است.
auth.haveToken = توکن بازیابی دارم
auth.resetTitle = انتخاب رمز عبور جدید
auth.resetToken = توکن بازیابی
auth.newPassword = رمز عبور جدید
auth.resetSubmit = تغییر رمز عبور
auth.resetDone = رمز عبور شما تغییر کرد. با رمز جدید وارد شوید.

# ---- forms
form.required = این فیلد الزامی است.
form.price = یک قیمت معتبر وارد کنید.
form.stock = موجودی باید یک عدد صحیح و صفر یا بیشتر باشد.
form.otp = کد ۸ رقمی را وارد کنید.
form.tracking = کد رهگیری ۱۰ رقمی را وارد کنید.

# ---- storefront
shop.search = جست‌وجوی محصولات…
shop.inStockOnly = فقط موجودها
shop.count = {n} محصول
shop.empty = محصولی پیدا نشد.
shop.add = افزودن به سبد
shop.added = «{name}» به سبد خرید اضافه شد
shop.ask = پرسش از دستیار
shop.askProduct = درباره {name} توضیح بده
shop.attributes = مشخصات
shop.backToStore = بازگشت به فروشگاه
shop.qty = تعداد
shop.inStock = موجود ({n})
shop.lowStock = فقط {n} عدد مانده
shop.outOfStock = ناموجود
shop.productNotFound = محصول پیدا نشد.
shop.storeNotFound = فروشگاه پیدا نشد.
shop.poweredBy = ساخته‌شده با ناوا
shop.createYours = فروشگاه خودتان را بسازید

# ---- chat
chat.title = دستیار خرید
chat.open = پرسش از دستیار
chat.placeholder = پرسش خود را بنویسید…
chat.send = ارسال
chat.typing = دستیار در حال نوشتن است
chat.welcome = سلام! من دستیار {store} هستم. درباره محصولات، قیمت و موجودی بپرسید یا همین‌جا سفارش بدهید.
chat.s1 = کدام محصولات موجود است؟
chat.s2 = ارزان‌ترین کالا کدام است؟
chat.s3 = اولین محصول را به سبد من اضافه کن
chat.s4 = چطور سفارشم را پیگیری کنم؟

# ---- cart and checkout
cart.title = سبد خرید
cart.open = باز کردن سبد خرید ({n} کالا)
cart.empty = سبد خرید شما خالی است
cart.emptyHint = از فروشگاه محصول اضافه کنید یا از دستیار بخواهید اضافه کند.
cart.total = جمع کل
cart.checkout = ثبت سفارش
cart.clear = خالی کردن سبد
cart.dec = کم کردن تعداد {name}
cart.inc = زیاد کردن تعداد {name}
cart.remove = حذف {name}
checkout.title = تکمیل خرید
checkout.name = نام و نام خانوادگی
checkout.phone = شماره تماس
checkout.email = ایمیل
checkout.address = آدرس تحویل
checkout.submit = ثبت سفارش
checkout.back = بازگشت به سبد
order.placed = سفارش ثبت شد
order.number = شماره سفارش
order.tracking = کد رهگیری
order.items = اقلام سفارش
order.pay = پرداخت
order.paid = پرداخت انجام شد. سپاسگزاریم!
order.sandbox = این یک پرداخت آزمایشی است. برای شبیه‌سازی پرداخت موفق، تأیید کنید.
order.sandboxConfirm = تأیید پرداخت آزمایشی
order.invoice = دریافت فاکتور (PDF)
order.trackLink = پیگیری این سفارش
order.continue = ادامه خرید

# ---- order tracking and statuses
track.title = پیگیری سفارش
track.lead = کد رهگیری ۱۰ رقمی را که هنگام خرید دریافت کرده‌اید وارد کنید.
track.number = کد رهگیری
track.submit = پیگیری
track.store = فروشگاه
track.placedAt = زمان ثبت
track.updatedAt = آخرین به‌روزرسانی
track.cancelled = این سفارش لغو شده است.
status.pending = در انتظار
status.confirmed = تأیید شد
status.preparing = در حال آماده‌سازی
status.shipped = ارسال شد
status.delivered = تحویل شد
status.cancelled = لغو شد
cs.idle = در حال مرور
cs.awaiting_customer = دریافت اطلاعات
cs.awaiting_confirmation = منتظر تأیید
cs.completed = تکمیل شد

# ---- seller panel
s.overview = نمای کلی
s.orders = سفارش‌ها
s.conversations = گفتگوها
s.products = محصولات
s.knowledge = دانش
s.activeStore = فروشگاه فعال
s.viewStore = مشاهده فروشگاه
s.logout = خروج
s.needStore = ابتدا یک فروشگاه بسازید.
s.goOverview = رفتن به نمای کلی
s.noStoreTitle = هنوز فروشگاهی ندارید
s.noStoreBody = اولین فروشگاه خود را بسازید تا با دستیار شروع به فروش کنید.
s.storeName = نام فروشگاه
s.businessType = نوع کسب‌وکار
s.storeDesc = توضیحات
s.logo = لوگو
s.editStore = ویرایش فروشگاه
s.newStore = فروشگاه جدید
s.storeCreated = فروشگاه ساخته شد.
s.publicLink = پیوند عمومی
s.deleteStore = حذف فروشگاه
s.deleteStoreNote = حذف فروشگاه، محصولات، پرسش‌های متداول و مطالب دانشی آن را برای همیشه پاک می‌کند.
ov.orders = سفارش‌ها
ov.value = ارزش سفارش‌ها
ov.products = محصولات فعال
ov.conversations = گفتگوها
ov.attention = نیازمند توجه
ov.allGood = چیزی نیاز به توجه شما ندارد.
ov.pendingOrders = سفارش‌های در انتظار
ov.lowStock = موجودی کم
ov.lowStockItem = {n} عدد مانده
ov.recent = گفتگوهای اخیر
o.empty = هنوز سفارشی ثبت نشده است.
o.search = جست‌وجو با نام، تلفن یا کد رهگیری
o.all = همه
o.id = سفارش
o.customer = مشتری
o.total = جمع کل
o.status = وضعیت
o.date = تاریخ
od.title = سفارش {id}
od.next = گام بعدی
od.final = این سفارش به وضعیت نهایی رسیده است.
od.moveTo = انتقال به «{status}»
od.cancelOrder = لغو سفارش
od.updated = سفارش به‌روزرسانی شد.
od.phone = تلفن
od.address = آدرس
od.invoice = شماره فاکتور
od.date = تاریخ
od.item = کالا
od.unit = قیمت واحد
od.qty = تعداد
od.line = جمع ردیف
c.empty = هنوز گفتگویی ثبت نشده است.
c.guest = مهمان {id}
c.noMessages = بدون پیام
c.messages = {n} پیام
c.order = سفارش {id}
c.user = مشتری
c.assistant = دستیار
p.add = افزودن محصول
p.edit = ویرایش محصول
p.created = محصول ساخته شد.
p.updated = محصول به‌روزرسانی شد.
p.deleted = محصول حذف شد.
p.empty = هنوز محصولی ندارید.
p.emptyHint = اولین محصول را اضافه کنید تا دستیار بتواند آن را بفروشد.
p.name = نام
p.price = قیمت
p.stock = موجودی
p.desc = توضیحات
p.image = تصویر
p.status = وضعیت
p.reserved = {n} رزرو شده
p.typeFields = مشخصات {type}
k.lead = دستیار از روی همین موارد پاسخ می‌دهد. آن‌ها را دقیق و کوتاه بنویسید.
k.tabKnowledge = پایگاه دانش
k.tabFaqs = سوالات متداول
k.add = افزودن مورد
k.editEntry = ویرایش مورد
k.title = عنوان
k.content = متن
k.question = پرسش
k.answer = پاسخ
k.active = فعال (مورد استفاده دستیار)
k.emptyKnowledge = هنوز مطلب دانشی ثبت نشده است.
k.emptyFaqs = هنوز پرسش متداولی ثبت نشده است.
`)
