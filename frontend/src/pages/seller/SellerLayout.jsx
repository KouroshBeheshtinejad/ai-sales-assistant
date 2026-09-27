import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { Brand, LocaleToggle, SkipLink } from '../../components/Layout'
import { Button, Empty, ErrorNote, Field, Icon, Loading, Modal } from '../../components/ui'
import { useAuth } from '../../lib/auth'
import { useI18n } from '../../lib/i18n'
import { SellerProvider, useSeller } from './SellerContext'

const NAV = [
  ['/seller', 's.overview', true, 'layers'],
  ['/seller/orders', 's.orders', false, 'card'],
  ['/seller/conversations', 's.conversations', false, 'chat'],
  ['/seller/products', 's.products', false, 'box'],
  ['/seller/knowledge', 's.knowledge', false, 'doc'],
]

export function NeedStore() {
  const { t } = useI18n()
  return <Empty title={t('s.needStore')} action={<Link className="btn btn-primary" to="/seller">{t('s.goOverview')}</Link>} />
}

export function PageHead({ title, actions }) {
  return <div className="page-head"><h1>{title}</h1>{actions && <div className="row">{actions}</div>}</div>
}

// The store switcher, shared by the desktop sidebar and the mobile "more" sheet.
// `variant="bare"` drops the visible label (an aria-label is enough once it sits in a
// compact bar) so it doesn't stack label-over-control in a horizontal layout.
function StoreSwitcher({ stores, store, select, variant }) {
  const { t } = useI18n()
  if (!stores.length) return null
  const control = (
    <select value={store?.id ?? ''} onChange={(e) => select(e.target.value)} aria-label={t('s.activeStore')}>
      {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
    </select>
  )
  if (variant === 'bare') return control
  return <Field label={t('s.activeStore')}>{control}</Field>
}

// Sign out, the public store link and the language switcher: identical content in the
// desktop sidebar footer and the mobile sheet, just styled differently by their parent.
function AccountActions({ store, signOut, onNavigate }) {
  const { t } = useI18n()
  return (
    <>
      <Link to="/seller/account" onClick={onNavigate}><Icon name="user" size={18} />{t('nav.account')}</Link>
      {store && <Link to={`/store/${store.id}`} target="_blank" rel="noreferrer" onClick={onNavigate}><Icon name="eye" size={18} />{t('s.viewStore')}</Link>}
      <LocaleToggle />
      <Button variant="ghost" size="sm" onClick={signOut}><Icon name="logout" size={18} />{t('s.logout')}</Button>
    </>
  )
}

// Fixed bottom tab bar for the 5 primary sections. Icon + short label, thumb-reachable,
// safe-area aware; this replaces the old horizontally-scrolling nav row on small screens.
function TabBar() {
  const { t } = useI18n()
  return (
    <nav className="seller-tabbar" aria-label={t('s.overview')}>
      {NAV.map(([to, label, end, icon]) => (
        <NavLink key={to} to={to} end={end} className="seller-tab">
          <Icon name={icon} size={22} />
          <span>{t(label)}</span>
        </NavLink>
      ))}
    </nav>
  )
}

// Compact top bar shown only on mobile: brand, the active store's name, and a "more"
// button that opens everything the desktop sidebar keeps visible (store switcher,
// view-store link, language, sign out) in an accessible modal sheet.
function MobileTopBar({ stores, store, select, signOut }) {
  const { t } = useI18n()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  useEffect(() => { setOpen(false) }, [pathname]) // navigating from the tab bar should close the sheet
  return (
    <div className="seller-topbar">
      <Brand to="/seller" />
      {store && <span className="seller-topbar-store">{store.name}</span>}
      <button type="button" className="menu-btn" aria-haspopup="dialog" onClick={() => setOpen(true)} aria-label={t('nav.openMenu')}>
        <Icon name="menu" />
      </button>
      {open && (
        <Modal title={t('nav.menu')} onClose={() => setOpen(false)}>
          <div className="stack seller-sheet">
            <StoreSwitcher stores={stores} store={store} select={select} />
            <AccountActions store={store} signOut={signOut} onNavigate={() => setOpen(false)} />
          </div>
        </Modal>
      )}
    </div>
  )
}

function Shell() {
  const { t } = useI18n()
  const { signOut } = useAuth()
  const { stores, store, select, loading, error, reloadStores } = useSeller()

  return (
    <>
      <SkipLink />
      <div className="seller">
        <aside className="seller-nav">
          <Brand to="/seller" />
          <StoreSwitcher stores={stores} store={store} select={select} />
          <nav aria-label="Seller">
            {NAV.map(([to, label, end, icon]) => (
              <NavLink key={to} to={to} end={end}><Icon name={icon} size={18} />{t(label)}</NavLink>
            ))}
          </nav>
          <div className="seller-foot">
            <AccountActions store={store} signOut={signOut} />
          </div>
        </aside>

        <MobileTopBar stores={stores} store={store} select={select} signOut={signOut} />

        <main id="main" className="seller-main">
          {loading ? <Loading /> : error ? <ErrorNote error={error} onRetry={reloadStores} /> : <Outlet />}
        </main>

        <TabBar />
      </div>
    </>
  )
}

export default function SellerLayout() {
  return <SellerProvider><Shell /></SellerProvider>
}
