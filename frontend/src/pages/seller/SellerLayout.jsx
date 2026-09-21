import { Link, NavLink, Outlet } from 'react-router-dom'
import { Brand, LocaleToggle, SkipLink } from '../../components/Layout'
import { Button, Empty, ErrorNote, Field, Icon, Loading } from '../../components/ui'
import { useAuth } from '../../lib/auth'
import { useI18n } from '../../lib/i18n'
import { SellerProvider, useSeller } from './SellerContext'

const NAV = [
  ['/seller', 's.overview', true],
  ['/seller/orders', 's.orders'],
  ['/seller/conversations', 's.conversations'],
  ['/seller/products', 's.products'],
  ['/seller/knowledge', 's.knowledge'],
]

export function NeedStore() {
  const { t } = useI18n()
  return <Empty title={t('s.needStore')} action={<Link className="btn btn-primary" to="/seller">{t('s.goOverview')}</Link>} />
}

export function PageHead({ title, actions }) {
  return <div className="page-head"><h1>{title}</h1>{actions && <div className="row">{actions}</div>}</div>
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
          {stores.length > 0 && (
            <Field label={t('s.activeStore')}>
              <select value={store?.id ?? ''} onChange={(e) => select(e.target.value)}>
                {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </Field>
          )}
          <nav aria-label="Seller">
            {NAV.map(([to, label, end]) => <NavLink key={to} to={to} end={end}>{t(label)}</NavLink>)}
          </nav>
          <div className="seller-foot">
            {store && <Link to={`/store/${store.id}`} target="_blank" rel="noreferrer"><Icon name="eye" size={18} />{t('s.viewStore')}</Link>}
            <LocaleToggle />
            <Button variant="ghost" size="sm" onClick={signOut}><Icon name="logout" size={18} />{t('s.logout')}</Button>
          </div>
        </aside>
        <main id="main" className="seller-main">
          {loading ? <Loading /> : error ? <ErrorNote error={error} onRetry={reloadStores} /> : <Outlet />}
        </main>
      </div>
    </>
  )
}

export default function SellerLayout() {
  return <SellerProvider><Shell /></SellerProvider>
}
