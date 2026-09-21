import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Async, Badge, Button, ConfirmButton, Empty, Field, Modal, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { copyText, parseDate } from '../../lib/util'
import { PageHead } from './SellerLayout'
import { useSeller } from './SellerContext'

function StoreForm({ store, onSaved, onCancel }) {
  const { t, err, bizLabel } = useI18n()
  const { types } = useSeller()
  const [form, setForm] = useState({ name: store?.name || '', description: store?.description || '', business_type: store?.business_type || 'clothing' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const payload = { name: form.name.trim(), description: form.description.trim() || null, business_type: form.business_type }
      const saved = store ? await api.seller.updateStore(store.id, payload) : await api.seller.createStore(payload)
      await onSaved(saved.store_id)
    } catch (e) {
      setError(err(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <Field label={t('s.storeName')}><input required maxLength={255} value={form.name} onChange={set('name')} data-autofocus /></Field>
      <Field label={t('s.businessType')}>
        <select value={form.business_type} onChange={set('business_type')}>
          {types.map((type) => <option key={type.slug} value={type.slug}>{bizLabel(type.slug, type.label)}</option>)}
        </select>
      </Field>
      <Field label={t('s.storeDesc')}><textarea rows={3} maxLength={10000} value={form.description} onChange={set('description')} /></Field>
      {error && <p className="notice notice-danger" role="alert">{error}</p>}
      <div className="row">
        <Button type="submit" variant="primary" busy={busy}>{store ? t('save') : t('create')}</Button>
        {onCancel && <Button onClick={onCancel}>{t('cancel')}</Button>}
      </div>
    </form>
  )
}

function StorePanel({ store }) {
  const { t, bizLabel, err } = useI18n()
  const toast = useToast()
  const { reloadStores, select } = useSeller()
  const [modal, setModal] = useState(null)
  const url = `${location.origin}/store/${store.id}`
  const label = bizLabel(store.business_type, store.business_type_label)

  const saved = async (id) => {
    await reloadStores()
    if (modal === 'create' && id) select(id)
    toast(modal === 'create' ? t('s.storeCreated') : t('saved'))
    setModal(null)
  }
  const remove = async () => {
    try {
      await api.seller.deleteStore(store.id)
      await reloadStores()
      toast(t('deleted'))
      setModal(null)
    } catch (e) {
      toast(err(e), 'danger')
    }
  }

  return (
    <section className="card stack">
      <div className="row between">
        <div><h2 className="h3">{store.name}</h2><p className="muted">{label}</p></div>
        <div className="row">
          <Button size="sm" onClick={() => setModal('edit')}>{t('s.editStore')}</Button>
          <Button size="sm" onClick={() => setModal('create')}>{t('s.newStore')}</Button>
        </div>
      </div>
      <div className="row">
        <span className="muted">{t('s.publicLink')}</span>
        <a href={url} target="_blank" rel="noreferrer" dir="ltr">{url}</a>
        <Button size="sm" onClick={async () => toast((await copyText(url)) ? t('copied') : t('err.generic'))}>{t('copy')}</Button>
      </div>
      {modal && (
        <Modal title={modal === 'edit' ? t('s.editStore') : t('s.newStore')} onClose={() => setModal(null)}>
          <StoreForm key={modal} store={modal === 'edit' ? store : null} onSaved={saved} onCancel={() => setModal(null)} />
          {modal === 'edit' && (
            <div className="danger-zone">
              <p className="muted">{t('s.deleteStoreNote')}</p>
              <ConfirmButton variant="danger" onConfirm={remove}>{t('s.deleteStore')}</ConfirmButton>
            </div>
          )}
        </Modal>
      )}
    </section>
  )
}

export default function Overview() {
  const { t, num, money, id, date } = useI18n()
  const { store, reloadStores, select } = useSeller()
  useSeo({ title: `${t('s.overview')} | NAVA` })
  const data = useAsync(() => (store ? Promise.all([api.seller.orders(store.id), api.seller.products(store.id), api.seller.conversations(store.id)]) : null), [store?.id])

  if (!store) {
    return (
      <div className="page-narrow">
        <Empty title={t('s.noStoreTitle')} hint={t('s.noStoreBody')} />
        <div className="card">
          <StoreForm onSaved={async (newId) => { await reloadStores(); select(newId) }} />
        </div>
      </div>
    )
  }

  return (
    <>
      <PageHead title={t('s.overview')} />
      <StorePanel store={store} />
      <Async state={data}>
        {([orders, products, conversations]) => {
          const pending = orders.filter((o) => o.status === 'pending')
          const value = orders.filter((o) => o.status !== 'cancelled').reduce((sum, o) => sum + Number(o.total_amount), 0)
          const low = products.filter((p) => p.is_active && p.stock <= 3).sort((a, b) => a.stock - b.stock)
          const stats = [
            [t('ov.orders'), num(orders.length)],
            [t('ov.value'), money(value)],
            [t('ov.products'), num(products.filter((p) => p.is_active).length)],
            [t('ov.conversations'), num(conversations.length)],
          ]
          return (
            <>
              <dl className="stats">
                {stats.map(([label, number]) => <div key={label}><dt>{label}</dt><dd>{number}</dd></div>)}
              </dl>
              <div className="two-col">
                <section className="card stack">
                  <h2 className="h3">{t('ov.attention')}</h2>
                  {!pending.length && !low.length && <p className="muted">{t('ov.allGood')}</p>}
                  {pending.length > 0 && (
                    <>
                      <h3 className="h4">{t('ov.pendingOrders')}</h3>
                      <ul className="plain-list">
                        {pending.slice(0, 5).map((o) => <li key={o.id}><Link to={`/seller/order/${o.id}`}>{t('od.title', { id: id(o.id) })} · {o.customer_name}</Link><span>{money(o.total_amount)}</span></li>)}
                      </ul>
                    </>
                  )}
                  {low.length > 0 && (
                    <>
                      <h3 className="h4">{t('ov.lowStock')}</h3>
                      <ul className="plain-list">
                        {low.slice(0, 5).map((p) => <li key={p.id}><Link to="/seller/products">{p.name}</Link><Badge tone={p.stock === 0 ? 'danger' : 'warn'}>{p.stock === 0 ? t('shop.outOfStock') : t('ov.lowStockItem', { n: p.stock })}</Badge></li>)}
                      </ul>
                    </>
                  )}
                </section>
                <section className="card stack">
                  <h2 className="h3">{t('ov.recent')}</h2>
                  {!conversations.length && <p className="muted">{t('c.empty')}</p>}
                  <ul className="plain-list">
                    {conversations.slice(0, 5).map((c) => <li key={c.id}><Link to={`/seller/conversation/${c.id}`}>{t('c.guest', { id: id(c.id) })}</Link><span className="muted">{date(parseDate(c.updated_at))}</span></li>)}
                  </ul>
                </section>
              </div>
            </>
          )
        }}
      </Async>
    </>
  )
}
