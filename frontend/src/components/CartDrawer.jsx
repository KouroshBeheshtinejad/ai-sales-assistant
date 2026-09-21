import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { copyText, downloadBlob, safeStorage, toLatinDigits, uuid } from '../lib/util'
import { Button, Empty, Field, Icon, Modal, StatusBadge, useToast } from './ui'

const CUSTOMER_KEY = 'nava_customer'

function CartView({ shop, onCheckout }) {
  const { t, num, money, err } = useI18n()
  const toast = useToast()
  const [busy, setBusy] = useState(null)
  const items = shop.cart?.items || []

  const run = async (key, action) => {
    setBusy(key)
    try { await action() } catch (error) { toast(err(error), 'danger') } finally { setBusy(null) }
  }
  if (!items.length) return <Empty title={t('cart.empty')} hint={t('cart.emptyHint')} />

  return (
    <>
      <ul className="cart-list">
        {items.map((item) => (
          <li key={item.product_id}>
            <div className="cart-name"><strong>{item.product_name}</strong><span className="muted">{money(item.unit_price)}</span></div>
            <div className="qty" role="group" aria-label={item.product_name}>
              <button type="button" disabled={busy === item.product_id} aria-label={t('cart.dec', { name: item.product_name })}
                onClick={() => run(item.product_id, () => (item.quantity > 1 ? shop.setQuantity(item.product_id, item.quantity - 1) : shop.removeItem(item.product_id)))}><Icon name="minus" size={16} /></button>
              <output>{num(item.quantity)}</output>
              <button type="button" disabled={busy === item.product_id || item.quantity >= 100} aria-label={t('cart.inc', { name: item.product_name })}
                onClick={() => run(item.product_id, () => shop.setQuantity(item.product_id, item.quantity + 1))}><Icon name="plus" size={16} /></button>
            </div>
            <strong className="cart-line">{money(item.line_total)}</strong>
            <button type="button" className="icon-btn" aria-label={t('cart.remove', { name: item.product_name })} onClick={() => run(item.product_id, () => shop.removeItem(item.product_id))}><Icon name="trash" size={18} /></button>
          </li>
        ))}
      </ul>
      <div className="cart-total"><span>{t('cart.total')}</span><strong>{money(shop.cart.total_amount)}</strong></div>
      <div className="stack">
        <Button variant="primary" onClick={onCheckout}>{t('cart.checkout')}</Button>
        <Button variant="ghost" size="sm" busy={busy === 'clear'} onClick={() => run('clear', shop.clearCart)}>{t('cart.clear')}</Button>
      </div>
    </>
  )
}

function CheckoutView({ shop, onBack, onDone }) {
  const { t, err } = useI18n()
  const saved = (() => { try { return JSON.parse(safeStorage.get(CUSTOMER_KEY) || '{}') } catch { return {} } })()
  const [form, setForm] = useState({ name: saved.name || '', phone: saved.phone || '', email: saved.email || '', address: saved.address || '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  // One idempotency key per checkout: a retry after a network failure can never create a second order.
  const idempotencyKey = useRef(uuid())
  const set = (name) => (event) => setForm((f) => ({ ...f, [name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const token = await shop.ensureGuest()
      const order = await api.checkout(shop.storeId, {
        customer_name: form.name.trim(),
        customer_phone: toLatinDigits(form.phone).trim(),
        customer_address: form.address.trim(),
        email: form.email.trim() || undefined,
      }, token, idempotencyKey.current)
      safeStorage.set(CUSTOMER_KEY, JSON.stringify(form))
      await Promise.all([shop.refreshCart(), shop.reloadCatalog()])
      onDone(order)
    } catch (e) {
      setError(err(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <Field label={t('checkout.name')}><input required maxLength={255} autoComplete="name" value={form.name} onChange={set('name')} data-autofocus /></Field>
      <Field label={t('checkout.phone')}><input required minLength={5} maxLength={50} type="tel" inputMode="tel" autoComplete="tel" dir="ltr" value={form.phone} onChange={set('phone')} /></Field>
      <Field label={`${t('checkout.email')} (${t('optional')})`}><input type="email" maxLength={255} autoComplete="email" dir="ltr" value={form.email} onChange={set('email')} /></Field>
      <Field label={t('checkout.address')}><textarea required rows={3} maxLength={500} autoComplete="street-address" value={form.address} onChange={set('address')} /></Field>
      {error && <p className="notice notice-danger" role="alert">{error}</p>}
      <Button type="submit" variant="primary" busy={busy}>{t('checkout.submit')}</Button>
      <Button variant="ghost" size="sm" onClick={onBack}>{t('checkout.back')}</Button>
    </form>
  )
}

function DoneView({ shop, order, onClose }) {
  const { t, id, money, err } = useI18n()
  const toast = useToast()
  const [payment, setPayment] = useState(null)
  const [busy, setBusy] = useState('')
  const payKey = useRef(uuid())
  const guest = shop.getGuestToken()

  const guarded = (name, action) => async () => {
    setBusy(name)
    try { await action() } catch (e) { toast(err(e), 'danger') } finally { setBusy('') }
  }
  const pay = guarded('pay', async () => {
    const created = await api.pay(order.id, payKey.current, guest)
    if (created.payment_url) { window.location.assign(created.payment_url); return } // real gateway
    setPayment(created) // sandbox provider: confirmed from this screen
  })
  const confirmPayment = guarded('verify', async () => {
    setPayment(await api.verifyPayment(payment.id, payment.authority, guest))
    toast(t('order.paid'))
  })
  const invoice = guarded('invoice', async () => {
    downloadBlob(await api.guestInvoice(shop.storeId, order.id, guest), `${order.invoice_number || 'invoice'}.pdf`)
  })

  return (
    <div className="stack">
      <dl className="facts">
        <div><dt>{t('order.number')}</dt><dd>{id(order.id)}</dd></div>
        <div>
          <dt>{t('order.tracking')}</dt>
          <dd className="row">{id(order.tracking_number)}<Button size="sm" onClick={async () => toast((await copyText(order.tracking_number)) ? t('copied') : t('err.generic'))}>{t('copy')}</Button></dd>
        </div>
        <div><dt>{t('o.status')}</dt><dd><StatusBadge status={order.status} /></dd></div>
        <div><dt>{t('cart.total')}</dt><dd><strong>{money(order.total_amount)}</strong></dd></div>
      </dl>
      <ul className="plain-list" aria-label={t('order.items')}>
        {order.items.map((item) => <li key={item.id}><span>{item.product_name} × {id(item.quantity)}</span><span>{money(item.line_total)}</span></li>)}
      </ul>

      {payment?.status === 'paid' ? (
        <p className="notice notice-ok" role="status">{t('order.paid')}</p>
      ) : payment ? (
        <div className="notice"><p>{t('order.sandbox')}</p><Button variant="primary" busy={busy === 'verify'} onClick={confirmPayment}>{t('order.sandboxConfirm')}</Button></div>
      ) : (
        <Button variant="primary" busy={busy === 'pay'} onClick={pay}>{t('order.pay')}</Button>
      )}
      <Button busy={busy === 'invoice'} onClick={invoice}>{t('order.invoice')}</Button>
      <Link className="btn btn-ghost" to={`/track?number=${order.tracking_number}`} onClick={onClose}>{t('order.trackLink')}</Link>
      <Button variant="ghost" onClick={onClose}>{t('order.continue')}</Button>
    </div>
  )
}

export default function CartDrawer({ shop, onClose }) {
  const { t } = useI18n()
  const [view, setView] = useState('cart')
  const [order, setOrder] = useState(null)
  const title = { cart: t('cart.title'), checkout: t('checkout.title'), done: t('order.placed') }[view]

  return (
    <Modal title={title} onClose={onClose} variant="drawer">
      {view === 'cart' && <CartView shop={shop} onCheckout={() => setView('checkout')} />}
      {view === 'checkout' && <CheckoutView shop={shop} onBack={() => setView('cart')} onDone={(created) => { setOrder(created); setView('done') }} />}
      {view === 'done' && order && <DoneView shop={shop} order={order} onClose={onClose} />}
    </Modal>
  )
}
