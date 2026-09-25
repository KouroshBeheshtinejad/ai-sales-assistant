import { Component, useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useI18n } from '../lib/i18n'
import { cx } from '../lib/util'
import { Button, Icon } from './ui'

export const DEMO_STORE_ID = import.meta.env.VITE_DEMO_STORE_ID || '1'

export function Brand({ to = '/' }) {
  const { t } = useI18n()
  return (
    <Link to={to} className="brand" aria-label={t('nav.home')}>
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="9" fill="var(--teal)" />
        <rect x="8" y="8" width="16" height="12" rx="4" fill="#fff" />
        <path d="M12 20v4l4-4z" fill="#fff" />
        <circle cx="13" cy="14" r="1.3" fill="var(--teal)" /><circle cx="16" cy="14" r="1.3" fill="var(--teal)" /><circle cx="19" cy="14" r="1.3" fill="var(--teal)" />
      </svg>
      <span>{t('brand')}</span>
    </Link>
  )
}

// A native <select>: the same control on desktop and Android, keyboard and screen-reader
// friendly, and the platform picker opens on touch devices.
export function LocaleToggle({ className }) {
  const { locale, setLocale, locales, t } = useI18n()
  return (
    <label className={cx('lang', className)}>
      <Icon name="globe" size={18} />
      <select value={locale} onChange={(event) => setLocale(event.target.value)} aria-label={t('nav.langName')}>
        {locales.map((item) => <option key={item.code} value={item.code} lang={item.code}>{item.name}</option>)}
      </select>
      <Icon name="chevron" size={14} className="lang-caret" />
    </label>
  )
}

export function SkipLink() {
  const { t } = useI18n()
  return <a className="skip" href="#main">{t('a11y.skip')}</a>
}

// Anchors on the landing page (/#features) need an explicit scroll: the router
// changes the URL but never moves the page. Any other navigation starts at the top.
function useScrollOnNavigate() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const target = hash ? document.getElementById(decodeURIComponent(hash.slice(1))) : null
      if (target) target.scrollIntoView({ block: 'start' })
      else window.scrollTo(0, 0)
    })
    return () => cancelAnimationFrame(frame)
  }, [pathname, hash])
}

const SECTION_LINKS = [
  ['nav.features', { pathname: '/', hash: '#features' }],
  ['nav.how', { pathname: '/', hash: '#how' }],
  ['nav.stores', { pathname: '/', hash: '#stores' }],
  ['nav.faq', { pathname: '/', hash: '#faq' }],
]

function AccountLinks({ onNavigate }) {
  const { t } = useI18n()
  const { isAuthed } = useAuth()
  return isAuthed ? (
    <Link className="btn btn-primary btn-sm" to="/seller" onClick={onNavigate}>{t('nav.panel')}</Link>
  ) : (
    <>
      <Link className="btn btn-ghost btn-sm" to="/login" onClick={onNavigate}>{t('nav.login')}</Link>
      <Link className="btn btn-primary btn-sm" to="/register" onClick={onNavigate}>{t('nav.register')}</Link>
    </>
  )
}

export function SiteHeader() {
  const { t } = useI18n()
  const { pathname, hash } = useLocation()
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  useEffect(() => { setOpen(false) }, [pathname, hash])
  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => { if (event.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <header className="topbar">
      <div className="wrap topbar-in">
        <Brand />
        <nav id="site-nav" className={cx('sitenav', open && 'is-open')} aria-label={t('nav.main')}>
          <ul className="sitenav-links">
            {SECTION_LINKS.map(([label, to]) => <li key={label}><Link to={to} onClick={close}>{t(label)}</Link></li>)}
            <li><Link to={`/store/${DEMO_STORE_ID}`} onClick={close}>{t('nav.demo')}</Link></li>
            <li><Link to="/track" onClick={close}>{t('nav.track')}</Link></li>
          </ul>
          <div className="sitenav-actions"><AccountLinks onNavigate={close} /></div>
        </nav>
        <div className="topbar-end">
          <LocaleToggle />
          <div className="topbar-actions"><AccountLinks /></div>
          <button type="button" className="menu-btn" aria-expanded={open} aria-controls="site-nav" aria-label={open ? t('nav.closeMenu') : t('nav.openMenu')} onClick={() => setOpen(!open)}>
            <Icon name={open ? 'close' : 'menu'} />
          </button>
        </div>
      </div>
    </header>
  )
}

const TRUST = [['shield', 'footer.trust1'], ['search', 'footer.trust2'], ['doc', 'footer.trust3'], ['database', 'footer.trust4']]

function FooterColumn({ title, children }) {
  return (
    <nav className="footer-col" aria-label={title}>
      <h2 className="footer-title">{title}</h2>
      <ul>{children}</ul>
    </nav>
  )
}

export function SiteFooter() {
  const { t, locale, setLocale, locales, meta } = useI18n()
  const { isAuthed } = useAuth()
  // Persian visitors see the Solar Hijri year, everyone else the Gregorian one.
  const year = new Intl.DateTimeFormat(meta.tag, { year: 'numeric' }).format(new Date())

  return (
    <footer className="footer">
      <div className="wrap">
        <ul className="trust">
          {TRUST.map(([icon, key]) => (
            <li key={key}>
              <span className="trust-icon"><Icon name={icon} size={22} /></span>
              <div><strong>{t(`${key}.t`)}</strong><span>{t(`${key}.d`)}</span></div>
            </li>
          ))}
        </ul>

        <div className="footer-grid">
          <div className="footer-brand">
            <Brand />
            <p>{t('footer.tagline')}</p>
          </div>
          <FooterColumn title={t('footer.product')}>
            <li><Link to={{ pathname: '/', hash: '#features' }}>{t('nav.features')}</Link></li>
            <li><Link to={{ pathname: '/', hash: '#how' }}>{t('nav.how')}</Link></li>
            <li><Link to={{ pathname: '/', hash: '#types' }}>{t('footer.types')}</Link></li>
            <li><Link to={{ pathname: '/', hash: '#faq' }}>{t('nav.faq')}</Link></li>
          </FooterColumn>
          <FooterColumn title={t('footer.sellers')}>
            {isAuthed
              ? <li><Link to="/seller">{t('nav.panel')}</Link></li>
              : <><li><Link to="/register">{t('nav.register')}</Link></li><li><Link to="/login">{t('nav.login')}</Link></li></>}
            <li><Link to={{ pathname: '/', hash: '#stores' }}>{t('nav.stores')}</Link></li>
          </FooterColumn>
          <FooterColumn title={t('footer.customers')}>
            <li><Link to={`/store/${DEMO_STORE_ID}`}>{t('nav.demo')}</Link></li>
            <li><Link to="/track">{t('nav.track')}</Link></li>
          </FooterColumn>
          <div className="footer-col">
            <h2 className="footer-title">{t('footer.language')}</h2>
            <ul className="footer-langs">
              {locales.map((item) => (
                <li key={item.code}>
                  <button type="button" lang={item.code} aria-pressed={item.code === locale} className={cx('link-btn', item.code === locale && 'on')} onClick={() => setLocale(item.code)}>{item.name}</button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <p>{t('footer.rights', { year })}</p>
          <button type="button" className="link-btn" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}><Icon name="up" size={16} />{t('footer.top')}</button>
        </div>
      </div>
    </footer>
  )
}

// Compact footer for the storefront: the shop stays in front, NAVA stays discreet.
export function StoreFooter() {
  const { t } = useI18n()
  return (
    <footer className="store-footer">
      <div className="wrap row between">
        <span className="muted">{t('shop.poweredBy')}</span>
        <div className="row">
          <Link to="/track">{t('nav.track')}</Link>
          <Link to="/register">{t('shop.createYours')}</Link>
        </div>
      </div>
    </footer>
  )
}

export function PublicLayout() {
  useScrollOnNavigate()
  return (
    <>
      <SkipLink />
      <SiteHeader />
      <main id="main"><Outlet /></main>
      <SiteFooter />
    </>
  )
}

export function NotFound() {
  const { t } = useI18n()
  return (
    <div className="wrap page-narrow center">
      <h1>{t('notfound.title')}</h1>
      <Link className="btn btn-primary" to="/">{t('notfound.home')}</Link>
    </div>
  )
}

class Boundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(error) { console.error(error) }
  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="wrap page-narrow center" role="alert">
        <h1>{this.props.title}</h1>
        <Button variant="primary" onClick={() => location.reload()}>{this.props.retry}</Button>
      </div>
    )
  }
}

export function ErrorBoundary({ children }) {
  const { t } = useI18n()
  return <Boundary title={t('crash.title')} retry={t('retry')}>{children}</Boundary>
}