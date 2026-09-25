import { parseCatalog } from './parse'

export default parseCatalog(`
# ---- core
brand = NAVA
loading = Chargement…
retry = Réessayer
close = Fermer
copy = Copier
copied = Copié
cancel = Annuler
create = Créer
save = Enregistrer
saved = Enregistré
edit = Modifier
delete = Supprimer
deleted = Supprimé
yes = Oui
no = Non
show = Afficher
hide = Masquer
select = Sélectionner…
active = Actif
inactive = Inactif
optional = facultatif
a11y.skip = Aller au contenu
confirm.sure = Êtes-vous sûr ?
crash.title = Une erreur est survenue
notfound.title = Page introuvable
notfound.home = Retour à l'accueil

# ---- errors
err.generic = Une erreur est survenue. Veuillez réessayer.
err.network = Erreur réseau. Vérifiez votre connexion et réessayez.
err.rate = Trop de requêtes. Patientez un instant et réessayez.
err.auth = Veuillez vous reconnecter.
err.notFound = Nous n'avons pas trouvé ce que vous cherchiez.
err.server = Le serveur a rencontré un problème. Veuillez réessayer plus tard.
err.m.invalidCredentials = E-mail ou mot de passe incorrect.
err.m.emailTaken = Cette adresse e-mail est déjà enregistrée.
err.m.invalidCode = Le code est invalide ou a expiré.
err.m.invalidReset = Le jeton de réinitialisation est invalide ou a expiré.
err.m.needVerify = Veuillez d'abord vérifier votre compte.
err.m.sessionExpired = Votre session a expiré. Veuillez vous reconnecter.
err.m.stock = Le stock de ce produit est insuffisant.
err.m.cartEmpty = Votre panier est vide.
err.m.inactive = Ce produit n'est pas disponible.
err.m.qty = La quantité doit être comprise entre 1 et 100.
err.m.image = L'image n'est pas prise en charge ou est trop volumineuse.
err.m.paid = Cette commande est déjà payée.
err.m.notPending = Seules les commandes en attente peuvent être payées.
err.m.guest = Votre session d'achat a expiré. Veuillez réessayer.

# ---- navigation and header
nav.main = Navigation principale
nav.features = Fonctionnalités
nav.how = Comment ça marche
nav.stores = Boutiques
nav.demo = Démo en direct
nav.faq = FAQ
nav.track = Suivre une commande
nav.login = Connexion
nav.register = Commencer
nav.panel = Espace vendeur
nav.langName = Langue
nav.menu = Menu
nav.openMenu = Ouvrir le menu
nav.closeMenu = Fermer le menu
nav.home = Accueil NAVA

# ---- landing: hero
landing.badge = Commerce conversationnel par IA
landing.title = Transformez les visiteurs de votre boutique en clients, une conversation à la fois
landing.lead = NAVA est un assistant de vente par IA pour les boutiques en ligne. Il répond à partir de votre propre catalogue et de vos politiques, remplit le panier, enregistre la commande et émet une facture avec numéro de suivi, en cinq langues et à toute heure.
landing.cta = Essayer la boutique démo
landing.ctaSeller = Ouvrir votre boutique
landing.b1 = Prix et stock toujours issus de votre base de données
landing.b2 = Achat en tant qu'invité, sans compte
landing.b3 = Cinq langues dès l'installation
landing.q1 = Avez-vous le sweat noir en taille L ?
landing.a1 = Oui, le sweat noir en L est disponible (il en reste 3) à 890 000 tomans. Je l'ajoute à votre panier ?
landing.q2 = Oui, ajoutez-le, s'il vous plaît.
landing.a2 = C'est fait. Votre panier contient 1 article, 890 000 tomans au total. Envoyez-moi votre nom, votre téléphone et votre adresse pour passer la commande.
landing.chipStock = En stock
landing.chipOrder = Commande confirmée
landing.chipTracking = Numéro de suivi émis

# ---- landing: stats
landing.stat.stores = Boutiques actives
landing.stat.products = Produits en vente
landing.stat.types = Modèles métier
landing.stat.languages = Langues

# ---- landing: how it works
landing.how = Comment ça marche
landing.howLead = De la première question à la commande livrée en quatre étapes.
landing.h1 = Connectez votre catalogue
landing.d1 = Ajoutez produits, FAQ et connaissances de la boutique depuis l'espace vendeur. L'assistant ne connaît que ce que vous lui donnez.
landing.h2 = Les clients posent leurs questions
landing.d2 = Les acheteurs discutent produits, tailles, prix et politiques, sans inscription.
landing.h3 = L'assistant vend
landing.d3 = Il trouve le bon produit, remplit le panier et recueille les informations de livraison, en lisant chaque fois prix et stock dans votre base de données.
landing.h4 = Vous expédiez
landing.d4 = Les commandes arrivent dans votre espace avec une facture et un numéro de suivi. Faites-les passer d'en attente à livrée.

# ---- landing: features
landing.features = Tout ce qu'il faut à une boutique pour vendre en conversant
landing.featuresLead = Une seule plateforme pour l'assistant, la vitrine et le back-office.
landing.f1.t = Des réponses issues de vos données
landing.f1.d = La recherche porte sur vos produits, FAQ et base de connaissances, sans jamais toucher une autre boutique. La recherche sémantique facultative comprend les questions reformulées.
landing.f2.t = Prix et stock fiables
landing.f2.d = Le modèle de langage n'invente jamais un prix ni un niveau de stock. Les deux sont lus dans la base de données au moment de la réponse.
landing.f3.t = Panier et paiement dans le chat
landing.f3.d = Ajoutez, modifiez et retirez des articles, confirmez la livraison et passez commande sans quitter la conversation.
landing.f4.t = Commandes, factures, suivi
landing.f4.d = Chaque commande reçoit une facture PDF et un numéro de suivi à 10 chiffres que le client peut consulter à tout moment.
landing.f5.t = Un vrai espace vendeur
landing.f5.d = Gérez produits, stock, commandes et conversations, et lisez chaque chat pour savoir ce que vos clients demandent vraiment.
landing.f6.t = Modèles pour {n} types de commerce
landing.f6.d = Mode, cafés, pharmacies, électronique, services et plus encore. Le formulaire produit s'adapte au type de commerce.
landing.f7.t = Cinq langues
landing.f7.d = Toute l'interface parle persan, anglais, espagnol, allemand et français, avec une mise en page de droite à gauche si besoin.
landing.f8.t = Conçu avec des garde-fous
landing.f8.d = Limitation de débit, protection CSRF, commandes idempotentes, comptes vérifiés et suppression automatique des anciens messages.

# ---- landing: assistant
landing.assistant = Un vendeur qui ne dort jamais
landing.assistantBody = L'assistant se comporte comme votre meilleur vendeur en magasin : il écoute, regarde en rayon et seulement ensuite répond.
landing.can1 = Recommande des produits selon le besoin, la taille, la couleur ou le budget
landing.can2 = Vérifie le stock et le prix en direct avant de répondre
landing.can3 = Répond aux questions de livraison et de retour à partir de votre FAQ
landing.can4 = Passe la commande dès que le client confirme
landing.q3 = Quel est le délai de livraison ?
landing.a3 = D'après la FAQ de cette boutique, les commandes partent sous deux jours ouvrés et arrivent généralement en trois à cinq jours.
landing.q4 = Où en est ma commande 4821903357 ?
landing.a4 = La commande 4821903357 a été expédiée. Vous pouvez la suivre à tout moment sur la page de suivi.

# ---- landing: showcase
landing.stores = Les boutiques NAVA
landing.storesLead = Une sélection aléatoire de boutiques actives. Actualisez pour en découvrir d'autres.
landing.shuffle = En voir d'autres
landing.visit = Visiter la boutique
landing.productsCount = {n} produits
landing.productsCount_one = {n} produit
landing.storesEmpty = Aucune boutique pour l'instant. Soyez la première à en ouvrir une.
landing.products = Tout frais sorti des rayons
landing.productsLead = Des produits aléatoires des boutiques, directement depuis la base de données.
landing.productsEmpty = Les produits apparaîtront ici dès que les boutiques en ajouteront.
landing.by = de {store}

# ---- landing: business types
landing.types = Conçu pour tous les types de commerce
landing.typesLead = Une plateforme, {n} modèles de produits prêts à l'emploi.
landing.typesMore = +{n} autres

# ---- landing: sellers and buyers
landing.sellers = Pour les vendeurs
landing.sellersBody = Offrez à chaque visiteur un vendeur qui connaît votre catalogue, sans embaucher personne.
landing.s1 = Créez une boutique en quelques minutes, sans développeur
landing.s2 = Formez l'assistant avec des FAQ et des fiches de connaissances
landing.s3 = Consultez commandes, conversations et alertes de stock bas au même endroit
landing.buyers = Pour les acheteurs
landing.buyersBody = Posez votre question comme en boutique et obtenez une réponse claire.
landing.y1 = Posez vos questions sur produits, tailles et prix dans votre langue
landing.y2 = Achetez en invité et suivez la commande avec son numéro
landing.y3 = Téléchargez votre facture en PDF

# ---- landing: faq
landing.faq = Questions fréquentes
faq.q1 = Qu'est-ce que NAVA ?
faq.a1 = NAVA est un assistant de vente par IA avec vitrine pour les boutiques en ligne. Les clients discutent avec l'assistant, remplissent un panier et commandent, tandis que les vendeurs gèrent produits, commandes et conversations depuis un espace dédié.
faq.q2 = Les clients ont-ils besoin d'un compte ?
faq.a2 = Non. Les acheteurs commandent en invité. Leur panier et leur commande sont liés à un jeton de session privé, et ils suivent la commande avec son numéro à 10 chiffres.
faq.q3 = L'assistant peut-il modifier les prix ou inventer du stock ?
faq.a3 = Non. L'application lit toujours prix, stock et totaux de commande dans la base de données. Le modèle de langage ne fait que rédiger la réponse.
faq.q4 = Quelles langues sont disponibles ?
faq.a4 = L'interface est disponible en persan, anglais, espagnol, allemand et français. Choisissez la langue dans le sélecteur de l'en-tête ou du pied de page.
faq.q5 = Comment démarrer ?
faq.a5 = Créez un compte vendeur, ouvrez une boutique, ajoutez quelques produits et FAQ, puis partagez le lien de votre boutique. La boutique démo en direct montre ce que verront vos clients.
faq.q6 = Que se passe-t-il si le fournisseur d'IA est indisponible ?
faq.a6 = L'assistant répond par un message générique et sûr, sans jamais divulguer de détails sur le fournisseur. La vitrine, le panier et le paiement continuent de fonctionner sans lui.

# ---- landing: final call to action
landing.ctaTitle = Prêt à laisser votre boutique parler pour vous ?
landing.ctaBody = Créez une boutique, ajoutez quelques produits et partagez le lien. Cela ne prend que quelques minutes.

# ---- footer
footer.tagline = L'assistant de vente par IA pour les boutiques en ligne : de la première question à la commande livrée.
footer.product = Produit
footer.sellers = Pour les vendeurs
footer.customers = Pour les acheteurs
footer.language = Langue
footer.types = Types de commerce
footer.rights = © {year} NAVA. Tous droits réservés.
footer.top = Retour en haut
footer.trust1.t = Paiement sécurisé
footer.trust1.d = Commandes idempotentes, paiements prêts pour une passerelle.
footer.trust2.t = Suivi des commandes
footer.trust2.d = Retrouvez chaque commande avec son numéro à 10 chiffres.
footer.trust3.t = Factures PDF
footer.trust3.d = Chaque commande est accompagnée d'une facture téléchargeable.
footer.trust4.t = Réponses fondées
footer.trust4.d = Prix et stock directement issus de la base de données.

# ---- auth
auth.loginTitle = Connexion
auth.registerTitle = Créez votre compte vendeur
auth.email = E-mail
auth.password = Mot de passe
auth.passwordHint = Au moins 8 caractères.
auth.phone = Téléphone
auth.phoneHint = Utilisé pour le code de vérification par SMS.
auth.loginSubmit = Se connecter
auth.registerSubmit = Créer le compte
auth.forgot = Mot de passe oublié ?
auth.noAccount = Pas encore de compte ?
auth.haveAccount = Vous avez déjà un compte ?
auth.backToLogin = Retour à la connexion
auth.verifyTitle = Vérifiez votre compte
auth.verifyLead = Nous avons envoyé un code à 8 chiffres à {email}.
auth.emailCode = Code de vérification e-mail
auth.phoneCode = Code de vérification téléphone
auth.verifySubmit = Vérifier et continuer
auth.unverified = Votre compte n'est pas encore vérifié. Saisissez le code que nous vous avons envoyé.
auth.verified = Votre compte est vérifié. Vous pouvez vous connecter.
auth.devHint = Mode développement : le code de vérification est affiché dans le journal du serveur.
auth.forgotTitle = Réinitialisez votre mot de passe
auth.forgotLead = Saisissez votre e-mail et nous vous enverrons un jeton de réinitialisation.
auth.forgotSubmit = Envoyer le jeton
auth.forgotSent = Si cette adresse est enregistrée, un jeton de réinitialisation a été envoyé.
auth.haveToken = J'ai déjà un jeton
auth.resetTitle = Choisissez un nouveau mot de passe
auth.resetToken = Jeton de réinitialisation
auth.newPassword = Nouveau mot de passe
auth.resetSubmit = Changer le mot de passe
auth.resetDone = Votre mot de passe a été modifié. Connectez-vous avec le nouveau.

# ---- forms
form.required = Ce champ est obligatoire.
form.price = Saisissez un prix valide.
form.stock = Le stock doit être un nombre entier, zéro ou plus.
form.otp = Saisissez le code à 8 chiffres.
form.tracking = Saisissez le numéro de suivi à 10 chiffres.

# ---- storefront
shop.search = Rechercher des produits…
shop.inStockOnly = En stock uniquement
shop.count = {n} produits
shop.count_one = {n} produit
shop.empty = Aucun produit trouvé.
shop.add = Ajouter au panier
shop.added = « {name} » a été ajouté à votre panier
shop.ask = Demander à l'assistant
shop.askProduct = Parle-moi de {name}
shop.attributes = Détails
shop.backToStore = Retour à la boutique
shop.qty = Quantité
shop.inStock = En stock ({n})
shop.lowStock = Plus que {n}
shop.lowStock_one = Plus que {n}
shop.outOfStock = Rupture de stock
shop.productNotFound = Produit introuvable.
shop.storeNotFound = Boutique introuvable.
shop.poweredBy = Propulsé par NAVA
shop.createYours = Ouvrez votre propre boutique

# ---- chat
chat.title = Assistant d'achat
chat.open = Demander à l'assistant
chat.placeholder = Écrivez votre question…
chat.send = Envoyer
chat.typing = L'assistant est en train d'écrire
chat.welcome = Bonjour ! Je suis l'assistant de {store}. Posez-moi vos questions sur les produits, les prix ou le stock, ou commandez directement ici.
chat.s1 = Quels produits sont en stock ?
chat.s2 = Quel est l'article le moins cher ?
chat.s3 = Ajoute le premier produit à mon panier
chat.s4 = Comment suivre ma commande ?

# ---- cart and checkout
cart.title = Panier
cart.open = Ouvrir le panier ({n} articles)
cart.open_one = Ouvrir le panier ({n} article)
cart.empty = Votre panier est vide
cart.emptyHint = Ajoutez des produits de la boutique ou demandez à l'assistant de le faire.
cart.total = Total
cart.checkout = Passer la commande
cart.clear = Vider le panier
cart.dec = Diminuer la quantité de {name}
cart.inc = Augmenter la quantité de {name}
cart.remove = Retirer {name}
checkout.title = Paiement
checkout.name = Nom complet
checkout.phone = Numéro de téléphone
checkout.email = E-mail
checkout.address = Adresse de livraison
checkout.submit = Passer la commande
checkout.back = Retour au panier
order.placed = Commande passée
order.number = Numéro de commande
order.tracking = Numéro de suivi
order.items = Articles de la commande
order.pay = Payer maintenant
order.paid = Paiement reçu. Merci !
order.sandbox = Il s'agit d'un paiement de test. Confirmez pour simuler un paiement réussi.
order.sandboxConfirm = Confirmer le paiement de test
order.invoice = Télécharger la facture (PDF)
order.trackLink = Suivre cette commande
order.continue = Continuer mes achats

# ---- order tracking and statuses
track.title = Suivez votre commande
track.lead = Saisissez le numéro de suivi à 10 chiffres reçu lors du paiement.
track.number = Numéro de suivi
track.submit = Suivre
track.store = Boutique
track.placedAt = Passée le
track.updatedAt = Dernière mise à jour
track.cancelled = Cette commande a été annulée.
status.pending = En attente
status.confirmed = Confirmée
status.preparing = En préparation
status.shipped = Expédiée
status.delivered = Livrée
status.cancelled = Annulée
cs.idle = Navigation
cs.awaiting_customer = Collecte des informations
cs.awaiting_confirmation = En attente de confirmation
cs.completed = Terminée

# ---- seller panel
s.overview = Vue d'ensemble
s.orders = Commandes
s.conversations = Conversations
s.products = Produits
s.knowledge = Connaissances
s.activeStore = Boutique active
s.viewStore = Voir la boutique
s.logout = Se déconnecter
s.needStore = Créez d'abord une boutique.
s.goOverview = Aller à la vue d'ensemble
s.noStoreTitle = Vous n'avez pas encore de boutique
s.noStoreBody = Créez votre première boutique pour commencer à vendre avec l'assistant.
s.storeName = Nom de la boutique
s.businessType = Type de commerce
s.storeDesc = Description
s.logo = Logo
s.editStore = Modifier la boutique
s.newStore = Nouvelle boutique
s.storeCreated = Boutique créée.
s.publicLink = Lien public
s.deleteStore = Supprimer la boutique
s.deleteStoreNote = Supprimer une boutique efface définitivement ses produits, FAQ et fiches de connaissances.
ov.orders = Commandes
ov.value = Valeur des commandes
ov.products = Produits actifs
ov.conversations = Conversations
ov.attention = À surveiller
ov.allGood = Rien ne demande votre attention.
ov.pendingOrders = Commandes en attente
ov.lowStock = Stock bas
ov.lowStockItem = Plus que {n}
ov.recent = Conversations récentes
o.empty = Aucune commande pour l'instant.
o.search = Rechercher par nom, téléphone ou numéro de suivi
o.all = Toutes
o.id = Commande
o.customer = Client
o.total = Total
o.status = Statut
o.date = Date
od.title = Commande {id}
od.next = Étape suivante
od.final = Cette commande est dans son état final.
od.moveTo = Passer à « {status} »
od.cancelOrder = Annuler la commande
od.updated = Commande mise à jour.
od.phone = Téléphone
od.address = Adresse
od.invoice = Numéro de facture
od.date = Date
od.item = Article
od.unit = Prix unitaire
od.qty = Qté
od.line = Total ligne
c.empty = Aucune conversation pour l'instant.
c.guest = Invité {id}
c.noMessages = Aucun message
c.messages = {n} messages
c.messages_one = {n} message
c.order = Commande {id}
c.user = Client
c.assistant = Assistant
p.add = Ajouter un produit
p.edit = Modifier le produit
p.created = Produit créé.
p.updated = Produit mis à jour.
p.deleted = Produit supprimé.
p.empty = Aucun produit pour l'instant.
p.emptyHint = Ajoutez votre premier produit pour que l'assistant puisse le vendre.
p.name = Nom
p.price = Prix
p.stock = Stock
p.desc = Description
p.image = Image
p.status = Statut
p.reserved = {n} réservés
p.typeFields = Détails : {type}
k.lead = L'assistant répond à partir de ces fiches. Gardez-les exactes et courtes.
k.tabKnowledge = Base de connaissances
k.tabFaqs = FAQ
k.add = Ajouter une fiche
k.editEntry = Modifier la fiche
k.title = Titre
k.content = Contenu
k.question = Question
k.answer = Réponse
k.active = Active (utilisée par l'assistant)
k.emptyKnowledge = Aucune fiche de connaissances pour l'instant.
k.emptyFaqs = Aucune FAQ pour l'instant.
`)
