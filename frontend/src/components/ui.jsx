import { Children, cloneElement, createContext, useCallback, useContext, useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useI18n } from '../lib/i18n'
import { STATUS_FLOW } from '../lib/orders'
import { cx, uuid } from '../lib/util'

export function Spinner() {
  return <span className="spinner" aria-hidden="true" />
}

export function Button({ variant = 'default', size, busy, disabled, className, type = 'button', children, ...rest }) {
  return (
    <button type={type} className={cx('btn', `btn-${variant}`, size && `btn-${size}`, className)} disabled={busy || disabled} aria-busy={busy || undefined} {...rest}>
      {busy && <Spinner />}
      {children}
    </button>
  )
}

// Label + a single control (input / select / textarea); wires id, hint and error for screen readers.
export function Field({ label, hint, error, className, children }) {
  const id = useId()
  const describedBy = error || hint ? `${id}-d` : undefined
  const control = cloneElement(Children.only(children), { id, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined })
  return (
    <div className={cx('field', className)}>
      <label htmlFor={id}>{label}</label>
      {control}
      {(error || hint) && <p id={describedBy} className={error ? 'field-error' : 'field-hint'}>{error || hint}</p>}
    </div>
  )
}

export function Check({ label, ...props }) {
  return <label className="check"><input type="checkbox" {...props} /><span>{label}</span></label>
}

export function Switch({ checked, onChange, label, disabled }) {
  return <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled} className="switch" onClick={() => onChange(!checked)}><span /></button>
}

export function Badge({ tone = 'neutral', children }) {
  return <span className={cx('badge', `badge-${tone}`)}>{children}</span>
}

const STATUS_TONE = { pending: 'warn', confirmed: 'info', preparing: 'info', shipped: 'info', delivered: 'ok', cancelled: 'danger' }
export function StatusBadge({ status }) {
  const { t } = useI18n()
  return <Badge tone={STATUS_TONE[status] || 'neutral'}>{t(`status.${status}`)}</Badge>
}

export function Timeline({ status }) {
  const { t } = useI18n()
  if (status === 'cancelled') return <p className="notice notice-danger">{t('track.cancelled')}</p>
  const current = STATUS_FLOW.indexOf(status)
  return (
    <ol className="timeline">
      {STATUS_FLOW.map((step, index) => (
        <li key={step} className={cx(index < current && 'done', index === current && 'current')} aria-current={index === current ? 'step' : undefined}>
          <span className="dot" aria-hidden="true" />
          <span>{t(`status.${step}`)}</span>
        </li>
      ))}
    </ol>
  )
}

export function Loading() {
  const { t } = useI18n()
  return <div className="state" role="status"><Spinner />{t('loading')}</div>
}

export function ErrorNote({ error, onRetry }) {
  const { t, err } = useI18n()
  return (
    <div className="state state-error" role="alert">
      <p>{err(error)}</p>
      {onRetry && <Button size="sm" onClick={onRetry}>{t('retry')}</Button>}
    </div>
  )
}

export function Empty({ title, hint, action }) {
  return <div className="state"><p className="state-title">{title}</p>{hint && <p>{hint}</p>}{action}</div>
}

// Renders loading / error / content for a useAsync() result.
export function Async({ state, children }) {
  if (state.loading && !state.data) return <Loading />
  if (state.error) return <ErrorNote error={state.error} onRetry={state.reload} />
  return children(state.data)
}

export function ConfirmButton({ onConfirm, children, busy, variant = 'ghost', size = 'sm', ...rest }) {
  const { t } = useI18n()
  const [asking, setAsking] = useState(false)
  if (!asking) return <Button variant={variant} size={size} onClick={() => setAsking(true)} {...rest}>{children}</Button>
  return (
    <span className="confirm" role="group" aria-label={t('confirm.sure')}>
      <span>{t('confirm.sure')}</span>
      <Button variant="danger" size="sm" busy={busy} onClick={async () => { await onConfirm(); setAsking(false) }}>{t('yes')}</Button>
      <Button size="sm" onClick={() => setAsking(false)}>{t('no')}</Button>
    </span>
  )
}

export function Modal({ title, onClose, children, variant = 'dialog' }) {
  const { t } = useI18n()
  const panel = useRef(null)
  const closeRef = useRef(onClose)
  const titleId = useId()
  closeRef.current = onClose

  useEffect(() => {
    const previous = document.activeElement
    const focusable = () => [...panel.current.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select,textarea,[tabindex]:not([tabindex="-1"])')]
    ;(panel.current.querySelector('[data-autofocus]') || focusable()[0])?.focus()
    const onKey = (event) => {
      if (event.key === 'Escape') closeRef.current()
      if (event.key !== 'Tab') return
      const items = focusable()
      if (!items.length) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    document.body.classList.add('no-scroll')
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.classList.remove('no-scroll')
      previous?.focus?.()
    }
  }, [])

  return createPortal(
    <div className={cx('overlay', variant)} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <div className="panel" role="dialog" aria-modal="true" aria-labelledby={titleId} ref={panel}>
        <div className="panel-head">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t('close')}><Icon name="close" /></button>
        </div>
        <div className="panel-body">{children}</div>
      </div>
    </div>,
    document.body,
  )
}

const ToastContext = createContext(() => {})
export const useToast = () => useContext(ToastContext)

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback((message, tone = 'ok') => {
    const id = uuid()
    setItems((list) => [...list, { id, message, tone }])
    setTimeout(() => setItems((list) => list.filter((item) => item.id !== id)), 4500)
  }, [])
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((item) => <div key={item.id} className={cx('toast', `toast-${item.tone}`)}>{item.message}</div>)}
      </div>
    </ToastContext.Provider>
  )
}

const PALETTES = [['#0d8a85', '#d9f0ee'], ['#27408b', '#e1e7f6'], ['#b7791f', '#fdf0d0'], ['#a8443a', '#f7e0dc'], ['#3b6b4f', '#dcebe1'], ['#6b4a8c', '#e9dff2']]
const hash = (text) => [...String(text)].reduce((h, ch) => (h * 31 + ch.codePointAt(0)) >>> 0, 7)

// Products have no photos in the data model: each gets a stable tile, derived from its name.
export function Swatch({ seed, label, className }) {
  const h = hash(seed)
  const [ink, ground] = PALETTES[h % PALETTES.length]
  const motif = Math.floor(h / 7) % 3
  return (
    <div className={cx('swatch', className)} style={{ background: ground, color: ink }} aria-hidden="true">
      <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" fill="none" stroke="currentColor" strokeWidth="1.4" opacity=".4">
        {motif === 0 && <><rect x="22" y="22" width="56" height="56" /><rect x="22" y="22" width="56" height="56" transform="rotate(45 50 50)" /><rect x="6" y="6" width="88" height="88" /></>}
        {motif === 1 && [46, 35, 24, 13].map((r) => <circle key={r} cx="50" cy="50" r={r} />)}
        {motif === 2 && <><path d="M50 4 96 50 50 96 4 50Z" /><path d="M50 22 78 50 50 78 22 50Z" /><path d="M50 40 60 50 50 60 40 50Z" /></>}
      </svg>
      <span>{String(label || '').trim().charAt(0)}</span>
    </div>
  )
}

const ICONS = {
  close: 'M6 6l12 12M18 6L6 18',
  cart: 'M4 5h2l2 10h9l2-7H7M10 20h.01M17 20h.01',
  chat: 'M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v6a2.5 2.5 0 0 1-2.5 2.5H12l-4 4v-4H7.5A2.5 2.5 0 0 1 5 12.5z',
  plus: 'M12 5v14M5 12h14',
  minus: 'M5 12h14',
  send: 'M4 12 20 4l-4 16-4-6z',
  trash: 'M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z',
  logout: 'M10 5H6v14h4M14 8l4 4-4 4M18 12H9',
  menu: 'M4 6h16M4 12h16M4 18h16',
  globe: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c2.5 2.5 3.8 5.5 3.8 9S14.5 18.5 12 21c-2.5-2.5-3.8-5.5-3.8-9S9.5 5.5 12 3z',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  chevron: 'M6 9l6 6 6-6',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  up: 'M12 19V5M6 11l6-6 6 6',
  shield: 'M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6zM9 12l2 2 4-4',
  store: 'M3 9l1.5-5h15L21 9M3 9c0 1.7 1.3 3 3 3s3-1.3 3-3c0 1.7 1.3 3 3 3s3-1.3 3-3c0 1.7 1.3 3 3 3s3-1.3 3-3M5 12v8h14v-8M10 20v-4h4v4',
  box: 'M12 3l8 4.5v9L12 21l-8-4.5v-9zM4 7.5l8 4.5 8-4.5M12 12v9',
  doc: 'M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6',
  sparkle: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z',
  bolt: 'M13 3L5 13h6l-1 8 8-10h-6z',
  lock: 'M6 11h12v9H6zM8 11V8a4 4 0 0 1 8 0v3',
  users: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20c.5-3.5 3.2-5.5 6.5-5.5s6 2 6.5 5.5M16 4.5a3.5 3.5 0 0 1 0 6.5M18 14.8c2 .7 3.2 2.5 3.5 5',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4',
  layers: 'M12 3l9 5-9 5-9-5zM3 12.5l9 5 9-5M3 17l9 5 9-5',
  database: 'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6',
  shuffle: 'M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5',
  card: 'M3 6h18v12H3zM3 10h18M7 15h3',
  tag: 'M3 12V4h8l10 10-8 8zM7.5 8.5h.01',
  code: 'M8 7l-5 5 5 5M16 7l5 5-5 5',
  truck: 'M2 6h11v10H2zM13 9h4l3 3v4h-7M6 19a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM17 19a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z',
}
export function Icon({ name, size = 20, className }) {
  return <svg className={cx('icon', className)} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={ICONS[name]} /></svg>
}