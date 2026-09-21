import { useState } from 'react'
import { trackOrder } from './api'

export function TrackOrder({ t }) {
  const [trackingNumber, setTrackingNumber] = useState('')
  const [order, setOrder] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async event => {
    event.preventDefault()
    setBusy(true)
    setError('')
    setOrder(null)
    try {
      setOrder(await trackOrder(trackingNumber))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return <main className="container section"><div className="card auth-card"><span className="eyebrow">NAVA</span><h1>{t.locale === 'fa' ? 'رهگیری سفارش' : 'Track your order'}</h1><form className="field" onSubmit={submit}><label htmlFor="tracking-number">{t.locale === 'fa' ? 'شماره رهگیری ۱۰ رقمی' : '10-digit tracking number'}</label><input id="tracking-number" inputMode="numeric" pattern="[0-9]{10}" maxLength="10" required value={trackingNumber} onChange={event => setTrackingNumber(event.target.value.replace(/\D/g, ''))}/><button className="btn btn-primary" disabled={busy}>{busy ? '...' : t.locale === 'fa' ? 'جستجو' : 'Find order'}</button></form>{error && <p role="alert" className="auth-error">{error}</p>}{order && <section className="card" style={{ marginTop: 24 }}><p className="muted">{order.store_name}</p><h2>#{order.tracking_number}</h2><p><strong>{t.status}:</strong> <span className="badge">{order.status}</span></p></section>}</div></main>
}