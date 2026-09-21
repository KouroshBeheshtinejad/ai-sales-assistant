import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button, Field, StatusBadge, Timeline } from '../components/ui'
import { api } from '../lib/api'
import { useSeo } from '../lib/hooks'
import { useI18n } from '../lib/i18n'
import { parseDate, toLatinDigits } from '../lib/util'

export default function Track() {
  const { t, id, date, err } = useI18n()
  const [params, setParams] = useSearchParams()
  const [number, setNumber] = useState(toLatinDigits(params.get('number') || ''))
  const [order, setOrder] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useSeo({ title: `${t('track.title')} | NAVA` })

  const lookup = async (value) => {
    if (!/^\d{10}$/.test(value)) { setError(t('form.tracking')); setOrder(null); return }
    setBusy(true)
    setError('')
    try { setOrder(await api.track(value)) } catch (e) { setOrder(null); setError(err(e)) } finally { setBusy(false) }
  }

  // Deep link from the checkout screen: /track?number=1234567890
  useEffect(() => {
    const initial = toLatinDigits(params.get('number') || '')
    if (initial) lookup(initial)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const submit = (event) => {
    event.preventDefault()
    setParams({ number })
    lookup(number)
  }

  return (
    <div className="wrap page-narrow">
      <h1>{t('track.title')}</h1>
      <p className="muted">{t('track.lead')}</p>
      <form className="row form-row" onSubmit={submit}>
        <Field label={t('track.number')}>
          <input inputMode="numeric" maxLength={10} dir="ltr" className="otp" value={number} onChange={(e) => setNumber(toLatinDigits(e.target.value).replace(/\D/g, ''))} />
        </Field>
        <Button type="submit" variant="primary" busy={busy}>{t('track.submit')}</Button>
      </form>
      {error && <p className="notice notice-danger" role="alert">{error}</p>}

      {order && (
        <section className="card stack" aria-live="polite">
          <div className="row between">
            <h2 className="h3">{id(order.tracking_number)}</h2>
            <StatusBadge status={order.status} />
          </div>
          <Timeline status={order.status} />
          <dl className="facts">
            <div><dt>{t('track.store')}</dt><dd><Link to={`/store/${order.store_id}`}>{order.store_name}</Link></dd></div>
            <div><dt>{t('track.placedAt')}</dt><dd>{date(parseDate(order.created_at))}</dd></div>
            <div><dt>{t('track.updatedAt')}</dt><dd>{date(parseDate(order.updated_at))}</dd></div>
          </dl>
        </section>
      )}
    </div>
  )
}
