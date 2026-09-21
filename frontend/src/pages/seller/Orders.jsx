import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Async, Empty, StatusBadge } from '../../components/ui'
import { api } from '../../lib/api'
import { useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { ALL_STATUSES } from '../../lib/orders'
import { cx, parseDate, toLatinDigits } from '../../lib/util'
import { useSeller } from './SellerContext'
import { NeedStore, PageHead } from './SellerLayout'

export default function Orders() {
  const { t, num, id, money, date } = useI18n()
  const { store } = useSeller()
  const [status, setStatus] = useState('all')
  const [query, setQuery] = useState('')
  useSeo({ title: `${t('s.orders')} | NAVA` })
  const state = useAsync(() => (store ? api.seller.orders(store.id) : null), [store?.id])
  if (!store) return <NeedStore />

  return (
    <>
      <PageHead title={t('s.orders')} />
      <Async state={state}>
        {(orders) => {
          if (!orders.length) return <Empty title={t('o.empty')} />
          const needle = toLatinDigits(query).trim().toLowerCase()
          const rows = orders.filter((o) => (status === 'all' || o.status === status)
            && (!needle || [o.customer_name, o.customer_phone, o.tracking_number, String(o.id)].some((v) => String(v).toLowerCase().includes(needle))))
          const count = (s) => orders.filter((o) => o.status === s).length
          return (
            <>
              <div className="toolbar">
                <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('o.search')} aria-label={t('o.search')} />
                <div className="chips" role="group" aria-label={t('o.status')}>
                  {['all', ...ALL_STATUSES].map((s) => (
                    <button key={s} type="button" className={cx('chip', status === s && 'on')} aria-pressed={status === s} onClick={() => setStatus(s)}>
                      {s === 'all' ? t('o.all') : t(`status.${s}`)} <span className="muted">{num(s === 'all' ? orders.length : count(s))}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th scope="col">{t('o.id')}</th><th scope="col">{t('o.customer')}</th><th scope="col">{t('o.total')}</th><th scope="col">{t('o.status')}</th><th scope="col">{t('o.date')}</th></tr>
                  </thead>
                  <tbody>
                    {rows.map((o) => (
                      <tr key={o.id}>
                        <td><Link to={`/seller/order/${o.id}`}>{id(o.id)}</Link></td>
                        <td>{o.customer_name}<small dir="ltr">{o.customer_phone}</small></td>
                        <td>{money(o.total_amount)}</td>
                        <td><StatusBadge status={o.status} /></td>
                        <td>{date(parseDate(o.created_at))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!rows.length && <Empty title={t('shop.empty')} />}
              </div>
            </>
          )
        }}
      </Async>
    </>
  )
}
