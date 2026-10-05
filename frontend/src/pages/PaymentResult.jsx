import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button, Field, Loading, StatusBadge } from '../components/ui'
import { api } from '../lib/api'
import { getGuest } from '../lib/guest'
import { LOCALES, useI18n, getBrowserTimezone } from '../lib/i18n'
import { downloadBlob } from '../lib/util'

export default function PaymentResult() {
  const { t, id, money, err } = useI18n()
  const [params] = useSearchParams()
  const [order, setOrder] = useState(null)
  const [error, setError] = useState('')
  const [locale, setLocale] = useState(LOCALES[0].code)
  const [busy, setBusy] = useState(false)
  const storeId = params.get('store_id')
  const orderId = params.get('order_id')

  useEffect(() => {
    if (params.get('payment') !== 'success' || !storeId || !orderId) return
    api.guestOrder(storeId, orderId, getGuest(storeId)).then(setOrder).catch((cause) => setError(err(cause)))
  }, [storeId, orderId, params, err])

  const invoice = async () => {
    setBusy(true)
    try {
      const timezone = getBrowserTimezone()
      downloadBlob(await api.guestInvoice(storeId, orderId, getGuest(storeId), locale, timezone), `${order.invoice_number}-${locale}.pdf`)
    } catch (cause) {
      setError(err(cause))
    } finally {
      setBusy(false)
    }
  }

  if (params.get('payment') !== 'success') {
    return <main className="wrap page-narrow"><h1>{t('payment.returnFailed')}</h1><Link className="btn" to="/">{t('notfound.home')}</Link></main>
  }
  if (error) return <main className="wrap page-narrow"><p className="notice notice-danger">{error}</p><Link className="btn" to="/">{t('notfound.home')}</Link></main>
  if (!order) return <main className="wrap page-narrow"><Loading /></main>

  return (
    <main className="wrap page-narrow">
      <h1>{t('order.paid')}</h1>
      <dl className="facts">
        <div><dt>{t('order.number')}</dt><dd>{id(order.id)}</dd></div>
        <div><dt>{t('order.tracking')}</dt><dd dir="ltr">{order.tracking_number}</dd></div>
        <div><dt>{t('o.status')}</dt><dd><StatusBadge status={order.status} /></dd></div>
        <div><dt>{t('cart.total')}</dt><dd>{money(order.total_amount, order.currency)}</dd></div>
      </dl>
      <Field label={t('order.invoiceLanguage')}>
        <select value={locale} onChange={(event) => setLocale(event.target.value)}>
          {LOCALES.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}
        </select>
      </Field>
      <Button busy={busy} onClick={invoice}>{t('order.invoice')}</Button>
      <Link className="btn btn-ghost" to={`/track?number=${order.tracking_number}`}>{t('order.trackLink')}</Link>
    </main>
  )
}