import { Component } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useI18n } from '../lib/i18n'
import { Button } from './ui'

export const DEMO_STORE_ID = import.meta.env.VITE_DEMO_STORE_ID || '1'

export function Brand({ to = '/' }) {
  const { t } = useI18n()
  return (
    <Link to={to} className="brand">
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

export function LocaleToggle() {
  const { locale, setLocale, t } = useI18n()
  return <button type="button" className="locale" onClick={() => setLocale(locale === 'fa' ? 'en' : 'fa')} aria-label={t('nav.langName')} lang={locale === 'fa' ? 'en' : 'fa'}>{t('nav.lang')}</button>
}

export function SkipLink() {
  const { t } = useI18n()
  return <a className="skip" href="#main">{t('a11y.skip')}</a>
}

export function PublicLayout() {
  const { t } = useI18n()
  const { isAuthed } = useAuth()
  return (
    <>
      <SkipLink />
      <header className="topbar">
        <div className="wrap topbar-in">
          <Brand />
          <nav className="topnav" aria-label="Main">
            <Link to={`/store/${DEMO_STORE_ID}`} className="hide-sm">{t('nav.demo')}</Link>
            <Link to="/track">{t('nav.track')}</Link>
            {isAuthed ? (
              <Link className="btn btn-primary btn-sm" to="/seller">{t('nav.panel')}</Link>
            ) : (
              <>
                <Link to="/login">{t('nav.login')}</Link>
                <Link className="btn btn-primary btn-sm hide-sm" to="/register">{t('nav.register')}</Link>
              </>
            )}
            <LocaleToggle />
          </nav>
        </div>
      </header>
      <main id="main"><Outlet /></main>
      <footer className="footer"><div className="wrap">{t('landing.footer')}</div></footer>
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
