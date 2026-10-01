import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { Async, Badge, Button, Empty, Field, StatusBadge, useToast } from '../components/ui'
import { api } from '../lib/api'
import { useAsync, useSeo } from '../lib/hooks'
import { useAuth } from '../lib/auth'
import { useI18n } from '../lib/i18n'

function DashboardHeader({ title }) {
  return <header className="page-head"><h1>{title}</h1></header>
}

export function dashboardPathForUser(user) {
  if (user.approval_status === 'pending') return '/workspace/pending'
  if (user.approval_status !== 'active') return '/workspace/rejected'
  return {
    customer: '/workspace/customer',
    support: '/workspace/support',
    god: '/workspace/god',
    store_owner: '/seller',
    store_admin: '/seller',
  }[user.role] || '/workspace/pending'
}

export function RoleDashboardRouter() {
  const { user, loading } = useAuth()
  if (loading || !user) return null
  return <Navigate to={dashboardPathForUser(user)} replace />
}

export function PendingDashboard() {
  const { t } = useI18n()
  useSeo({ title: `${t('dash.pendingTitle')} | NAVA` })
  return <main className="wrap page-narrow"><DashboardHeader title={t('dash.pendingTitle')} /><p className="notice">{t('dash.pendingBody')}</p></main>
}

export function RejectedDashboard() {
  const { t } = useI18n()
  return <main className="wrap page-narrow"><DashboardHeader title={t('dash.pendingTitle')} /><p className="notice notice-danger">{t('dash.rejected')}</p></main>
}

export function CustomerDashboard() {
  const { t, money, id, date } = useI18n()
  useSeo({ title: `${t('dash.customer')} | NAVA` })
  const orders = useAsync(() => api.orders(), [])
  return (
    <main className="wrap page-narrow">
      <DashboardHeader title={t('dash.customer')} />
      <Async state={orders}>{(items) => items.length ? (
        <section className="card stack">
          <h2 className="h3">{t('dash.orders')}</h2>
          <ul className="plain-list">
            {items.map((order) => <li key={order.id}>
              <span><strong>{t('od.title', { id: id(order.id) })}</strong><span className="muted"> · {date(new Date(order.created_at))}</span><br />{order.tracking_number && <Link to={`/track?number=${order.tracking_number}`}>{t('order.tracking')}: {id(order.tracking_number)}</Link>}</span>
              <span className="stack"><StatusBadge status={order.status} /><strong>{money(order.total_amount)}</strong></span>
            </li>)}
          </ul>
        </section>
      ) : <Empty title={t('dash.empty')} />}</Async>
    </main>
  )
}

export function SupportDashboard() {
  const { t, id, money, date } = useI18n()
  useSeo({ title: `${t('dash.support')} | NAVA` })
  const orders = useAsync(() => api.admin.orders(), [])
  return (
    <main className="wrap page-narrow">
      <DashboardHeader title={t('dash.support')} />
      <Async state={orders}>{(items) => items.length ? (
        <section className="card stack"><h2 className="h3">{t('dash.orders')}</h2>
          <ul className="plain-list">{items.map((order) => <li key={order.id}>
            <span><strong>{order.customer_name}</strong><br /><span dir="ltr">{order.customer_phone}</span><br /><span className="muted">{t('od.title', { id: id(order.id) })} · {date(new Date(order.created_at))}</span></span>
            <span className="stack"><StatusBadge status={order.status} /><span dir="ltr">{order.tracking_number}</span><strong>{money(order.total_amount)}</strong></span>
          </li>)}</ul>
        </section>
      ) : <Empty title={t('dash.empty')} />}</Async>
    </main>
  )
}

export function GodDashboard() {
  const { t, id, money } = useI18n()
  const toast = useToast()
  const load = () => Promise.all([api.admin.users(), api.admin.stores(), api.admin.products(), api.admin.orders()])
  const state = useAsync(load, [])
  const [busyId, setBusyId] = useState(null)
  const accountRequests = (state.data?.[0] || []).filter((user) =>
    user.approval_status === 'pending' && ['store_owner', 'support'].includes(user.role),
  )
  useSeo({ title: `${t('dash.god')} | NAVA` })

  const act = async (userId, action) => {
    setBusyId(userId)
    try {
      await action()
      await state.reload()
    } catch (error) {
      toast(error.message, 'danger')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <main className="wrap page-narrow">
      <DashboardHeader title={t('dash.god')} />
      <Link className="btn btn-primary" to="/seller">{t('dash.openOperations')}</Link>
      <Async state={state}>{([users, stores, products, orders]) => <>
        <dl className="stats">
          {[[t('dash.users'), users.length], [t('dash.stores'), stores.length], [t('dash.products'), products.length], [t('dash.orders'), orders.length]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{id(value)}</dd></div>)}
        </dl>
        <section className="card stack">
          <h2 className="h3">{t('dash.approvals')}</h2>
          {accountRequests.length === 0 && <p className="muted">{t('dash.empty')}</p>}
          <ul className="plain-list">{accountRequests.map((user) => <li key={user.id}>
            <span><strong>{user.name || user.email}</strong><br /><span dir="ltr">{user.email}</span><br /><span className="muted">{t(`role.${user.role}`)} · {user.is_verified ? t('dash.verified') : t('auth.verifyTitle')}</span></span>
            <span className="row"><Button size="sm" disabled={!user.is_verified} busy={busyId === user.id} onClick={() => act(user.id, () => api.admin.decideAccount(user.id, 'active'))}>{t('dash.approve')}</Button><Button size="sm" variant="danger" busy={busyId === user.id} onClick={() => act(user.id, () => api.admin.decideAccount(user.id, 'rejected'))}>{t('dash.reject')}</Button></span>
          </li>)}</ul>
        </section>
        <section className="card stack"><h2 className="h3">{t('dash.users')}</h2>
          <ul className="plain-list">{users.map((user) => <li key={user.id}>
            <span><strong>{user.name || user.email}</strong><br /><span dir="ltr">{user.email}</span></span>
            <span className="row"><Badge>{t(`role.${user.role}`)}</Badge>{user.role !== 'god' && user.role !== 'store_admin' && <Field label={t('dash.role')}><select aria-label={`${t('dash.role')}: ${user.email}`} value={user.role} disabled={user.approval_status === 'pending' || busyId === user.id} onChange={(event) => act(user.id, () => api.admin.setRole(user.id, event.target.value))}>{['customer', 'store_owner', 'support'].map((role) => <option key={role} value={role}>{t(`role.${role}`)}</option>)}</select></Field>}</span>
          </li>)}</ul>
        </section>
        <section className="card stack"><h2 className="h3">{t('dash.stores')}</h2><ul className="plain-list">{stores.map((store) => <li key={store.id}><span><strong>{store.name}</strong><br /><span className="muted">{store.owner_email}</span></span><span>{t('dash.owner')}: {id(store.owner_id)}</span></li>)}</ul></section>
        <section className="card stack"><h2 className="h3">{t('dash.products')}</h2><ul className="plain-list">{products.map((product) => <li key={product.id}><span>{product.name}<br /><span className="muted">{t('s.activeStore')}: {id(product.store_id)}</span></span><span>{money(product.price)}</span></li>)}</ul></section>
        <section className="card stack"><h2 className="h3">{t('dash.orders')}</h2><ul className="plain-list">{orders.slice(0, 20).map((order) => <li key={order.id}><span>{order.customer_name}<br /><span dir="ltr">{order.tracking_number}</span></span><span><StatusBadge status={order.status} /> {money(order.total_amount)}</span></li>)}</ul></section>
      </>}</Async>
    </main>
  )
}
