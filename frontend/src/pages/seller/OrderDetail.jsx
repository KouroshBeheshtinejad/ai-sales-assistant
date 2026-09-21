import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Async, Button, ConfirmButton, StatusBadge, Timeline, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { TRANSITIONS } from '../../lib/orders'
import { parseDate } from '../../lib/util'
import { PageHead } from './SellerLayout'

export default function OrderDetail() {
  const { orderId } = useParams()
  const { t, id, money, date, err } = useI18n()
  const toast = useToast()
  const [busy, setBusy] = useState('')
  const state = useAsync(() => api.seller.order(orderId), [orderId])
  useSeo({ title: `${t('od.title', { id: id(orderId) })} | NAVA` })

  const move = async (next) => {
    setBusy(next)
    try {
      state.setData(await api.seller.setOrderStatus(orderId, next))
      toast(t('od.updated'))
    } catch (e) {
      toast(err(e), 'danger')
    } finally {
      setBusy('')
    }
  }

  return (
    <>
      <Link className="back-link" to="/seller/orders">{t('s.orders')}</Link>
      <Async state={state}>
        {(order) => {
          const options = TRANSITIONS[order.status] || []
          return (
            <>
              <PageHead title={t('od.title', { id: id(order.id) })} actions={<StatusBadge status={order.status} />} />
              <div className="two-col">
                <section className="card stack">
                  <Timeline status={order.status} />
                  <h2 className="h3">{t('od.next')}</h2>
                  {options.length === 0 ? <p className="muted">{t('od.final')}</p> : (
                    <div className="row">
                      {options.map((next) => next === 'cancelled'
                        ? <ConfirmButton key={next} variant="danger" size="md" busy={busy === next} onConfirm={() => move(next)}>{t('od.cancelOrder')}</ConfirmButton>
                        : <Button key={next} variant="primary" busy={busy === next} disabled={Boolean(busy)} onClick={() => move(next)}>{t('od.moveTo', { status: t(`status.${next}`) })}</Button>)}
                    </div>
                  )}
                </section>
                <section className="card">
                  <dl className="facts">
                    <div><dt>{t('o.customer')}</dt><dd>{order.customer_name}</dd></div>
                    <div><dt>{t('od.phone')}</dt><dd dir="ltr">{order.customer_phone}</dd></div>
                    <div><dt>{t('od.address')}</dt><dd>{order.customer_address}</dd></div>
                    <div><dt>{t('order.tracking')}</dt><dd>{id(order.tracking_number)}</dd></div>
                    <div><dt>{t('od.invoice')}</dt><dd dir="ltr">{order.invoice_number}</dd></div>
                    <div><dt>{t('od.date')}</dt><dd>{date(parseDate(order.created_at))}</dd></div>
                  </dl>
                </section>
              </div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th scope="col">{t('od.item')}</th><th scope="col">{t('od.unit')}</th><th scope="col">{t('od.qty')}</th><th scope="col">{t('od.line')}</th></tr></thead>
                  <tbody>
                    {order.items.map((item) => <tr key={item.id}><td>{item.product_name}</td><td>{money(item.unit_price)}</td><td>{id(item.quantity)}</td><td>{money(item.line_total)}</td></tr>)}
                  </tbody>
                  <tfoot><tr><th scope="row" colSpan={3}>{t('cart.total')}</th><td><strong>{money(order.total_amount)}</strong></td></tr></tfoot>
                </table>
              </div>
            </>
          )
        }}
      </Async>
    </>
  )
}
