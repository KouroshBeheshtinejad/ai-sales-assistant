import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { Async, Badge, Button, ConfirmButton, Empty, Field, Icon, StatusBadge, useToast } from '../components/ui'
import { api } from '../lib/api'
import { useAsync, useSeo } from '../lib/hooks'
import { useAuth } from '../lib/auth'
import { useI18n } from '../lib/i18n'
import { useSeller } from './seller/SellerContext'

function DashboardHeader({ title }) {
  return <header className="page-head"><h1>{title}</h1></header>
}

export function dashboardPathForUser(user) {
  if (user.approval_status === 'pending') return '/workspace/pending'
  if (user.approval_status !== 'active') return '/workspace/rejected'
  if (user.role === 'god') return '/seller/platform'
  if (user.role === 'support') return '/seller/support'
  if (user.store_memberships?.some((membership) => membership.status === 'approved')) return '/seller'
  return {
    customer: '/workspace/customer',
    support: '/seller/support',
    god: '/seller/platform',
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
  const orders = useAsync(() => api.orders(), [])
  const conversations = useAsync(() => api.support.conversations(), [])
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submitSupport = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.support.create({ message })
      setMessage('')
      await conversations.reload()
    } catch (cause) {
      setError(cause.message)
    } finally {
      setBusy(false)
    }
  }
  useSeo({ title: `${t('dash.customer')} | NAVA` })
  return (
    <>
      <DashboardHeader title={t('dash.customer')} />
      <Async state={orders}>{(items) => items.length ? (
        <section className="card stack"><h2 className="h3">{t('dash.orders')}</h2>
          <ul className="plain-list">{items.map((order) => <li key={order.id}>
            <span><strong>{t('od.title', { id: id(order.id) })}</strong><span className="muted"> · {date(new Date(order.created_at))}</span><br />{order.tracking_number && <Link to={`/track?number=${order.tracking_number}`}>{t('order.tracking')}: {id(order.tracking_number)}</Link>}</span>
            <span className="stack"><StatusBadge status={order.status} /><strong>{money(order.total_amount)}</strong></span>
          </li>)}</ul>
        </section>
      ) : <Empty title={t('dash.empty')} />}</Async>
      <section className="card stack">
        <h2 className="h3">{t('dash.contactSupport')}</h2>
        <form className="stack" onSubmit={submitSupport}>
          <Field label={t('dash.supportMessage')}><textarea required maxLength={5000} value={message} onChange={(event) => setMessage(event.target.value)} /></Field>
          {error && <p className="notice notice-danger" role="alert">{error}</p>}
          <Button type="submit" variant="primary" busy={busy}><Icon name="send" size={16} />{t('dash.sendSupport')}</Button>
        </form>
        <Async state={conversations}>{(items) => !items.length ? <p className="muted">{t('dash.noSupportConversations')}</p> : (
          <ul className="list-cards">{items.map((item) => <CustomerSupportThread key={item.id} conversation={item} onReply={conversations.reload} />)}</ul>
        )}</Async>
      </section>
    </>
  )
}

function CustomerSupportThread({ conversation, onReply }) {
  const { t, date } = useI18n()
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const last = conversation.messages.at(-1)
  const reply = async (event) => {
    event.preventDefault()
    setBusy(true)
    try {
      await api.support.reply(conversation.id, message)
      setMessage('')
      await onReply()
    } finally {
      setBusy(false)
    }
  }
  return (
    <li className="card stack">
      <div className="row between"><strong>{t('dash.supportTicket', { id: conversation.id })}</strong><Badge>{t(`dash.supportStatus.${conversation.status}`)}</Badge></div>
      {last && <p>{last.content}</p>}
      <small className="muted">{date(new Date(conversation.updated_at))}</small>
      {!['resolved', 'closed'].includes(conversation.status) && <form className="row" onSubmit={reply}>
        <input required aria-label={t('dash.supportReply')} value={message} onChange={(event) => setMessage(event.target.value)} />
        <Button type="submit" size="sm" busy={busy}>{t('dash.reply')}</Button>
      </form>}
    </li>
  )
}

export function StoreSupportDashboard() {
  const { t } = useI18n()
  const { store } = useSeller()
  const conversations = useAsync(() => api.support.conversations(), [])
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useSeo({ title: `${t('dash.contactSupport')} | NAVA` })
  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.support.create({ store_id: store.id, message })
      setMessage('')
      await conversations.reload()
    } catch (cause) {
      setError(cause.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <DashboardHeader title={t('dash.contactSupport')} />
      <section className="card stack">
        <h2 className="h3">{store.name}</h2>
        <form className="stack" onSubmit={submit}>
          <Field label={t('dash.supportMessage')}><textarea required maxLength={5000} value={message} onChange={(event) => setMessage(event.target.value)} /></Field>
          {error && <p className="notice notice-danger" role="alert">{error}</p>}
          <Button type="submit" variant="primary" busy={busy}><Icon name="send" size={16} />{t('dash.sendSupport')}</Button>
        </form>
        <Async state={conversations}>{(items) => {
          const storeThreads = items.filter((item) => item.store_id === store.id)
          return !storeThreads.length ? <p className="muted">{t('dash.noSupportConversations')}</p> : <ul className="list-cards">{storeThreads.map((item) => <CustomerSupportThread key={item.id} conversation={item} onReply={conversations.reload} />)}</ul>
        }}</Async>
      </section>
    </>
  )
}

export function SupportDashboard() {
  const { t, date, money } = useI18n()
  const [statusFilter, setStatusFilter] = useState('')
  const [selected, setSelected] = useState(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const queue = useAsync(() => api.support.queue(statusFilter || undefined), [statusFilter])
  useSeo({ title: `${t('dash.support')} | NAVA` })
  const act = async (operation) => {
    setBusy(true)
    try {
      await operation()
      await queue.reload()
      setSelected(null)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <DashboardHeader title={t('dash.support')} />
      <div className="row">
        <Field label={t('dash.filterStatus')}><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="">{t('dash.allStatuses')}</option>
          {['new', 'assigned', 'waiting_customer', 'waiting_support', 'resolved', 'closed'].map((value) => <option key={value} value={value}>{t(`dash.supportStatus.${value}`)}</option>)}
        </select></Field>
      </div>
      <Async state={queue}>{(items) => !items.length ? <Empty title={t('dash.noSupportConversations')} /> : (
        <div className="two-col">
          <ul className="list-cards">{items.map((item) => <li key={item.id} className="card stack">
            <Button variant="ghost" size="sm" onClick={() => setSelected(item)}>{t('dash.supportTicket', { id: item.id })}</Button>
            <span>{item.messages.at(-1)?.content}</span>
            {item.customer && <small className="muted">{item.customer.name || item.customer.email}{item.store ? ` · ${item.store.name}` : ''}</small>}
            <div className="row between"><Badge>{t(`dash.supportStatus.${item.status}`)}</Badge><small className="muted">{date(new Date(item.updated_at))}</small></div>
            {item.assigned_to ? <small className="muted">{t('dash.assigned')}</small> : <Button size="sm" busy={busy} onClick={() => act(() => api.support.claim(item.id))}>{t('dash.claim')}</Button>}
          </li>)}</ul>
          {selected && <section className="card stack" aria-label={t('dash.supportTicket', { id: selected.id })}>
            <h2 className="h3">{t('dash.supportTicket', { id: selected.id })}</h2>
            {selected.customer && <p className="muted">{selected.customer.name || selected.customer.email}{selected.customer.phone ? ` · ${selected.customer.phone}` : ''}{selected.store ? ` · ${selected.store.name}` : ''}</p>}
            {selected.order && <p className="muted">{t('od.title', { id: selected.order.id })} · {t(`status.${selected.order.status}`)} · {money(selected.order.total_amount)}</p>}
            <div className="transcript" role="log">{selected.messages.map((item) => <p key={item.id} className="bubble">{item.content}</p>)}</div>
            <form className="stack" onSubmit={(event) => { event.preventDefault(); act(() => api.support.agentReply(selected.id, message)) }}>
              <Field label={t('dash.supportReply')}><textarea required maxLength={5000} value={message} onChange={(event) => setMessage(event.target.value)} /></Field>
              <div className="row"><Button type="submit" busy={busy}>{t('dash.reply')}</Button><Button type="button" variant="primary" busy={busy} onClick={() => act(() => api.support.setStatus(selected.id, 'resolved'))}>{t('dash.resolve')}</Button></div>
            </form>
          </section>}
        </div>
      )}</Async>
    </>
  )
}

export function GodDashboard() {
  const { t, id, money, date } = useI18n()
  const { select } = useSeller()
  const toast = useToast()
  const load = () => Promise.all([
    api.admin.users(),
    api.admin.stores(),
    api.admin.products(),
    api.admin.orders(),
    api.admin.auditLogs(),
    api.admin.databaseSummary(),
    api.support.queue(),
  ])
  const state = useAsync(load, [])
  const [busyId, setBusyId] = useState(null)
  const [databaseEntity, setDatabaseEntity] = useState('users')
  const [databaseQuery, setDatabaseQuery] = useState('')
  const [databaseSearch, setDatabaseSearch] = useState('')
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [ownerSelections, setOwnerSelections] = useState({})
  const systemOverview = useAsync(() => api.admin.systemOverview(), [])
  const databaseRecords = useAsync(
    () => api.admin.databaseRecords(databaseEntity, databaseSearch),
    [databaseEntity, databaseSearch],
  )
  const databaseRecord = useAsync(
    () => selectedRecord ? api.admin.databaseRecord(selectedRecord.entity, selectedRecord.id) : null,
    [selectedRecord?.entity, selectedRecord?.id],
  )
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
      <Async state={state}>{([users, stores, products, orders, auditLogs, databaseSummary, supportQueue]) => <>
        <dl className="stats">
          {[[t('dash.users'), users.length], [t('dash.stores'), stores.length], [t('dash.products'), products.length], [t('dash.orders'), orders.length], [t('dash.openSupport'), supportQueue.filter((item) => !['resolved', 'closed'].includes(item.status)).length]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{id(value)}</dd></div>)}
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
        <section className="card stack"><h2 className="h3">{t('dash.stores')}</h2><ul className="plain-list">{stores.map((store) => <li key={store.id}>
          <span><strong>{store.name}</strong><br /><span className="muted">{store.owner_email}</span></span>
          <span className="row">{t('dash.owner')}: {id(store.owner_id)}
            <Field label={t('dash.transferOwner')}><select value={ownerSelections[store.id] || ''} onChange={(event) => setOwnerSelections((current) => ({ ...current, [store.id]: event.target.value }))}><option value="">{t('dash.selectOwner')}</option>{users.filter((user) => user.is_verified && user.approval_status === 'active').map((user) => <option key={user.id} value={user.id}>{user.email}</option>)}</select></Field>
            {ownerSelections[store.id] && <ConfirmButton size="sm" busy={busyId === `store-${store.id}`} onConfirm={() => act(`store-${store.id}`, () => api.admin.transferStoreOwner(store.id, Number(ownerSelections[store.id])))}>{t('dash.transferOwner')}</ConfirmButton>}
            <Link className="btn btn-sm" to="/seller" onClick={() => select(store.id)}>{t('dash.manage')}</Link>
          </span>
        </li>)}</ul></section>
        <section className="card stack"><h2 className="h3">{t('dash.products')}</h2><ul className="plain-list">{products.map((product) => <li key={product.id}><span>{product.name}<br /><span className="muted">{t('s.activeStore')}: {id(product.store_id)}</span></span><span className="row">{money(product.price)}<Link className="btn btn-sm" to="/seller/products" onClick={() => select(product.store_id)}>{t('dash.manage')}</Link></span></li>)}</ul></section>
        <section className="card stack"><h2 className="h3">{t('dash.orders')}</h2><ul className="plain-list">{orders.slice(0, 20).map((order) => <li key={order.id}><span>{order.customer_name}<br /><span dir="ltr">{order.tracking_number}</span></span><span className="row"><StatusBadge status={order.status} /> {money(order.total_amount)}<Link className="btn btn-sm" to={`/seller/order/${order.id}`}>{t('dash.manage')}</Link></span></li>)}</ul></section>
        <section className="card stack"><h2 className="h3">{t('dash.auditLogs')}</h2>
          {auditLogs.length === 0 ? <p className="muted">{t('dash.empty')}</p> : <ul className="plain-list">{auditLogs.slice(0, 10).map((event) => <li key={event.id}>
            <span><strong>{event.action}</strong><br /><span className="muted">{event.resource_type} · {event.resource_id || '—'}</span></span>
            <span className="muted">{date(new Date(event.created_at))}</span>
          </li>)}</ul>}
        </section>
        <section className="card stack"><h2 className="h3">{t('dash.database')}</h2>
          <ul className="plain-list">{databaseSummary.map((item) => <li key={item.entity}><span>{item.entity}</span><strong>{id(item.count)}</strong></li>)}</ul>
          <div className="row">
            <Field label={t('dash.databaseEntity')}><select value={databaseEntity} onChange={(event) => { setDatabaseEntity(event.target.value); setSelectedRecord(null) }}>{databaseSummary.map((item) => <option key={item.entity} value={item.entity}>{item.entity}</option>)}</select></Field>
            <form className="row" onSubmit={(event) => { event.preventDefault(); setDatabaseSearch(databaseQuery); setSelectedRecord(null) }}>
              <Field label={t('dash.databaseSearch')}><input value={databaseQuery} onChange={(event) => setDatabaseQuery(event.target.value)} /></Field>
              <Button type="submit">{t('dash.search')}</Button>
            </form>
          </div>
          <Async state={databaseRecords}>{(records) => <ul className="plain-list">{records.map((record) => <li key={record.id}>
            <span>{Object.entries(record).slice(0, 3).map(([key, value]) => `${key}: ${value ?? '—'}`).join(' · ')}</span>
            {databaseEntity === 'memberships' && <Link className="btn btn-sm" to="/seller/team" onClick={() => select(record.store_id)}>{t('dash.manage')}</Link>}
            {databaseEntity === 'stores' && <Link className="btn btn-sm" to="/seller" onClick={() => select(record.id)}>{t('dash.manage')}</Link>}
            {databaseEntity === 'products' && <Link className="btn btn-sm" to="/seller/products" onClick={() => select(record.store_id)}>{t('dash.manage')}</Link>}
            {['faqs', 'knowledge'].includes(databaseEntity) && <Link className="btn btn-sm" to="/seller/knowledge" onClick={() => select(record.store_id)}>{t('dash.manage')}</Link>}
            {databaseEntity === 'orders' && <Link className="btn btn-sm" to={`/seller/order/${record.id}`}>{t('dash.manage')}</Link>}
            <Button size="sm" onClick={() => setSelectedRecord({ entity: databaseEntity, id: record.id })}>{t('dash.inspect')}</Button>
          </li>)}</ul>}</Async>
          {selectedRecord && <Async state={databaseRecord}>{(record) => <pre className="api-detail-body">{JSON.stringify(record, null, 2)}</pre>}</Async>}
        </section>
        <section className="card stack"><h2 className="h3">{t('dash.system')}</h2>
          <Async state={systemOverview}>{(system) => <>
            <div className="row"><Badge tone={system.database_status === 'ok' ? 'ok' : 'danger'}>{t(`dash.databaseStatus.${system.database_status}`)}</Badge></div>
            <dl className="stats">
              {[[t('dash.activeUsers'), system.users.active], [t('dash.pendingUsers'), system.users.pending], [t('dash.payments'), system.payments.total], [t('dash.paymentPending'), system.payments.by_status.pending], [t('dash.paymentPaid'), system.payments.by_status.paid], [t('dash.paymentFailed'), system.payments.by_status.failed]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{id(value)}</dd></div>)}
            </dl>
          </>}</Async>
        </section>
      </>}</Async>
    </main>
  )
}
