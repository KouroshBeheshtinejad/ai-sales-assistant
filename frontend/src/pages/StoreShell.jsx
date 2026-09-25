import { useCallback, useState } from 'react'
import { Link, Outlet, useParams } from 'react-router-dom'
import CartDrawer from '../components/CartDrawer'
import ChatDock from '../components/ChatDock'
import { Brand, LocaleToggle, SkipLink, StoreFooter } from '../components/Layout'
import { ErrorNote, Icon, Loading } from '../components/ui'
import { useSeo } from '../lib/hooks'
import { useI18n } from '../lib/i18n'
import { useShop } from '../lib/useShop'

// Owns everything that must survive navigation inside one store:
// catalog, guest cart, cart drawer and the assistant.
export default function StoreShell() {
  const { id } = useParams()
  const { t, num } = useI18n()
  const shop = useShop(id)
  const [cartOpen, setCartOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const store = shop.catalog?.store
  const clearDraft = useCallback(() => setDraft(''), [])

  useSeo({ title: store ? `${store.name} | NAVA` : 'NAVA | AI commerce', description: store?.description || undefined })

  if (shop.error) {
    return (
      <div className="wrap page-narrow center">
        {shop.error.status === 404 ? <h1>{t('shop.storeNotFound')}</h1> : <ErrorNote error={shop.error} onRetry={shop.reloadCatalog} />}
        <Link className="btn btn-primary" to="/">{t('notfound.home')}</Link>
      </div>
    )
  }

  const ask = (text) => { setDraft(text); setChatOpen(true) }

  return (
    <>
      <SkipLink />
      <header className="topbar">
        <div className="wrap topbar-in">
          <Brand />
          {store && <Link className="store-crumb" to={`/store/${store.id}`}>{store.name}</Link>}
          <nav className="topnav" aria-label={t('nav.main')}>
            <Link to="/track" className="hide-sm">{t('nav.track')}</Link>
            <button type="button" className="btn btn-sm cart-btn" onClick={() => setCartOpen(true)} aria-label={t('cart.open', { n: shop.cartCount })}>
              <Icon name="cart" />
              {shop.cartCount > 0 && <span className="count" aria-hidden="true">{num(shop.cartCount)}</span>}
            </button>
            <LocaleToggle />
          </nav>
        </div>
      </header>

      <div className="wrap shop-grid">
        <main id="main">{shop.catalog ? <Outlet context={{ shop, ask }} /> : <Loading />}</main>
        <ChatDock key={id} shop={shop} storeName={store?.name} open={chatOpen} onClose={() => setChatOpen(false)} draft={draft} onDraftUsed={clearDraft} />
      </div>

      <StoreFooter />
      <button type="button" className="btn btn-primary chat-fab" onClick={() => setChatOpen(true)}><Icon name="chat" />{t('chat.open')}</button>
      {cartOpen && <CartDrawer shop={shop} onClose={() => setCartOpen(false)} />}
    </>
  )
}
