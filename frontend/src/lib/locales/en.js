import { parseCatalog } from './parse'

export default parseCatalog(`
# ---- core
brand = NAVA
loading = Loading…
retry = Try again
close = Close
copy = Copy
copied = Copied
cancel = Cancel
create = Create
save = Save
saved = Saved
edit = Edit
delete = Delete
deleted = Deleted
yes = Yes
no = No
show = Show
hide = Hide
select = Select…
active = Active
inactive = Inactive
optional = optional
a11y.skip = Skip to content
confirm.sure = Are you sure?
crash.title = Something went wrong
notfound.title = Page not found
notfound.home = Back to home

# ---- errors
err.generic = Something went wrong. Please try again.
err.network = Network error. Check your connection and try again.
err.rate = Too many requests. Please wait a moment and try again.
err.auth = Please sign in again.
err.notFound = We could not find what you were looking for.
err.server = The server ran into a problem. Please try again later.
err.m.invalidCredentials = Invalid email or password.
err.m.emailTaken = This email is already registered.
err.m.invalidCode = The code is invalid or has expired.
err.m.invalidReset = The reset token is invalid or has expired.
err.m.needVerify = Please verify your account first.
err.m.sessionExpired = Your session has expired. Please sign in again.
err.m.stock = There is not enough stock for this product.
err.m.cartEmpty = Your cart is empty.
err.m.inactive = This product is not available.
err.m.qty = Quantity must be between 1 and 100.
err.m.image = The image is not supported or is too large.
err.m.paid = This order is already paid.
err.m.notPending = Only pending orders can be paid.
err.m.guest = Your shopping session expired. Please try again.

# ---- navigation and header
nav.main = Main navigation
nav.features = Features
nav.how = How it works
nav.stores = Stores
nav.demo = Live demo
nav.faq = FAQ
nav.track = Track order
nav.login = Sign in
nav.register = Get started
nav.panel = Seller panel
nav.langName = Language
nav.menu = Menu
nav.openMenu = Open menu
nav.closeMenu = Close menu
nav.home = NAVA home

# ---- landing: hero
landing.badge = AI conversational commerce
landing.title = Turn store visitors into customers, one conversation at a time
landing.lead = NAVA is an AI sales assistant for online stores. It answers from your own catalog and policies, fills the cart, takes the order and issues a tracked invoice, in five languages, around the clock.
landing.cta = Try the live demo store
landing.ctaSeller = Open your store
landing.b1 = Prices and stock always come from your database
landing.b2 = Guest checkout, no account needed
landing.b3 = Five languages out of the box
landing.q1 = Do you have the black hoodie in size L?
landing.a1 = Yes, the black hoodie in L is in stock (3 left) for 890,000 Toman. Shall I add it to your cart?
landing.q2 = Yes, please add it.
landing.a2 = Done. Your cart has 1 item, 890,000 Toman in total. Send me your name, phone and address to place the order.
landing.chipStock = In stock
landing.chipOrder = Order confirmed
landing.chipTracking = Tracking number issued

# ---- landing: stats
landing.stat.stores = Live stores
landing.stat.products = Products on sale
landing.stat.types = Business templates
landing.stat.languages = Languages

# ---- landing: how it works
landing.how = How it works
landing.howLead = From the first question to a delivered order in four steps.
landing.h1 = Connect your catalog
landing.d1 = Add products, FAQs and store knowledge from the seller panel. The assistant only knows what you give it.
landing.h2 = Customers ask
landing.d2 = Shoppers chat about products, sizes, prices and policies, with no sign-up required.
landing.h3 = The assistant sells
landing.d3 = It finds the right product, fills the cart and collects delivery details, reading price and stock from your database every time.
landing.h4 = You fulfil
landing.d4 = Orders reach your panel with an invoice and a tracking number. Move them from pending to delivered.

# ---- landing: features
landing.features = Everything a store needs to sell by conversation
landing.featuresLead = One platform for the assistant, the storefront and the back office.
landing.f1.t = Answers from your own data
landing.f1.d = Retrieval runs over your products, FAQs and knowledge base and never crosses into another store. Optional semantic search understands rephrased questions.
landing.f2.t = Trusted prices and stock
landing.f2.d = The language model never invents a price or an inventory level. Both are read from the database at the moment of the answer.
landing.f3.t = Cart and checkout in chat
landing.f3.d = Add, change and remove items, confirm delivery details and place the order without leaving the conversation.
landing.f4.t = Orders, invoices, tracking
landing.f4.d = Every order gets a PDF invoice and a 10-digit tracking number that customers can look up at any time.
landing.f5.t = A real seller panel
landing.f5.d = Manage products, stock, orders and conversations, and read every chat to learn what customers actually ask.
landing.f6.t = Templates for {n} business types
landing.f6.d = Clothing, cafés, pharmacies, electronics, services and more. The product form adapts to the kind of business.
landing.f7.t = Five languages
landing.f7.d = The whole interface speaks Persian, English, Spanish, German and French, with right-to-left layout where needed.
landing.f8.t = Built with safeguards
landing.f8.d = Rate limiting, CSRF protection, idempotent checkout, verified accounts and automatic deletion of old conversation messages.

# ---- landing: assistant
landing.assistant = A salesperson that never sleeps
landing.assistantBody = The assistant behaves like your best shop assistant: it listens, checks the shelf and only then answers.
landing.can1 = Recommends products by need, size, colour or budget
landing.can2 = Checks live stock and price before it answers
landing.can3 = Answers delivery and return questions from your FAQs
landing.can4 = Places the order once the customer confirms
landing.q3 = How long does delivery take?
landing.a3 = According to this store's FAQ, orders ship within two business days and usually arrive in three to five days.
landing.q4 = Where is my order 4821903357?
landing.a4 = Order 4821903357 has been shipped. You can follow it at any time on the tracking page.

# ---- landing: showcase
landing.stores = Stores on NAVA
landing.storesLead = A random selection of live stores. Refresh to meet others.
landing.shuffle = Show others
landing.visit = Visit store
landing.productsCount = {n} products
landing.productsCount_one = {n} product
landing.storesEmpty = No stores yet. Be the first to open one.
landing.products = Fresh from the shelves
landing.productsLead = Random products from the stores above, straight from the database.
landing.productsEmpty = Products will appear here as soon as stores add them.
landing.by = by {store}

# ---- landing: business types
landing.types = Made for every kind of business
landing.typesLead = One platform, {n} ready-made product templates.
landing.typesMore = +{n} more

# ---- landing: sellers and buyers
landing.sellers = For sellers
landing.sellersBody = Give every visitor a knowledgeable shop assistant without hiring one.
landing.s1 = Set up a store in minutes, no developer needed
landing.s2 = Teach the assistant with FAQs and knowledge entries
landing.s3 = See every order, conversation and low-stock alert in one place
landing.buyers = For shoppers
landing.buyersBody = Ask a question the way you would ask in a shop and get a straight answer.
landing.y1 = Ask about products, sizes and prices in your own language
landing.y2 = Check out as a guest, then track the order with its number
landing.y3 = Download your invoice as a PDF

# ---- landing: faq
landing.faq = Frequently asked questions
faq.q1 = What is NAVA?
faq.a1 = NAVA is an AI sales assistant and storefront for online shops. Customers chat with the assistant, fill a cart and place orders, while sellers manage products, orders and conversations from a panel.
faq.q2 = Do customers need an account?
faq.a2 = No. Shoppers check out as guests. Their cart and order are tied to a private session token, and they can track the order with its 10-digit number.
faq.q3 = Can the assistant change prices or invent stock?
faq.a3 = No. Prices, stock and order totals are always read from the database by the application. The language model only writes the wording of the answer.
faq.q4 = Which languages are supported?
faq.a4 = The interface is available in Persian, English, Spanish, German and French. Pick a language from the switcher in the header or footer.
faq.q5 = How do I get started?
faq.a5 = Create a seller account, open a store, add a few products and FAQs, then share your store link. The live demo store shows what customers will see.
faq.q6 = What if the AI provider is unavailable?
faq.a6 = The assistant answers with a safe generic message and never exposes provider details. The storefront, cart and checkout keep working without it.

# ---- landing: final call to action
landing.ctaTitle = Ready to let your store do the talking?
landing.ctaBody = Create a store, add a few products and share the link. It takes minutes.

# ---- footer
footer.tagline = The AI sales assistant for online stores: from the first question to the delivered order.
footer.product = Product
footer.sellers = For sellers
footer.customers = For shoppers
footer.language = Language
footer.types = Business types
footer.rights = © {year} NAVA. All rights reserved.
footer.top = Back to top
footer.trust1.t = Safe checkout
footer.trust1.d = Idempotent orders, gateway-ready payments.
footer.trust2.t = Order tracking
footer.trust2.d = Look up any order by its 10-digit number.
footer.trust3.t = PDF invoices
footer.trust3.d = Every order comes with a downloadable invoice.
footer.trust4.t = Grounded answers
footer.trust4.d = Prices and stock straight from the database.

# ---- auth
auth.loginTitle = Sign in
auth.registerTitle = Create your seller account
auth.email = Email
auth.password = Password
auth.passwordHint = At least 8 characters.
auth.phone = Phone
auth.phoneHint = Used for an SMS verification code.
auth.loginSubmit = Sign in
auth.registerSubmit = Create account
auth.forgot = Forgot your password?
auth.noAccount = Don't have an account?
auth.haveAccount = Already have an account?
auth.backToLogin = Back to sign in
auth.verifyTitle = Verify your account
auth.verifyLead = We sent an 8-digit code to {email}.
auth.emailCode = Email verification code
auth.phoneCode = Phone verification code
auth.verifySubmit = Verify and continue
auth.unverified = Your account is not verified yet. Enter the code we sent you.
auth.verified = Your account is verified. You can sign in now.
auth.devHint = Development mode: the verification code is printed in the server log.
auth.forgotTitle = Reset your password
auth.forgotLead = Enter your email and we will send you a reset token.
auth.forgotSubmit = Send reset token
auth.forgotSent = If this email is registered, a reset token has been sent.
auth.haveToken = I already have a reset token
auth.resetTitle = Choose a new password
auth.resetToken = Reset token
auth.newPassword = New password
auth.resetSubmit = Change password
auth.resetDone = Your password was changed. Sign in with the new password.

# ---- forms
form.required = This field is required.
form.price = Enter a valid price.
form.stock = Stock must be a whole number, zero or more.
form.otp = Enter the 8-digit code.
form.tracking = Enter the 10-digit tracking number.

# ---- storefront
shop.search = Search products…
shop.inStockOnly = In stock only
shop.count = {n} products
shop.count_one = {n} product
shop.empty = No products found.
shop.add = Add to cart
shop.added = "{name}" was added to your cart
shop.ask = Ask the assistant
shop.askProduct = Tell me about {name}
shop.attributes = Details
shop.backToStore = Back to store
shop.qty = Quantity
shop.inStock = In stock ({n})
shop.lowStock = Only {n} left
shop.lowStock_one = Only {n} left
shop.outOfStock = Out of stock
shop.productNotFound = Product not found.
shop.storeNotFound = Store not found.
shop.poweredBy = Powered by NAVA
shop.createYours = Open your own store

# ---- chat
chat.title = Shopping assistant
chat.open = Ask the assistant
chat.placeholder = Type your question…
chat.send = Send
chat.typing = The assistant is typing
chat.welcome = Hi! I am the assistant of {store}. Ask me about products, prices or stock, or place an order right here.
chat.s1 = Which products are in stock?
chat.s2 = What is the cheapest item?
chat.s3 = Add the first product to my cart
chat.s4 = How can I track my order?

# ---- cart and checkout
cart.title = Shopping cart
cart.open = Open cart ({n} items)
cart.open_one = Open cart ({n} item)
cart.empty = Your cart is empty
cart.emptyHint = Add products from the store or ask the assistant to add them.
cart.total = Total
cart.checkout = Checkout
cart.clear = Clear cart
cart.dec = Decrease quantity of {name}
cart.inc = Increase quantity of {name}
cart.remove = Remove {name}
checkout.title = Checkout
checkout.name = Full name
checkout.phone = Phone number
checkout.email = Email
checkout.address = Delivery address
checkout.submit = Place order
checkout.back = Back to cart
order.placed = Order placed
order.number = Order number
order.tracking = Tracking number
order.items = Order items
order.pay = Pay now
order.paid = Payment received. Thank you!
order.sandbox = This is a sandbox payment. Confirm to simulate a successful payment.
order.sandboxConfirm = Confirm test payment
order.invoice = Download invoice (PDF)
order.trackLink = Track this order
order.continue = Continue shopping

# ---- order tracking and statuses
track.title = Track your order
track.lead = Enter the 10-digit tracking number you received at checkout.
track.number = Tracking number
track.submit = Track
track.store = Store
track.placedAt = Placed
track.updatedAt = Last update
track.cancelled = This order was cancelled.
status.pending = Pending
status.confirmed = Confirmed
status.preparing = Preparing
status.shipped = Shipped
status.delivered = Delivered
status.cancelled = Cancelled
cs.idle = Browsing
cs.awaiting_customer = Collecting details
cs.awaiting_confirmation = Awaiting confirmation
cs.completed = Completed

# ---- seller panel
s.overview = Overview
s.orders = Orders
s.conversations = Conversations
s.products = Products
s.knowledge = Knowledge
s.activeStore = Active store
s.viewStore = View store
s.logout = Sign out
s.needStore = Create a store first.
s.goOverview = Go to overview
s.noStoreTitle = You have no store yet
s.noStoreBody = Create your first store to start selling with the assistant.
s.storeName = Store name
s.businessType = Business type
s.storeDesc = Description
s.logo = Logo
s.editStore = Edit store
s.newStore = New store
s.storeCreated = Store created.
s.publicLink = Public link
s.deleteStore = Delete store
s.deleteStoreNote = Deleting a store permanently removes its products, FAQs and knowledge entries.
ov.orders = Orders
ov.value = Order value
ov.products = Active products
ov.conversations = Conversations
ov.attention = Needs attention
ov.allGood = Nothing needs your attention.
ov.pendingOrders = Pending orders
ov.lowStock = Low stock
ov.lowStockItem = {n} left
ov.recent = Recent conversations
o.empty = No orders yet.
o.search = Search by name, phone or tracking number
o.all = All
o.id = Order
o.customer = Customer
o.total = Total
o.status = Status
o.date = Date
od.title = Order {id}
od.next = Next step
od.final = This order is final.
od.moveTo = Move to "{status}"
od.cancelOrder = Cancel order
od.updated = Order updated.
od.phone = Phone
od.address = Address
od.invoice = Invoice number
od.date = Date
od.item = Item
od.unit = Unit price
od.qty = Qty
od.line = Line total
c.empty = No conversations yet.
c.guest = Guest {id}
c.noMessages = No messages
c.messages = {n} messages
c.messages_one = {n} message
c.order = Order {id}
c.user = Customer
c.assistant = Assistant
p.add = Add product
p.edit = Edit product
p.created = Product created.
p.updated = Product updated.
p.deleted = Product deleted.
p.empty = No products yet.
p.emptyHint = Add your first product so the assistant can sell it.
p.name = Name
p.price = Price
p.stock = Stock
p.desc = Description
p.image = Image
p.status = Status
p.reserved = {n} reserved
p.typeFields = {type} details
k.lead = The assistant answers from these entries. Keep them accurate and short.
k.tabKnowledge = Knowledge base
k.tabFaqs = FAQs
k.add = Add entry
k.editEntry = Edit entry
k.title = Title
k.content = Content
k.question = Question
k.answer = Answer
k.active = Active (used by the assistant)
k.emptyKnowledge = No knowledge entries yet.
k.emptyFaqs = No FAQs yet.
`)
