import { parseCatalog } from './parse'

export default parseCatalog(`
# ---- core
brand = NAVA
loading = Cargando…
retry = Reintentar
close = Cerrar
copy = Copiar
copied = Copiado
cancel = Cancelar
create = Crear
save = Guardar
saved = Guardado
edit = Editar
delete = Eliminar
deleted = Eliminado
yes = Sí
no = No
show = Mostrar
hide = Ocultar
select = Seleccionar…
active = Activo
inactive = Inactivo
optional = opcional
a11y.skip = Saltar al contenido
confirm.sure = ¿Seguro?
crash.title = Algo salió mal
notfound.title = Página no encontrada
notfound.home = Volver al inicio

# ---- errors
err.generic = Algo salió mal. Inténtalo de nuevo.
err.network = Error de red. Comprueba tu conexión e inténtalo de nuevo.
err.rate = Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.
err.auth = Inicia sesión de nuevo.
err.notFound = No encontramos lo que buscabas.
err.server = El servidor tuvo un problema. Inténtalo más tarde.
err.m.invalidCredentials = Correo o contraseña incorrectos.
err.m.emailTaken = Este correo ya está registrado.
err.m.invalidCode = El código no es válido o ha caducado.
err.m.invalidReset = El token de restablecimiento no es válido o ha caducado.
err.m.needVerify = Verifica primero tu cuenta.
err.m.sessionExpired = Tu sesión ha caducado. Inicia sesión de nuevo.
err.m.stock = No hay existencias suficientes de este producto.
err.m.cartEmpty = Tu carrito está vacío.
err.m.inactive = Este producto no está disponible.
err.m.qty = La cantidad debe estar entre 1 y 100.
err.m.image = La imagen no es compatible o es demasiado grande.
err.m.paid = Este pedido ya está pagado.
err.m.notPending = Solo se pueden pagar los pedidos pendientes.
err.m.guest = Tu sesión de compra ha caducado. Inténtalo de nuevo.

# ---- navigation and header
nav.main = Navegación principal
nav.features = Funciones
nav.how = Cómo funciona
nav.stores = Tiendas
nav.demo = Demo en vivo
nav.faq = Preguntas frecuentes
nav.track = Seguir pedido
nav.login = Iniciar sesión
nav.register = Empezar
nav.panel = Panel de vendedor
nav.langName = Idioma
nav.menu = Menú
nav.openMenu = Abrir menú
nav.closeMenu = Cerrar menú
nav.home = Inicio de NAVA

# ---- landing: hero
landing.badge = Comercio conversacional con IA
landing.title = Convierte a los visitantes de tu tienda en clientes, conversación a conversación
landing.lead = NAVA es un asistente de ventas con IA para tiendas online. Responde con tu propio catálogo y tus políticas, llena el carrito, registra el pedido y emite una factura con seguimiento, en cinco idiomas y a cualquier hora.
landing.cta = Probar la tienda demo
landing.ctaSeller = Abre tu tienda
landing.b1 = Los precios y el stock siempre salen de tu base de datos
landing.b2 = Compra como invitado, sin cuenta
landing.b3 = Cinco idiomas de serie
landing.q1 = ¿Tenéis la sudadera negra en talla L?
landing.a1 = Sí, la sudadera negra en L está disponible (quedan 3) por 890.000 tomanes. ¿La añado a tu carrito?
landing.q2 = Sí, añádela, por favor.
landing.a2 = Hecho. Tu carrito tiene 1 artículo, 890.000 tomanes en total. Envíame tu nombre, teléfono y dirección para registrar el pedido.
landing.chipStock = Disponible
landing.chipOrder = Pedido confirmado
landing.chipTracking = Número de seguimiento emitido

# ---- landing: stats
landing.stat.stores = Tiendas activas
landing.stat.products = Productos a la venta
landing.stat.types = Plantillas de negocio
landing.stat.languages = Idiomas

# ---- landing: how it works
landing.how = Cómo funciona
landing.howLead = De la primera pregunta al pedido entregado en cuatro pasos.
landing.h1 = Conecta tu catálogo
landing.d1 = Añade productos, preguntas frecuentes y conocimiento de la tienda desde el panel. El asistente solo sabe lo que tú le das.
landing.h2 = Los clientes preguntan
landing.d2 = Los compradores hablan sobre productos, tallas, precios y políticas, sin necesidad de registrarse.
landing.h3 = El asistente vende
landing.d3 = Encuentra el producto adecuado, llena el carrito y recoge los datos de entrega, leyendo precio y stock de tu base de datos cada vez.
landing.h4 = Tú envías
landing.d4 = Los pedidos llegan a tu panel con factura y número de seguimiento. Llévalos de pendiente a entregado.

# ---- landing: features
landing.features = Todo lo que una tienda necesita para vender conversando
landing.featuresLead = Una sola plataforma para el asistente, el escaparate y la gestión interna.
landing.f1.t = Respuestas con tus propios datos
landing.f1.d = La búsqueda se hace sobre tus productos, preguntas frecuentes y base de conocimiento, y nunca pasa a otra tienda. La búsqueda semántica opcional entiende preguntas reformuladas.
landing.f2.t = Precios y stock fiables
landing.f2.d = El modelo de lenguaje nunca inventa un precio ni un nivel de inventario. Ambos se leen de la base de datos en el momento de responder.
landing.f3.t = Carrito y pago en el chat
landing.f3.d = Añade, cambia y quita artículos, confirma los datos de entrega y haz el pedido sin salir de la conversación.
landing.f4.t = Pedidos, facturas y seguimiento
landing.f4.d = Cada pedido tiene una factura en PDF y un número de seguimiento de 10 dígitos que el cliente puede consultar cuando quiera.
landing.f5.t = Un panel de vendedor de verdad
landing.f5.d = Gestiona productos, stock, pedidos y conversaciones, y lee cada chat para saber qué preguntan realmente tus clientes.
landing.f6.t = Plantillas para {n} tipos de negocio
landing.f6.d = Moda, cafeterías, farmacias, electrónica, servicios y más. El formulario de producto se adapta al tipo de negocio.
landing.f7.t = Cinco idiomas
landing.f7.d = Toda la interfaz habla persa, inglés, español, alemán y francés, con diseño de derecha a izquierda cuando hace falta.
landing.f8.t = Con medidas de seguridad
landing.f8.d = Límite de peticiones, protección CSRF, pagos idempotentes, cuentas verificadas y borrado automático de mensajes antiguos.

# ---- landing: assistant
landing.assistant = Un vendedor que nunca duerme
landing.assistantBody = El asistente se comporta como tu mejor dependiente: escucha, mira el estante y solo después responde.
landing.can1 = Recomienda productos según necesidad, talla, color o presupuesto
landing.can2 = Comprueba el stock y el precio en vivo antes de responder
landing.can3 = Responde dudas de envío y devoluciones con tus preguntas frecuentes
landing.can4 = Registra el pedido cuando el cliente lo confirma
landing.q3 = ¿Cuánto tarda el envío?
landing.a3 = Según las preguntas frecuentes de esta tienda, los pedidos salen en dos días laborables y suelen llegar en tres a cinco días.
landing.q4 = ¿Dónde está mi pedido 4821903357?
landing.a4 = El pedido 4821903357 ha sido enviado. Puedes seguirlo cuando quieras en la página de seguimiento.

# ---- landing: showcase
landing.stores = Tiendas en NAVA
landing.storesLead = Una selección aleatoria de tiendas activas. Actualiza para conocer otras.
landing.shuffle = Mostrar otras
landing.visit = Visitar tienda
landing.productsCount = {n} productos
landing.productsCount_one = {n} producto
landing.storesEmpty = Aún no hay tiendas. Sé la primera en abrir una.
landing.products = Recién salidos de los estantes
landing.productsLead = Productos aleatorios de las tiendas, directamente de la base de datos.
landing.productsEmpty = Los productos aparecerán aquí en cuanto las tiendas los añadan.
landing.by = de {store}

# ---- landing: business types
landing.types = Hecho para cualquier tipo de negocio
landing.typesLead = Una plataforma, {n} plantillas de producto listas para usar.
landing.typesMore = +{n} más

# ---- landing: sellers and buyers
landing.sellers = Para vendedores
landing.sellersBody = Da a cada visitante un dependiente que conoce tu catálogo, sin contratar a nadie.
landing.s1 = Crea una tienda en minutos, sin desarrolladores
landing.s2 = Enseña al asistente con preguntas frecuentes y fichas de conocimiento
landing.s3 = Consulta pedidos, conversaciones y alertas de poco stock en un solo lugar
landing.buyers = Para compradores
landing.buyersBody = Pregunta como lo harías en una tienda y recibe una respuesta clara.
landing.y1 = Pregunta por productos, tallas y precios en tu idioma
landing.y2 = Compra como invitado y sigue el pedido con su número
landing.y3 = Descarga tu factura en PDF

# ---- landing: faq
landing.faq = Preguntas frecuentes
faq.q1 = ¿Qué es NAVA?
faq.a1 = NAVA es un asistente de ventas con IA y un escaparate para tiendas online. Los clientes hablan con el asistente, llenan el carrito y hacen pedidos, mientras los vendedores gestionan productos, pedidos y conversaciones desde un panel.
faq.q2 = ¿Los clientes necesitan una cuenta?
faq.a2 = No. Los compradores pagan como invitados. Su carrito y su pedido van ligados a un token de sesión privado y pueden seguir el pedido con su número de 10 dígitos.
faq.q3 = ¿Puede el asistente cambiar precios o inventar stock?
faq.a3 = No. La aplicación lee siempre de la base de datos los precios, el stock y los totales del pedido. El modelo de lenguaje solo redacta la respuesta.
faq.q4 = ¿Qué idiomas están disponibles?
faq.a4 = La interfaz está disponible en persa, inglés, español, alemán y francés. Elige el idioma en el selector del encabezado o del pie de página.
faq.q5 = ¿Cómo empiezo?
faq.a5 = Crea una cuenta de vendedor, abre una tienda, añade algunos productos y preguntas frecuentes y comparte el enlace de tu tienda. La tienda demo en vivo muestra lo que verán tus clientes.
faq.q6 = ¿Qué pasa si el proveedor de IA no está disponible?
faq.a6 = El asistente responde con un mensaje genérico y seguro, y nunca revela detalles del proveedor. El escaparate, el carrito y el pago siguen funcionando sin él.

# ---- landing: final call to action
landing.ctaTitle = ¿Listo para que tu tienda hable por ti?
landing.ctaBody = Crea una tienda, añade unos productos y comparte el enlace. Solo lleva unos minutos.

# ---- footer
footer.tagline = El asistente de ventas con IA para tiendas online: de la primera pregunta al pedido entregado.
footer.product = Producto
footer.sellers = Para vendedores
footer.customers = Para compradores
footer.language = Idioma
footer.types = Tipos de negocio
footer.rights = © {year} NAVA. Todos los derechos reservados.
footer.top = Volver arriba
footer.trust1.t = Pago seguro
footer.trust1.d = Pedidos idempotentes y pagos listos para pasarela.
footer.trust2.t = Seguimiento de pedidos
footer.trust2.d = Consulta cualquier pedido con su número de 10 dígitos.
footer.trust3.t = Facturas en PDF
footer.trust3.d = Cada pedido incluye una factura descargable.
footer.trust4.t = Respuestas fundamentadas
footer.trust4.d = Precios y stock directamente de la base de datos.

# ---- auth
auth.loginTitle = Iniciar sesión
auth.registerTitle = Crea tu cuenta de vendedor
auth.email = Correo electrónico
auth.password = Contraseña
auth.passwordHint = Al menos 8 caracteres.
auth.phone = Teléfono
auth.phoneHint = Se usa para el código de verificación por SMS.
auth.loginSubmit = Iniciar sesión
auth.registerSubmit = Crear cuenta
auth.forgot = ¿Olvidaste tu contraseña?
auth.noAccount = ¿No tienes cuenta?
auth.haveAccount = ¿Ya tienes cuenta?
auth.backToLogin = Volver a iniciar sesión
auth.verifyTitle = Verifica tu cuenta
auth.verifyLead = Hemos enviado un código de 8 dígitos a {email}.
auth.emailCode = Código de verificación del correo
auth.phoneCode = Código de verificación del teléfono
auth.verifySubmit = Verificar y continuar
auth.unverified = Tu cuenta aún no está verificada. Introduce el código que te enviamos.
auth.verified = Tu cuenta está verificada. Ya puedes iniciar sesión.
auth.devHint = Modo desarrollo: el código de verificación se imprime en el registro del servidor.
auth.forgotTitle = Restablece tu contraseña
auth.forgotLead = Introduce tu correo y te enviaremos un token de restablecimiento.
auth.forgotSubmit = Enviar token
auth.forgotSent = Si este correo está registrado, se ha enviado un token de restablecimiento.
auth.haveToken = Ya tengo un token
auth.resetTitle = Elige una nueva contraseña
auth.resetToken = Token de restablecimiento
auth.newPassword = Nueva contraseña
auth.resetSubmit = Cambiar contraseña
auth.resetDone = Tu contraseña se ha cambiado. Inicia sesión con la nueva.

# ---- forms
form.required = Este campo es obligatorio.
form.price = Introduce un precio válido.
form.stock = El stock debe ser un número entero, cero o más.
form.otp = Introduce el código de 8 dígitos.
form.tracking = Introduce el número de seguimiento de 10 dígitos.

# ---- storefront
shop.search = Buscar productos…
shop.inStockOnly = Solo disponibles
shop.count = {n} productos
shop.count_one = {n} producto
shop.empty = No se encontraron productos.
shop.add = Añadir al carrito
shop.added = "{name}" se añadió a tu carrito
shop.ask = Preguntar al asistente
shop.askProduct = Háblame de {name}
shop.attributes = Detalles
shop.backToStore = Volver a la tienda
shop.qty = Cantidad
shop.inStock = Disponible ({n})
shop.lowStock = Solo quedan {n}
shop.lowStock_one = Solo queda {n}
shop.outOfStock = Agotado
shop.productNotFound = Producto no encontrado.
shop.storeNotFound = Tienda no encontrada.
shop.poweredBy = Con tecnología de NAVA
shop.createYours = Abre tu propia tienda

# ---- chat
chat.title = Asistente de compras
chat.open = Preguntar al asistente
chat.placeholder = Escribe tu pregunta…
chat.send = Enviar
chat.typing = El asistente está escribiendo
chat.welcome = ¡Hola! Soy el asistente de {store}. Pregúntame por productos, precios o stock, o haz tu pedido aquí mismo.
chat.s1 = ¿Qué productos hay disponibles?
chat.s2 = ¿Cuál es el artículo más barato?
chat.s3 = Añade el primer producto a mi carrito
chat.s4 = ¿Cómo puedo seguir mi pedido?

# ---- cart and checkout
cart.title = Carrito de compra
cart.open = Abrir carrito ({n} artículos)
cart.open_one = Abrir carrito ({n} artículo)
cart.empty = Tu carrito está vacío
cart.emptyHint = Añade productos de la tienda o pídeselo al asistente.
cart.total = Total
cart.checkout = Finalizar compra
cart.clear = Vaciar carrito
cart.dec = Reducir la cantidad de {name}
cart.inc = Aumentar la cantidad de {name}
cart.remove = Quitar {name}
checkout.title = Finalizar compra
checkout.name = Nombre completo
checkout.phone = Teléfono
checkout.email = Correo electrónico
checkout.address = Dirección de entrega
checkout.submit = Hacer pedido
checkout.back = Volver al carrito
order.placed = Pedido realizado
order.number = Número de pedido
order.tracking = Número de seguimiento
order.items = Artículos del pedido
order.pay = Pagar ahora
order.paid = Pago recibido. ¡Gracias!
order.sandbox = Este es un pago de prueba. Confirma para simular un pago correcto.
order.sandboxConfirm = Confirmar pago de prueba
order.invoice = Descargar factura (PDF)
order.trackLink = Seguir este pedido
order.continue = Seguir comprando

# ---- order tracking and statuses
track.title = Sigue tu pedido
track.lead = Introduce el número de seguimiento de 10 dígitos que recibiste al finalizar la compra.
track.number = Número de seguimiento
track.submit = Seguir
track.store = Tienda
track.placedAt = Realizado
track.updatedAt = Última actualización
track.cancelled = Este pedido fue cancelado.
status.pending = Pendiente
status.confirmed = Confirmado
status.preparing = En preparación
status.shipped = Enviado
status.delivered = Entregado
status.cancelled = Cancelado
cs.idle = Explorando
cs.awaiting_customer = Recogiendo datos
cs.awaiting_confirmation = Esperando confirmación
cs.completed = Completada

# ---- seller panel
s.overview = Resumen
s.orders = Pedidos
s.conversations = Conversaciones
s.products = Productos
s.knowledge = Conocimiento
s.activeStore = Tienda activa
s.viewStore = Ver tienda
s.logout = Cerrar sesión
s.needStore = Crea primero una tienda.
s.goOverview = Ir al resumen
s.noStoreTitle = Aún no tienes ninguna tienda
s.noStoreBody = Crea tu primera tienda para empezar a vender con el asistente.
s.storeName = Nombre de la tienda
s.businessType = Tipo de negocio
s.storeDesc = Descripción
s.logo = Logotipo
s.editStore = Editar tienda
s.newStore = Nueva tienda
s.storeCreated = Tienda creada.
s.publicLink = Enlace público
s.deleteStore = Eliminar tienda
s.deleteStoreNote = Eliminar una tienda borra de forma permanente sus productos, preguntas frecuentes y fichas de conocimiento.
ov.orders = Pedidos
ov.value = Valor de los pedidos
ov.products = Productos activos
ov.conversations = Conversaciones
ov.attention = Requiere atención
ov.allGood = Nada requiere tu atención.
ov.pendingOrders = Pedidos pendientes
ov.lowStock = Poco stock
ov.lowStockItem = Quedan {n}
ov.recent = Conversaciones recientes
o.empty = Aún no hay pedidos.
o.search = Buscar por nombre, teléfono o número de seguimiento
o.all = Todos
o.id = Pedido
o.customer = Cliente
o.total = Total
o.status = Estado
o.date = Fecha
od.title = Pedido {id}
od.next = Siguiente paso
od.final = Este pedido ya está en su estado final.
od.moveTo = Pasar a "{status}"
od.cancelOrder = Cancelar pedido
od.updated = Pedido actualizado.
od.phone = Teléfono
od.address = Dirección
od.invoice = Número de factura
od.date = Fecha
od.item = Artículo
od.unit = Precio unitario
od.qty = Cant.
od.line = Total de línea
c.empty = Aún no hay conversaciones.
c.guest = Invitado {id}
c.noMessages = Sin mensajes
c.messages = {n} mensajes
c.messages_one = {n} mensaje
c.order = Pedido {id}
c.user = Cliente
c.assistant = Asistente
p.add = Añadir producto
p.edit = Editar producto
p.created = Producto creado.
p.updated = Producto actualizado.
p.deleted = Producto eliminado.
p.empty = Aún no hay productos.
p.emptyHint = Añade tu primer producto para que el asistente pueda venderlo.
p.name = Nombre
p.price = Precio
p.stock = Stock
p.desc = Descripción
p.image = Imagen
p.status = Estado
p.reserved = {n} reservados
p.typeFields = Detalles de {type}
k.lead = El asistente responde a partir de estas fichas. Mantenlas precisas y breves.
k.tabKnowledge = Base de conocimiento
k.tabFaqs = Preguntas frecuentes
k.add = Añadir ficha
k.editEntry = Editar ficha
k.title = Título
k.content = Contenido
k.question = Pregunta
k.answer = Respuesta
k.active = Activa (la usa el asistente)
k.emptyKnowledge = Aún no hay fichas de conocimiento.
k.emptyFaqs = Aún no hay preguntas frecuentes.
`)
