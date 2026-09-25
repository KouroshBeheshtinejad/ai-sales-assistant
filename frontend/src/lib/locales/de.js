import { parseCatalog } from './parse'

export default parseCatalog(`
# ---- core
brand = NAVA
loading = Wird geladen…
retry = Erneut versuchen
close = Schließen
copy = Kopieren
copied = Kopiert
cancel = Abbrechen
create = Erstellen
save = Speichern
saved = Gespeichert
edit = Bearbeiten
delete = Löschen
deleted = Gelöscht
yes = Ja
no = Nein
show = Anzeigen
hide = Verbergen
select = Auswählen…
active = Aktiv
inactive = Inaktiv
optional = optional
a11y.skip = Zum Inhalt springen
confirm.sure = Sind Sie sicher?
crash.title = Etwas ist schiefgelaufen
notfound.title = Seite nicht gefunden
notfound.home = Zurück zur Startseite

# ---- errors
err.generic = Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.
err.network = Netzwerkfehler. Prüfen Sie Ihre Verbindung und versuchen Sie es erneut.
err.rate = Zu viele Anfragen. Bitte warten Sie einen Moment und versuchen Sie es erneut.
err.auth = Bitte melden Sie sich erneut an.
err.notFound = Wir konnten nicht finden, was Sie suchen.
err.server = Auf dem Server ist ein Problem aufgetreten. Bitte versuchen Sie es später erneut.
err.m.invalidCredentials = E-Mail oder Passwort ist falsch.
err.m.emailTaken = Diese E-Mail-Adresse ist bereits registriert.
err.m.invalidCode = Der Code ist ungültig oder abgelaufen.
err.m.invalidReset = Das Zurücksetzungs-Token ist ungültig oder abgelaufen.
err.m.needVerify = Bitte bestätigen Sie zuerst Ihr Konto.
err.m.sessionExpired = Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.
err.m.stock = Von diesem Produkt ist nicht genug auf Lager.
err.m.cartEmpty = Ihr Warenkorb ist leer.
err.m.inactive = Dieses Produkt ist nicht verfügbar.
err.m.qty = Die Menge muss zwischen 1 und 100 liegen.
err.m.image = Das Bild wird nicht unterstützt oder ist zu groß.
err.m.paid = Diese Bestellung ist bereits bezahlt.
err.m.notPending = Nur offene Bestellungen können bezahlt werden.
err.m.guest = Ihre Einkaufssitzung ist abgelaufen. Bitte versuchen Sie es erneut.

# ---- navigation and header
nav.main = Hauptnavigation
nav.features = Funktionen
nav.how = So funktioniert es
nav.stores = Shops
nav.demo = Live-Demo
nav.faq = FAQ
nav.track = Bestellung verfolgen
nav.login = Anmelden
nav.register = Loslegen
nav.panel = Verkäuferbereich
nav.langName = Sprache
nav.menu = Menü
nav.openMenu = Menü öffnen
nav.closeMenu = Menü schließen
nav.home = NAVA Startseite

# ---- landing: hero
landing.badge = KI-gestützter Dialog-Handel
landing.title = Machen Sie Shop-Besucher zu Kunden, Gespräch für Gespräch
landing.lead = NAVA ist ein KI-Verkaufsassistent für Online-Shops. Er antwortet aus Ihrem eigenen Katalog und Ihren Richtlinien, füllt den Warenkorb, nimmt die Bestellung auf und stellt eine Rechnung mit Sendungsnummer aus, in fünf Sprachen und rund um die Uhr.
landing.cta = Demo-Shop ausprobieren
landing.ctaSeller = Eigenen Shop eröffnen
landing.b1 = Preise und Bestand kommen immer aus Ihrer Datenbank
landing.b2 = Gastbestellung ohne Konto
landing.b3 = Fünf Sprachen von Haus aus
landing.q1 = Haben Sie den schwarzen Hoodie in Größe L?
landing.a1 = Ja, der schwarze Hoodie in L ist lieferbar (noch 3 Stück) für 890.000 Toman. Soll ich ihn in den Warenkorb legen?
landing.q2 = Ja, bitte.
landing.a2 = Erledigt. Ihr Warenkorb enthält 1 Artikel, insgesamt 890.000 Toman. Senden Sie mir Name, Telefonnummer und Adresse, um die Bestellung aufzugeben.
landing.chipStock = Auf Lager
landing.chipOrder = Bestellung bestätigt
landing.chipTracking = Sendungsnummer vergeben

# ---- landing: stats
landing.stat.stores = Aktive Shops
landing.stat.products = Produkte im Angebot
landing.stat.types = Branchenvorlagen
landing.stat.languages = Sprachen

# ---- landing: how it works
landing.how = So funktioniert es
landing.howLead = Von der ersten Frage bis zur gelieferten Bestellung in vier Schritten.
landing.h1 = Katalog verbinden
landing.d1 = Fügen Sie Produkte, FAQs und Shop-Wissen im Verkäuferbereich hinzu. Der Assistent kennt nur, was Sie ihm geben.
landing.h2 = Kunden fragen
landing.d2 = Käufer chatten über Produkte, Größen, Preise und Richtlinien, ganz ohne Registrierung.
landing.h3 = Der Assistent verkauft
landing.d3 = Er findet das passende Produkt, füllt den Warenkorb und erfragt die Lieferdaten und liest Preis und Bestand jedes Mal aus Ihrer Datenbank.
landing.h4 = Sie liefern
landing.d4 = Bestellungen erreichen Ihren Bereich mit Rechnung und Sendungsnummer. Bringen Sie sie von „offen“ bis „geliefert“.

# ---- landing: features
landing.features = Alles, was ein Shop braucht, um im Gespräch zu verkaufen
landing.featuresLead = Eine Plattform für Assistent, Schaufenster und Backoffice.
landing.f1.t = Antworten aus Ihren eigenen Daten
landing.f1.d = Die Suche läuft über Ihre Produkte, FAQs und Wissensdatenbank und greift nie auf einen anderen Shop zu. Die optionale semantische Suche versteht umformulierte Fragen.
landing.f2.t = Verlässliche Preise und Bestände
landing.f2.d = Das Sprachmodell erfindet niemals einen Preis oder Lagerbestand. Beides wird im Moment der Antwort aus der Datenbank gelesen.
landing.f3.t = Warenkorb und Kasse im Chat
landing.f3.d = Artikel hinzufügen, ändern und entfernen, Lieferdaten bestätigen und bestellen, ohne das Gespräch zu verlassen.
landing.f4.t = Bestellungen, Rechnungen, Tracking
landing.f4.d = Jede Bestellung erhält eine PDF-Rechnung und eine 10-stellige Sendungsnummer, die Kunden jederzeit abrufen können.
landing.f5.t = Ein echter Verkäuferbereich
landing.f5.d = Verwalten Sie Produkte, Bestand, Bestellungen und Gespräche und lesen Sie jeden Chat, um zu sehen, was Kunden wirklich fragen.
landing.f6.t = Vorlagen für {n} Branchen
landing.f6.d = Mode, Cafés, Apotheken, Elektronik, Dienstleistungen und mehr. Das Produktformular passt sich der Branche an.
landing.f7.t = Fünf Sprachen
landing.f7.d = Die gesamte Oberfläche spricht Persisch, Englisch, Spanisch, Deutsch und Französisch, mit Rechts-nach-links-Layout, wo nötig.
landing.f8.t = Mit Schutzmaßnahmen gebaut
landing.f8.d = Ratenbegrenzung, CSRF-Schutz, idempotente Bestellungen, verifizierte Konten und automatische Löschung alter Gesprächsnachrichten.

# ---- landing: assistant
landing.assistant = Ein Verkäufer, der nie schläft
landing.assistantBody = Der Assistent verhält sich wie Ihr bester Verkäufer im Laden: Er hört zu, schaut ins Regal und antwortet erst dann.
landing.can1 = Empfiehlt Produkte nach Bedarf, Größe, Farbe oder Budget
landing.can2 = Prüft Bestand und Preis live, bevor er antwortet
landing.can3 = Beantwortet Fragen zu Lieferung und Rückgabe aus Ihren FAQs
landing.can4 = Gibt die Bestellung auf, sobald der Kunde bestätigt
landing.q3 = Wie lange dauert die Lieferung?
landing.a3 = Laut den FAQs dieses Shops werden Bestellungen innerhalb von zwei Werktagen versendet und kommen meist nach drei bis fünf Tagen an.
landing.q4 = Wo ist meine Bestellung 4821903357?
landing.a4 = Die Bestellung 4821903357 wurde versendet. Sie können sie jederzeit auf der Tracking-Seite verfolgen.

# ---- landing: showcase
landing.stores = Shops auf NAVA
landing.storesLead = Eine zufällige Auswahl aktiver Shops. Aktualisieren Sie, um weitere zu entdecken.
landing.shuffle = Andere anzeigen
landing.visit = Shop besuchen
landing.productsCount = {n} Produkte
landing.productsCount_one = {n} Produkt
landing.storesEmpty = Noch keine Shops. Eröffnen Sie den ersten.
landing.products = Frisch aus dem Regal
landing.productsLead = Zufällige Produkte aus den Shops, direkt aus der Datenbank.
landing.productsEmpty = Produkte erscheinen hier, sobald Shops welche hinzufügen.
landing.by = von {store}

# ---- landing: business types
landing.types = Für jede Art von Geschäft gemacht
landing.typesLead = Eine Plattform, {n} fertige Produktvorlagen.
landing.typesMore = +{n} weitere

# ---- landing: sellers and buyers
landing.sellers = Für Verkäufer
landing.sellersBody = Geben Sie jedem Besucher einen kundigen Verkäufer, ohne jemanden einzustellen.
landing.s1 = Shop in Minuten einrichten, ohne Entwickler
landing.s2 = Den Assistenten mit FAQs und Wissenseinträgen schulen
landing.s3 = Bestellungen, Gespräche und Bestandswarnungen an einem Ort sehen
landing.buyers = Für Käufer
landing.buyersBody = Fragen Sie so, wie Sie im Laden fragen würden, und erhalten Sie eine klare Antwort.
landing.y1 = Fragen zu Produkten, Größen und Preisen in Ihrer Sprache
landing.y2 = Als Gast bestellen und die Bestellung per Nummer verfolgen
landing.y3 = Rechnung als PDF herunterladen

# ---- landing: faq
landing.faq = Häufig gestellte Fragen
faq.q1 = Was ist NAVA?
faq.a1 = NAVA ist ein KI-Verkaufsassistent mit Schaufenster für Online-Shops. Kunden chatten mit dem Assistenten, füllen den Warenkorb und bestellen, während Verkäufer Produkte, Bestellungen und Gespräche in einem Bereich verwalten.
faq.q2 = Brauchen Kunden ein Konto?
faq.a2 = Nein. Käufer bestellen als Gast. Warenkorb und Bestellung sind an ein privates Sitzungs-Token gebunden, und die Bestellung lässt sich mit der 10-stelligen Nummer verfolgen.
faq.q3 = Kann der Assistent Preise ändern oder Bestand erfinden?
faq.a3 = Nein. Preise, Bestände und Bestellsummen liest die Anwendung immer aus der Datenbank. Das Sprachmodell formuliert nur den Antworttext.
faq.q4 = Welche Sprachen werden unterstützt?
faq.a4 = Die Oberfläche gibt es auf Persisch, Englisch, Spanisch, Deutsch und Französisch. Wählen Sie die Sprache über die Auswahl in Kopf- oder Fußzeile.
faq.q5 = Wie fange ich an?
faq.a5 = Erstellen Sie ein Verkäuferkonto, eröffnen Sie einen Shop, fügen Sie einige Produkte und FAQs hinzu und teilen Sie Ihren Shop-Link. Der Live-Demo-Shop zeigt, was Ihre Kunden sehen.
faq.q6 = Was passiert, wenn der KI-Anbieter nicht erreichbar ist?
faq.a6 = Der Assistent antwortet mit einer sicheren, allgemeinen Meldung und gibt keine Anbieterdetails preis. Schaufenster, Warenkorb und Kasse funktionieren auch ohne ihn.

# ---- landing: final call to action
landing.ctaTitle = Bereit, Ihren Shop für sich sprechen zu lassen?
landing.ctaBody = Shop erstellen, ein paar Produkte hinzufügen und den Link teilen. Das dauert nur Minuten.

# ---- footer
footer.tagline = Der KI-Verkaufsassistent für Online-Shops: von der ersten Frage bis zur gelieferten Bestellung.
footer.product = Produkt
footer.sellers = Für Verkäufer
footer.customers = Für Käufer
footer.language = Sprache
footer.types = Branchen
footer.rights = © {year} NAVA. Alle Rechte vorbehalten.
footer.top = Nach oben
footer.trust1.t = Sichere Kasse
footer.trust1.d = Idempotente Bestellungen, Zahlungen bereit für Gateways.
footer.trust2.t = Bestellverfolgung
footer.trust2.d = Jede Bestellung per 10-stelliger Nummer abrufen.
footer.trust3.t = PDF-Rechnungen
footer.trust3.d = Zu jeder Bestellung gibt es eine herunterladbare Rechnung.
footer.trust4.t = Belegte Antworten
footer.trust4.d = Preise und Bestände direkt aus der Datenbank.

# ---- auth
auth.loginTitle = Anmelden
auth.registerTitle = Verkäuferkonto erstellen
auth.email = E-Mail
auth.password = Passwort
auth.passwordHint = Mindestens 8 Zeichen.
auth.phone = Telefon
auth.phoneHint = Wird für den Bestätigungscode per SMS verwendet.
auth.loginSubmit = Anmelden
auth.registerSubmit = Konto erstellen
auth.forgot = Passwort vergessen?
auth.noAccount = Noch kein Konto?
auth.haveAccount = Sie haben bereits ein Konto?
auth.backToLogin = Zurück zur Anmeldung
auth.verifyTitle = Konto bestätigen
auth.verifyLead = Wir haben einen 8-stelligen Code an {email} gesendet.
auth.emailCode = E-Mail-Bestätigungscode
auth.phoneCode = Telefon-Bestätigungscode
auth.verifySubmit = Bestätigen und fortfahren
auth.unverified = Ihr Konto ist noch nicht bestätigt. Geben Sie den Code ein, den wir gesendet haben.
auth.verified = Ihr Konto ist bestätigt. Sie können sich jetzt anmelden.
auth.devHint = Entwicklungsmodus: Der Bestätigungscode steht im Server-Log.
auth.forgotTitle = Passwort zurücksetzen
auth.forgotLead = Geben Sie Ihre E-Mail-Adresse ein, wir senden Ihnen ein Zurücksetzungs-Token.
auth.forgotSubmit = Token senden
auth.forgotSent = Wenn diese E-Mail-Adresse registriert ist, wurde ein Zurücksetzungs-Token gesendet.
auth.haveToken = Ich habe bereits ein Token
auth.resetTitle = Neues Passwort wählen
auth.resetToken = Zurücksetzungs-Token
auth.newPassword = Neues Passwort
auth.resetSubmit = Passwort ändern
auth.resetDone = Ihr Passwort wurde geändert. Melden Sie sich mit dem neuen Passwort an.

# ---- forms
form.required = Dieses Feld ist erforderlich.
form.price = Geben Sie einen gültigen Preis ein.
form.stock = Der Bestand muss eine ganze Zahl sein, null oder mehr.
form.otp = Geben Sie den 8-stelligen Code ein.
form.tracking = Geben Sie die 10-stellige Sendungsnummer ein.

# ---- storefront
shop.search = Produkte suchen…
shop.inStockOnly = Nur lieferbar
shop.count = {n} Produkte
shop.count_one = {n} Produkt
shop.empty = Keine Produkte gefunden.
shop.add = In den Warenkorb
shop.added = „{name}“ wurde in den Warenkorb gelegt
shop.ask = Assistenten fragen
shop.askProduct = Erzähl mir etwas über {name}
shop.attributes = Details
shop.backToStore = Zurück zum Shop
shop.qty = Menge
shop.inStock = Auf Lager ({n})
shop.lowStock = Nur noch {n} übrig
shop.lowStock_one = Nur noch {n} übrig
shop.outOfStock = Nicht auf Lager
shop.productNotFound = Produkt nicht gefunden.
shop.storeNotFound = Shop nicht gefunden.
shop.poweredBy = Bereitgestellt von NAVA
shop.createYours = Eigenen Shop eröffnen

# ---- chat
chat.title = Einkaufsassistent
chat.open = Assistenten fragen
chat.placeholder = Frage eingeben…
chat.send = Senden
chat.typing = Der Assistent schreibt
chat.welcome = Hallo! Ich bin der Assistent von {store}. Fragen Sie mich nach Produkten, Preisen oder Bestand oder bestellen Sie gleich hier.
chat.s1 = Welche Produkte sind lieferbar?
chat.s2 = Was ist der günstigste Artikel?
chat.s3 = Lege das erste Produkt in meinen Warenkorb
chat.s4 = Wie kann ich meine Bestellung verfolgen?

# ---- cart and checkout
cart.title = Warenkorb
cart.open = Warenkorb öffnen ({n} Artikel)
cart.open_one = Warenkorb öffnen ({n} Artikel)
cart.empty = Ihr Warenkorb ist leer
cart.emptyHint = Legen Sie Produkte aus dem Shop hinein oder bitten Sie den Assistenten darum.
cart.total = Gesamt
cart.checkout = Zur Kasse
cart.clear = Warenkorb leeren
cart.dec = Menge von {name} verringern
cart.inc = Menge von {name} erhöhen
cart.remove = {name} entfernen
checkout.title = Kasse
checkout.name = Vollständiger Name
checkout.phone = Telefonnummer
checkout.email = E-Mail
checkout.address = Lieferadresse
checkout.submit = Bestellung aufgeben
checkout.back = Zurück zum Warenkorb
order.placed = Bestellung aufgegeben
order.number = Bestellnummer
order.tracking = Sendungsnummer
order.items = Bestellte Artikel
order.pay = Jetzt bezahlen
order.paid = Zahlung erhalten. Vielen Dank!
order.sandbox = Dies ist eine Testzahlung. Bestätigen Sie, um eine erfolgreiche Zahlung zu simulieren.
order.sandboxConfirm = Testzahlung bestätigen
order.invoice = Rechnung herunterladen (PDF)
order.trackLink = Diese Bestellung verfolgen
order.continue = Weiter einkaufen

# ---- order tracking and statuses
track.title = Bestellung verfolgen
track.lead = Geben Sie die 10-stellige Sendungsnummer ein, die Sie beim Bezahlen erhalten haben.
track.number = Sendungsnummer
track.submit = Verfolgen
track.store = Shop
track.placedAt = Aufgegeben
track.updatedAt = Letzte Aktualisierung
track.cancelled = Diese Bestellung wurde storniert.
status.pending = Offen
status.confirmed = Bestätigt
status.preparing = In Vorbereitung
status.shipped = Versendet
status.delivered = Geliefert
status.cancelled = Storniert
cs.idle = Stöbert
cs.awaiting_customer = Daten werden erfasst
cs.awaiting_confirmation = Wartet auf Bestätigung
cs.completed = Abgeschlossen

# ---- seller panel
s.overview = Übersicht
s.orders = Bestellungen
s.conversations = Gespräche
s.products = Produkte
s.knowledge = Wissen
s.activeStore = Aktiver Shop
s.viewStore = Shop ansehen
s.logout = Abmelden
s.needStore = Erstellen Sie zuerst einen Shop.
s.goOverview = Zur Übersicht
s.noStoreTitle = Sie haben noch keinen Shop
s.noStoreBody = Erstellen Sie Ihren ersten Shop, um mit dem Assistenten zu verkaufen.
s.storeName = Shop-Name
s.businessType = Branche
s.storeDesc = Beschreibung
s.logo = Logo
s.editStore = Shop bearbeiten
s.newStore = Neuer Shop
s.storeCreated = Shop erstellt.
s.publicLink = Öffentlicher Link
s.deleteStore = Shop löschen
s.deleteStoreNote = Beim Löschen eines Shops werden Produkte, FAQs und Wissenseinträge dauerhaft entfernt.
ov.orders = Bestellungen
ov.value = Bestellwert
ov.products = Aktive Produkte
ov.conversations = Gespräche
ov.attention = Erfordert Aufmerksamkeit
ov.allGood = Nichts erfordert Ihre Aufmerksamkeit.
ov.pendingOrders = Offene Bestellungen
ov.lowStock = Niedriger Bestand
ov.lowStockItem = Noch {n}
ov.recent = Letzte Gespräche
o.empty = Noch keine Bestellungen.
o.search = Suche nach Name, Telefon oder Sendungsnummer
o.all = Alle
o.id = Bestellung
o.customer = Kunde
o.total = Gesamt
o.status = Status
o.date = Datum
od.title = Bestellung {id}
od.next = Nächster Schritt
od.final = Diese Bestellung ist abgeschlossen.
od.moveTo = Auf „{status}“ setzen
od.cancelOrder = Bestellung stornieren
od.updated = Bestellung aktualisiert.
od.phone = Telefon
od.address = Adresse
od.invoice = Rechnungsnummer
od.date = Datum
od.item = Artikel
od.unit = Einzelpreis
od.qty = Menge
od.line = Zeilensumme
c.empty = Noch keine Gespräche.
c.guest = Gast {id}
c.noMessages = Keine Nachrichten
c.messages = {n} Nachrichten
c.messages_one = {n} Nachricht
c.order = Bestellung {id}
c.user = Kunde
c.assistant = Assistent
p.add = Produkt hinzufügen
p.edit = Produkt bearbeiten
p.created = Produkt erstellt.
p.updated = Produkt aktualisiert.
p.deleted = Produkt gelöscht.
p.empty = Noch keine Produkte.
p.emptyHint = Fügen Sie Ihr erstes Produkt hinzu, damit der Assistent es verkaufen kann.
p.name = Name
p.price = Preis
p.stock = Bestand
p.desc = Beschreibung
p.image = Bild
p.status = Status
p.reserved = {n} reserviert
p.typeFields = Details: {type}
k.lead = Der Assistent antwortet anhand dieser Einträge. Halten Sie sie korrekt und kurz.
k.tabKnowledge = Wissensdatenbank
k.tabFaqs = FAQs
k.add = Eintrag hinzufügen
k.editEntry = Eintrag bearbeiten
k.title = Titel
k.content = Inhalt
k.question = Frage
k.answer = Antwort
k.active = Aktiv (vom Assistenten genutzt)
k.emptyKnowledge = Noch keine Wissenseinträge.
k.emptyFaqs = Noch keine FAQs.
`)
