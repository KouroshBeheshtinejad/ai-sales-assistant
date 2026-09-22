import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { safeStorage } from './util'

// Every string is written once as [persian, english].
const D = {
  brand: ['ناوا', 'NAVA'],
  currency: ['تومان', 'Toman'],
  loading: ['در حال بارگذاری…', 'Loading…'],
  retry: ['تلاش دوباره', 'Try again'],
  save: ['ذخیره تغییرات', 'Save changes'],
  create: ['ایجاد', 'Create'],
  cancel: ['انصراف', 'Cancel'],
  close: ['بستن', 'Close'],
  edit: ['ویرایش', 'Edit'],
  delete: ['حذف', 'Delete'],
  copy: ['کپی', 'Copy'],
  copied: ['کپی شد', 'Copied'],
  back: ['بازگشت', 'Back'],
  search: ['جستجو', 'Search'],
  active: ['فعال', 'Active'],
  inactive: ['غیرفعال', 'Inactive'],
  optional: ['اختیاری', 'Optional'],
  saved: ['ذخیره شد.', 'Saved.'],
  deleted: ['حذف شد.', 'Deleted.'],
  show: ['نمایش', 'Show'],
  hide: ['پنهان', 'Hide'],
  select: ['انتخاب کنید…', 'Select…'],
  yes: ['بله', 'Yes'],
  no: ['خیر', 'No'],
  'confirm.sure': ['مطمئنید؟', 'Sure?'],
  'a11y.skip': ['پرش به محتوای اصلی', 'Skip to main content'],
  'notfound.title': ['این صفحه پیدا نشد', "This page doesn't exist"],
  'notfound.home': ['بازگشت به صفحه اصلی', 'Back to the home page'],
  'crash.title': ['مشکلی در نمایش صفحه پیش آمد', 'Something broke while showing this page'],

  'nav.demo': ['فروشگاه نمونه', 'Demo store'],
  'nav.track': ['رهگیری سفارش', 'Track order'],
  'nav.login': ['ورود', 'Sign in'],
  'nav.register': ['ثبت‌نام', 'Create account'],
  'nav.panel': ['پنل فروشنده', 'Seller panel'],
  'nav.lang': ['EN', 'فا'],
  'nav.langName': ['English', 'فارسی'],

  'landing.title': ['گفتگو را به فروش تبدیل کنید', 'Turn conversations into sales'],
  'landing.lead': [
    'ناوا دستیار فروشی است که فقط از اطلاعات همان فروشگاه جواب می‌دهد. مشتری در همان گفتگو محصول را پیدا می‌کند، به سبد اضافه می‌کند و سفارش ثبت می‌کند.',
    'NAVA is a store assistant that answers only from your own catalog, FAQs and policies. Shoppers find a product, fill a cart and place an order without leaving the chat.',
  ],
  'landing.cta': ['مشاهده فروشگاه نمونه', 'Open the demo store'],
  'landing.ctaSeller': ['ساخت فروشگاه', 'Start selling'],
  'landing.q1': ['کتونی مشکی سایز ۴۲ دارید؟', 'Do you have the black sneakers in size 42?'],
  'landing.a1': ['بله، «کتونی مشکی» سایز ۴۲ موجود است: ۲٬۴۵۰٬۰۰۰ تومان، ۵ عدد در انبار.', 'Yes, "Black sneakers" in size 42 are in stock: 2,450,000 Toman, 5 left.'],
  'landing.q2': ['دو تا می‌خوام', "I'll take two"],
  'landing.a2': ['۲ عدد «کتونی مشکی» به سبد خرید اضافه شد. مبلغ کل: ۴٬۹۰۰٬۰۰۰ تومان', 'Added 2 × "Black sneakers" to your cart. Total: 4,900,000 Toman'],
  'landing.how': ['مسیر یک سفارش', 'How an order happens'],
  'landing.h1': ['مشتری می‌پرسد', 'The shopper asks'],
  'landing.d1': ['درباره قیمت، موجودی، ارسال یا مرجوعی؛ به زبان خودش.', 'About price, stock, shipping or returns, in their own words.'],
  'landing.h2': ['دستیار از داده فروشگاه جواب می‌دهد', 'The assistant answers from store data'],
  'landing.d2': ['محصول، سؤال‌های متداول و دانش شما. قیمت و موجودی همیشه از پایگاه داده می‌آید، نه از حدس مدل.', "Products, FAQs and your knowledge base. Price and stock always come from the database, never from the model's guess."],
  'landing.h3': ['سبد و ثبت سفارش', 'Cart and checkout'],
  'landing.d3': ['با دکمه یا با گفتگو. مبلغ و موجودی سمت سرور بررسی می‌شود.', 'By button or by chat. Totals and stock are validated on the server.'],
  'landing.h4': ['فروشنده سفارش را تحویل می‌گیرد', 'The seller takes over'],
  'landing.d4': ['سفارش‌ها و گفتگوها در پنل فروشنده دیده می‌شوند و وضعیت هر سفارش تا تحویل پیگیری می‌شود.', 'Orders and conversations show up in the seller panel, and each order is followed through to delivery.'],
  'landing.sellers': ['برای فروشنده', 'For sellers'],
  'landing.sellersBody': ['محصول، سؤال‌های متداول و دانش فروشگاه را وارد کنید تا دستیار دقیقاً همان‌ها را بداند. فیلدهای محصول با نوع کسب‌وکار شما تنظیم می‌شود.', 'Add products, FAQs and store knowledge and the assistant knows exactly that. Product fields adapt to your type of business.'],
  'landing.buyers': ['برای مشتری', 'For shoppers'],
  'landing.buyersBody': ['بدون ساخت حساب خرید کنید و سفارش را با شماره رهگیری ۱۰ رقمی دنبال کنید.', 'Shop without an account and follow your order with a 10-digit tracking number.'],
  'landing.footer': ['ناوا، تجارت مکالمه‌ای برای فروشگاه‌های آنلاین', 'NAVA, conversational commerce for online stores'],

  'auth.loginTitle': ['ورود به پنل فروشنده', 'Sign in to your seller panel'],
  'auth.registerTitle': ['ساخت حساب فروشنده', 'Create a seller account'],
  'auth.email': ['ایمیل', 'Email'],
  'auth.phone': ['شماره موبایل', 'Mobile number'],
  'auth.phoneHint': ['اختیاری. اگر وارد کنید، یک کد جداگانه هم برای موبایل لازم است.', 'Optional. If you add one, a separate code is needed for it.'],
  'auth.password': ['رمز عبور', 'Password'],
  'auth.passwordHint': ['دست‌کم ۸ نویسه', 'At least 8 characters'],
  'auth.loginSubmit': ['ورود', 'Sign in'],
  'auth.registerSubmit': ['ثبت‌نام', 'Create account'],
  'auth.forgot': ['رمز عبور را فراموش کرده‌اید؟', 'Forgot your password?'],
  'auth.noAccount': ['حساب ندارید؟', 'No account yet?'],
  'auth.haveAccount': ['حساب دارید؟', 'Already have an account?'],
  'auth.verifyTitle': ['تأیید حساب', 'Verify your account'],
  'auth.verifyLead': ['کد ۸ رقمی ارسال‌شده به {email} را وارد کنید. کد ۱۰ دقیقه اعتبار دارد.', 'Enter the 8-digit code sent to {email}. It is valid for 10 minutes.'],
  'auth.emailCode': ['کد ایمیل', 'Email code'],
  'auth.phoneCode': ['کد پیامک موبایل', 'Mobile code'],
  'auth.verifySubmit': ['تأیید و ادامه', 'Verify and continue'],
  'auth.devHint': ['حالت توسعه: اگر OTP_PROVIDER=log باشد، کد در لاگ سرور چاپ می‌شود.', 'Dev mode: with OTP_PROVIDER=log the code is printed in the server log.'],
  'auth.unverified': ['حساب شما هنوز تأیید نشده است. کد تأیید را وارد کنید.', "Your account isn't verified yet. Enter your verification code."],
  'auth.verified': ['حساب تأیید شد. اکنون وارد شوید.', 'Account verified. You can sign in now.'],
  'auth.forgotTitle': ['بازیابی رمز عبور', 'Reset your password'],
  'auth.forgotLead': ['ایمیل حساب را وارد کنید تا راهنمای بازیابی ارسال شود.', "Enter your account email and we'll send reset instructions."],
  'auth.forgotSubmit': ['ارسال راهنما', 'Send instructions'],
  'auth.forgotSent': ['اگر حسابی با این ایمیل وجود داشته باشد، راهنمای بازیابی ارسال می‌شود.', 'If an account exists for this email, reset instructions are on their way.'],
  'auth.haveToken': ['کد بازیابی دارم', 'I have a reset code'],
  'auth.resetTitle': ['رمز عبور جدید', 'Choose a new password'],
  'auth.resetToken': ['کد بازیابی', 'Reset code'],
  'auth.newPassword': ['رمز عبور جدید', 'New password'],
  'auth.resetSubmit': ['تغییر رمز عبور', 'Change password'],
  'auth.resetDone': ['رمز عبور تغییر کرد. با رمز جدید وارد شوید.', 'Password changed. Sign in with your new password.'],
  'auth.backToLogin': ['بازگشت به ورود', 'Back to sign in'],

  'shop.search': ['جستجوی محصول', 'Search products'],
  'shop.inStockOnly': ['فقط کالاهای موجود', 'In stock only'],
  'shop.count': ['{n} محصول', '{n} products'],
  'shop.empty': ['محصولی برای نمایش پیدا نشد.', 'No products to show.'],
  'shop.add': ['افزودن به سبد', 'Add to cart'],
  'shop.added': ['«{name}» به سبد اضافه شد.', '"{name}" added to your cart.'],
  'shop.details': ['جزئیات', 'Details'],
  'shop.ask': ['از دستیار بپرسید', 'Ask the assistant'],
  'shop.askProduct': ['قیمت و موجودی «{name}» چقدر است؟', 'What is the price and stock of "{name}"?'],
  'shop.inStock': ['{n} عدد موجود', '{n} in stock'],
  'shop.lowStock': ['فقط {n} عدد مانده', 'Only {n} left'],
  'shop.outOfStock': ['ناموجود', 'Out of stock'],
  'shop.storeNotFound': ['این فروشگاه پیدا نشد.', "This store doesn't exist."],
  'shop.productNotFound': ['این محصول در دسترس نیست.', "This product isn't available."],
  'shop.backToStore': ['بازگشت به فروشگاه', 'Back to the store'],
  'shop.attributes': ['مشخصات', 'Specifications'],
  'shop.qty': ['تعداد', 'Quantity'],

  'cart.title': ['سبد خرید', 'Your cart'],
  'cart.open': ['سبد خرید ({n})', 'Cart ({n})'],
  'cart.empty': ['سبد خرید خالی است.', 'Your cart is empty.'],
  'cart.emptyHint': ['از فروشگاه محصول اضافه کنید یا از دستیار بخواهید.', 'Add something from the shop or ask the assistant.'],
  'cart.total': ['مبلغ کل', 'Total'],
  'cart.remove': ['حذف {name}', 'Remove {name}'],
  'cart.inc': ['افزایش تعداد {name}', 'Increase quantity of {name}'],
  'cart.dec': ['کاهش تعداد {name}', 'Decrease quantity of {name}'],
  'cart.checkout': ['ادامه و ثبت سفارش', 'Continue to checkout'],
  'cart.clear': ['خالی کردن سبد', 'Clear cart'],
  'checkout.title': ['اطلاعات تحویل', 'Delivery details'],
  'checkout.name': ['نام و نام خانوادگی', 'Full name'],
  'checkout.phone': ['شماره تماس', 'Phone number'],
  'checkout.email': ['ایمیل', 'Email'],
  'checkout.address': ['آدرس کامل', 'Full address'],
  'checkout.submit': ['ثبت سفارش', 'Place order'],
  'checkout.back': ['بازگشت به سبد', 'Back to cart'],
  'order.placed': ['سفارش شما ثبت شد', 'Your order is placed'],
  'order.number': ['شماره سفارش', 'Order number'],
  'order.tracking': ['شماره رهگیری', 'Tracking number'],
  'order.pay': ['پرداخت آنلاین', 'Pay online'],
  'order.sandbox': ['درگاه آزمایشی فعال است. برای شبیه‌سازی پرداخت، تأیید کنید.', 'The sandbox gateway is active. Confirm to simulate a payment.'],
  'order.sandboxConfirm': ['تأیید پرداخت آزمایشی', 'Confirm test payment'],
  'order.paid': ['پرداخت با موفقیت انجام شد.', 'Payment received.'],
  'order.invoice': ['دانلود فاکتور', 'Download invoice'],
  'order.trackLink': ['پیگیری سفارش', 'Track this order'],
  'order.continue': ['ادامه خرید', 'Keep shopping'],
  'order.items': ['اقلام سفارش', 'Items'],

  'chat.title': ['دستیار فروشگاه', 'Store assistant'],
  'chat.welcome': ['سلام! درباره محصولات، قیمت، موجودی یا قوانین «{store}» بپرسید.', 'Hi! Ask me about products, prices, stock or the policies of "{store}".'],
  'chat.placeholder': ['پیام خود را بنویسید…', 'Type your message…'],
  'chat.send': ['ارسال', 'Send'],
  'chat.open': ['گفتگو با دستیار', 'Chat with the assistant'],
  'chat.typing': ['دستیار در حال نوشتن است', 'The assistant is typing'],
  'chat.s1': ['چه محصولاتی دارید؟', 'What products do you have?'],
  'chat.s2': ['قوانین ارسال و مرجوعی چیست؟', 'What are your shipping and return policies?'],
  'chat.s3': ['سبد خرید من', 'Show my cart'],
  'chat.s4': ['ثبت سفارش', 'Checkout'],

  'track.title': ['رهگیری سفارش', 'Track your order'],
  'track.lead': ['شماره رهگیری ۱۰ رقمی سفارش را وارد کنید.', 'Enter the 10-digit tracking number of your order.'],
  'track.number': ['شماره رهگیری', 'Tracking number'],
  'track.submit': ['پیگیری', 'Track'],
  'track.store': ['فروشگاه', 'Store'],
  'track.placedAt': ['زمان ثبت', 'Placed on'],
  'track.updatedAt': ['آخرین به‌روزرسانی', 'Last update'],
  'track.cancelled': ['این سفارش لغو شده است.', 'This order was cancelled.'],

  'status.pending': ['در انتظار تأیید', 'Pending'],
  'status.confirmed': ['تأیید شده', 'Confirmed'],
  'status.preparing': ['در حال آماده‌سازی', 'Preparing'],
  'status.shipped': ['ارسال شده', 'Shipped'],
  'status.delivered': ['تحویل شده', 'Delivered'],
  'status.cancelled': ['لغو شده', 'Cancelled'],
  'cs.idle': ['در حال مرور', 'Browsing'],
  'cs.awaiting_customer': ['منتظر اطلاعات مشتری', 'Waiting for customer details'],
  'cs.awaiting_confirmation': ['منتظر تأیید نهایی', 'Waiting for confirmation'],
  'cs.completed': ['سفارش ثبت شد', 'Order placed'],

  's.overview': ['نمای کلی', 'Overview'],
  's.orders': ['سفارش‌ها', 'Orders'],
  's.conversations': ['گفتگوها', 'Conversations'],
  's.products': ['محصولات', 'Products'],
  's.knowledge': ['دانش فروشگاه', 'Store knowledge'],
  's.activeStore': ['فروشگاه فعال', 'Active store'],
  's.viewStore': ['مشاهده فروشگاه', 'View storefront'],
  's.logout': ['خروج', 'Sign out'],
  's.noStoreTitle': ['هنوز فروشگاهی ندارید', "You don't have a store yet"],
  's.noStoreBody': ['برای شروع، اولین فروشگاه خود را بسازید.', 'Create your first store to get started.'],
  's.needStore': ['ابتدا یک فروشگاه بسازید.', 'Create a store first.'],
  's.goOverview': ['ساخت فروشگاه', 'Create a store'],
  's.newStore': ['فروشگاه جدید', 'New store'],
  's.editStore': ['ویرایش فروشگاه', 'Edit store'],
  's.storeName': ['نام فروشگاه', 'Store name'],
  's.storeDesc': ['توضیحات', 'Description'],
  's.logo': ['لوگوی فروشگاه', 'Store logo'],
  's.businessType': ['نوع کسب‌وکار', 'Business type'],
  's.deleteStore': ['حذف فروشگاه', 'Delete store'],
  's.deleteStoreNote': ['حذف فروشگاه، محصولات و دانش آن را هم پاک می‌کند. فروشگاهی که سفارش دارد قابل حذف نیست.', 'Deleting a store also removes its products and knowledge. A store that has orders cannot be deleted.'],
  's.publicLink': ['نشانی فروشگاه شما', 'Your storefront link'],
  's.storeCreated': ['فروشگاه ساخته شد.', 'Store created.'],

  'ov.orders': ['سفارش‌ها', 'Orders'],
  'ov.value': ['ارزش سفارش‌ها (بدون لغوشده)', 'Order value (excl. cancelled)'],
  'ov.products': ['محصولات فعال', 'Active products'],
  'ov.conversations': ['گفتگوها', 'Conversations'],
  'ov.attention': ['نیاز به اقدام', 'Needs attention'],
  'ov.pendingOrders': ['سفارش‌های در انتظار تأیید', 'Orders waiting for confirmation'],
  'ov.lowStock': ['موجودی کم', 'Low stock'],
  'ov.lowStockItem': ['{n} عدد مانده', '{n} left'],
  'ov.allGood': ['فعلاً موردی نیاز به اقدام ندارد.', 'Nothing needs your attention right now.'],
  'ov.recent': ['آخرین گفتگوها', 'Latest conversations'],

  'o.search': ['جستجو با نام، تلفن یا شماره رهگیری', 'Search by name, phone or tracking number'],
  'o.all': ['همه', 'All'],
  'o.id': ['سفارش', 'Order'],
  'o.customer': ['مشتری', 'Customer'],
  'o.total': ['مبلغ', 'Total'],
  'o.status': ['وضعیت', 'Status'],
  'o.date': ['تاریخ', 'Date'],
  'o.empty': ['هنوز سفارشی ثبت نشده است.', 'No orders yet.'],
  'od.title': ['سفارش {id}', 'Order {id}'],
  'od.phone': ['تلفن', 'Phone'],
  'od.address': ['آدرس', 'Address'],
  'od.invoice': ['شماره فاکتور', 'Invoice number'],
  'od.unit': ['قیمت واحد', 'Unit price'],
  'od.qty': ['تعداد', 'Qty'],
  'od.line': ['جمع', 'Subtotal'],
  'od.item': ['کالا', 'Item'],
  'od.next': ['تغییر وضعیت', 'Update status'],
  'od.final': ['این سفارش در وضعیت نهایی است و دیگر تغییر نمی‌کند.', 'This order is in a final state and cannot change.'],
  'od.moveTo': ['تغییر به «{status}»', 'Mark as {status}'],
  'od.cancelOrder': ['لغو سفارش', 'Cancel order'],
  'od.updated': ['وضعیت سفارش به‌روز شد.', 'Order status updated.'],
  'od.date': ['ثبت‌شده در', 'Placed on'],

  'c.empty': ['هنوز گفتگویی انجام نشده است.', 'No conversations yet.'],
  'c.guest': ['مشتری مهمان {id}', 'Guest shopper {id}'],
  'c.messages': ['{n} پیام', '{n} messages'],
  'c.order': ['سفارش {id}', 'Order {id}'],
  'c.user': ['مشتری', 'Customer'],
  'c.assistant': ['دستیار', 'Assistant'],
  'c.tool': ['ابزار', 'Tool'],
  'c.noMessages': ['بدون پیام', 'No messages'],

  'p.add': ['محصول جدید', 'New product'],
  'p.edit': ['ویرایش محصول', 'Edit product'],
  'p.name': ['نام', 'Name'],
  'p.price': ['قیمت (تومان)', 'Price (Toman)'],
  'p.stock': ['موجودی', 'Stock'],
  'p.desc': ['توضیحات', 'Description'],
  'p.image': ['تصویر محصول', 'Product image'],
  'p.status': ['وضعیت', 'Status'],
  'p.reserved': ['{n} رزرو', '{n} reserved'],
  'p.empty': ['هنوز محصولی اضافه نکرده‌اید.', "You haven't added any products yet."],
  'p.emptyHint': ['دستیار فقط از محصولاتی که اینجا اضافه می‌کنید جواب می‌دهد.', 'The assistant only answers from the products you add here.'],
  'p.created': ['محصول ایجاد شد.', 'Product created.'],
  'p.updated': ['محصول به‌روز شد.', 'Product updated.'],
  'p.deleted': ['محصول حذف شد.', 'Product deleted.'],
  'p.typeFields': ['ویژگی‌های ویژه «{type}»', '{type} details'],

  'k.lead': ['دستیار برای جواب دادن به مشتری از این مطالب استفاده می‌کند.', 'The assistant uses these entries to answer customers.'],
  'k.tabKnowledge': ['دانش', 'Knowledge'],
  'k.tabFaqs': ['سؤال‌های متداول', 'FAQs'],
  'k.add': ['افزودن', 'Add'],
  'k.editEntry': ['ویرایش', 'Edit entry'],
  'k.title': ['عنوان', 'Title'],
  'k.content': ['متن', 'Content'],
  'k.question': ['سؤال', 'Question'],
  'k.answer': ['پاسخ', 'Answer'],
  'k.active': ['در پاسخ‌ها استفاده شود', 'Use in answers'],
  'k.emptyKnowledge': ['هنوز مطلبی اضافه نشده است. مثلاً قوانین ارسال یا ساعت کاری فروشگاه.', 'No entries yet. Try shipping rules or opening hours.'],
  'k.emptyFaqs': ['هنوز سؤالی اضافه نشده است.', 'No FAQs yet.'],

  'form.required': ['این فیلد الزامی است.', 'This field is required.'],
  'form.price': ['قیمت باید عددی صفر یا بیشتر باشد.', 'Price must be a number, zero or more.'],
  'form.stock': ['موجودی باید عدد صحیح صفر یا بیشتر باشد.', 'Stock must be a whole number, zero or more.'],
  'form.otp': ['کد باید ۸ رقم باشد.', 'The code must be 8 digits.'],
  'form.tracking': ['شماره رهگیری ۱۰ رقم است.', 'A tracking number has 10 digits.'],

  'err.network': ['اتصال به سرور برقرار نشد. اینترنت خود را بررسی کنید.', "Couldn't reach the server. Check your connection."],
  'err.generic': ['مشکلی پیش آمد. دوباره تلاش کنید.', 'Something went wrong. Please try again.'],
  'err.rate': ['تعداد درخواست‌ها زیاد است. کمی صبر کنید و دوباره تلاش کنید.', 'Too many requests. Wait a moment and try again.'],
  'err.session': ['نشست شما منقضی شده است. دوباره وارد شوید.', 'Your session has expired. Please sign in again.'],
  'err.guest': ['نشست خرید معتبر نیست. دوباره تلاش کنید.', 'Your shopping session is no longer valid. Please try again.'],
  'err.stock': ['موجودی کافی نیست.', 'Not enough stock.'],
  'err.inactive': ['این محصول در حال حاضر در دسترس نیست.', 'This product is currently unavailable.'],
  'err.emptyCart': ['سبد خرید خالی است.', 'Your cart is empty.'],
  'err.quantity': ['تعداد باید بین ۱ تا ۱۰۰ باشد.', 'Quantity must be between 1 and 100.'],
  'err.credentials': ['ایمیل یا رمز عبور درست نیست.', 'Incorrect email or password.'],
  'err.unverified': ['حساب شما هنوز تأیید نشده است.', "Your account isn't verified yet."],
  'err.emailTaken': ['با این ایمیل قبلاً ثبت‌نام شده است.', 'An account with this email already exists.'],
  'err.otp': ['کد نادرست است یا منقضی شده.', 'The code is wrong or has expired.'],
  'err.resetToken': ['کد بازیابی نادرست است یا منقضی شده.', 'The reset code is wrong or has expired.'],
  'err.notFound': ['مورد پیدا نشد.', 'Not found.'],
  'err.transition': ['این تغییر وضعیت مجاز نیست.', "That status change isn't allowed."],
  'err.payment': ['درگاه پرداخت هنوز پیکربندی نشده است.', "The payment gateway isn't configured yet."],
  'err.paid': ['این سفارش قبلاً پرداخت شده است.', 'This order is already paid.'],
  'err.assistant': ['دستیار موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید یا مستقیم با فروشنده تماس بگیرید.', 'The assistant is temporarily unavailable. Try again later or contact the seller directly.'],
}

const ERROR_PATTERNS = [
  [/insufficient stock/i, 'err.stock'],
  [/not active|is inactive|not available in this store/i, 'err.inactive'],
  [/cart is empty/i, 'err.emptyCart'],
  [/^quantity/i, 'err.quantity'],
  [/invalid email or password/i, 'err.credentials'],
  [/verification is required/i, 'err.unverified'],
  [/email already registered/i, 'err.emailTaken'],
  [/invalid or expired verification/i, 'err.otp'],
  [/invalid or expired reset/i, 'err.resetToken'],
  [/guest token|idempotency key/i, 'err.guest'],
  [/session expired|invalid token|not authenticated|user not found/i, 'err.session'],
  [/cannot change status|invalid status/i, 'err.transition'],
  [/payment provider is not configured/i, 'err.payment'],
  [/already paid/i, 'err.paid'],
  [/assistant (is|could)/i, 'err.assistant'],
  [/not found/i, 'err.notFound'],
]

const BUSINESS_FA = {
  clothing: 'پوشاک و مد', fast_food: 'فست‌فود', restaurant: 'رستوران', bakery: 'نانوایی و شیرینی', cafe: 'کافه',
  pharmacy: 'داروخانه', electronics: 'لوازم الکترونیکی', furniture: 'مبلمان', grocery: 'خواربار و سوپرمارکت',
  cosmetics: 'لوازم آرایشی', jewelry: 'جواهر و طلا', beauty_salon: 'سالن زیبایی', home_decor: 'دکوراسیون منزل',
  stationery: 'لوازم‌التحریر', pet_store: 'پت‌شاپ', sports: 'ورزش و طبیعت‌گردی', fitness: 'باشگاه و تناسب اندام',
  automotive: 'خودرو', books_music: 'کتاب و موسیقی', toys: 'اسباب‌بازی', hardware: 'ابزار و یراق',
  flowers: 'گل و هدیه', real_estate: 'املاک', travel: 'گردشگری و سفر', medical_clinic: 'کلینیک پزشکی',
  dental: 'دندانپزشکی', yoga: 'یوگا و سلامت', educational: 'خدمات آموزشی', digital_products: 'محصولات دیجیتال',
  software: 'نرم‌افزار و SaaS', agency: 'آژانس بازاریابی', construction: 'ساختمان‌سازی', landscaping: 'محوطه‌سازی',
  cleaning: 'خدمات نظافت', laundry: 'خشکشویی', printing: 'چاپ و طراحی', event_planning: 'برگزاری رویداد',
  wedding: 'خدمات عروسی', artist_shop: 'فروشگاه هنری', handmade: 'صنایع دستی', agricultural: 'محصولات کشاورزی',
  veterinary: 'دامپزشکی', aquarium: 'آکواریوم و ماهی', garden: 'مرکز باغبانی', grocery_delivery: 'تحویل مواد غذایی',
  productivity: 'ابزار بهره‌وری', car_rental: 'اجاره خودرو', boat: 'قایق و دریانوردی', camping: 'کمپینگ و طبیعت',
}

const FIELD_FA = {
  size: 'سایز', color: 'رنگ', material: 'جنس', gender: 'جنسیت', ingredients: 'مواد تشکیل‌دهنده', spice_level: 'میزان تندی',
  calories: 'کالری', contains_nuts: 'حاوی آجیل', cuisine: 'نوع آشپزی', serving_size: 'اندازه سرو', dietary: 'رژیم غذایی',
  prep_time: 'زمان آماده‌سازی (دقیقه)', flavor: 'طعم', weight: 'وزن', contains_egg: 'حاوی تخم‌مرغ', freshness: 'تازگی',
  coffee_origin: 'خاستگاه قهوه', roast_level: 'درجه رست', milk_type: 'نوع شیر', temperature: 'دما', dosage: 'دوز',
  usage: 'نحوه مصرف', prescription_required: 'نیاز به نسخه', expiry_date: 'تاریخ انقضا', brand: 'برند', model: 'مدل',
  warranty: 'گارانتی (ماه)', power: 'مشخصات برق', dimensions: 'ابعاد', assembly_required: 'نیاز به مونتاژ', origin: 'مبدأ',
  packaging: 'بسته‌بندی', shelf_life: 'ماندگاری', organic: 'ارگانیک', skin_type: 'نوع پوست', fragrance: 'رایحه',
  volume: 'حجم', cruelty_free: 'بدون آزمایش روی حیوانات', metal: 'فلز', stone: 'سنگ', certified: 'دارای گواهی',
}

const OPTION_FA = {
  Unisex: 'یونیسکس', Men: 'مردانه', Women: 'زنانه', Kids: 'بچگانه', Low: 'کم', Medium: 'متوسط', High: 'زیاد',
  Light: 'روشن', Dark: 'تیره', Hot: 'گرم', Ice: 'سرد', Warm: 'ولرم', Regular: 'معمولی', Oat: 'جو دوسر', Almond: 'بادام',
  Soy: 'سویا', Dry: 'خشک', Oily: 'چرب', Sensitive: 'حساس', Normal: 'معمولی', 'Same Day': 'همان روز', '48h': '۴۸ ساعت', '72h': '۷۲ ساعت',
}

const I18nContext = createContext(null)
const STORAGE_KEY = 'nava_locale'

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(() => (safeStorage.get(STORAGE_KEY) === 'en' ? 'en' : 'fa'))
  const fa = locale === 'fa'

  useEffect(() => {
    document.documentElement.lang = locale
    document.documentElement.dir = fa ? 'rtl' : 'ltr'
  }, [locale, fa])

  const setLocale = useCallback((next) => { safeStorage.set(STORAGE_KEY, next); setLocaleState(next) }, [])

  const value = useMemo(() => {
    const tag = fa ? 'fa-IR' : 'en-US'
    const numberFormat = new Intl.NumberFormat(tag, { maximumFractionDigits: 2 })
    const dateFormat = new Intl.DateTimeFormat(tag, { dateStyle: 'medium', timeStyle: 'short' })
    const idFormat = new Intl.NumberFormat(tag, { useGrouping: false })

    const t = (key, vars) => {
      const entry = D[key]
      let text = entry ? entry[fa ? 0 : 1] : key
      if (vars) for (const [name, v] of Object.entries(vars)) text = text.replaceAll(`{${name}}`, typeof v === 'number' ? numberFormat.format(v) : v)
      return text
    }
    const num = (n) => numberFormat.format(Number(n) || 0)
    const id = (n) => idFormat.format(Number(n) || 0) // ids and tracking numbers: no digit grouping
    const money = (n) => `${num(n)} ${t('currency')}`
    const date = (d) => (d && !Number.isNaN(d.getTime()) ? dateFormat.format(d) : '')
    const bizLabel = (slug, fallback) => (fa ? BUSINESS_FA[slug] : null) || fallback || slug
    const fieldLabel = (field) => (fa ? FIELD_FA[field.name] : null) || field.label || field.name.replace(/_/g, ' ')
    const optionLabel = (option) => (fa ? OPTION_FA[option] : null) || option
    const err = (error) => {
      if (!error) return ''
      if (error.status === 0) return t('err.network')
      if (error.status === 429) return t('err.rate')
      const hit = ERROR_PATTERNS.find(([pattern]) => pattern.test(error.message))
      if (hit) return t(hit[1])
      // Messages written in Persian by the backend (chat flow) are shown as-is.
      return /[\u0600-\u06FF]/.test(error.message) ? error.message : t('err.generic')
    }
    return { locale, setLocale, fa, dir: fa ? 'rtl' : 'ltr', t, num, id, money, date, bizLabel, fieldLabel, optionLabel, err }
  }, [locale, fa, setLocale])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export const useI18n = () => useContext(I18nContext)
