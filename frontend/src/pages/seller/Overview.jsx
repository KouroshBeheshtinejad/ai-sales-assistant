import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Async, Badge, Button, ConfirmButton, Empty, Field, Icon, Modal, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { useAuth } from '../../lib/auth'
import { copyText, parseDate } from '../../lib/util'
import { PageHead } from './SellerLayout'
import { useSeller } from './SellerContext'

export function BusinessTypePicker({ types, value, onChange, label }) {
  const { t, bizLabel } = useI18n()
  const pickerId = useId()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const rootRef = useRef(null)
  const searchRef = useRef(null)
  const selectedType = types.find((type) => type.slug === value)
  const filteredTypes = types.filter((type) => bizLabel(type.slug, type.label).toLowerCase().includes(query.trim().toLowerCase()))

  useEffect(() => {
    if (!open) return undefined
    searchRef.current?.focus()
    const closeOnOutsideClick = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('pointerdown', closeOnOutsideClick)
    return () => document.removeEventListener('pointerdown', closeOnOutsideClick)
  }, [open])

  const close = () => {
    setOpen(false)
    setQuery('')
  }

  return (
    <div className="field business-type-field" ref={rootRef}>
      <label htmlFor={pickerId}>{label}</label>
      <button id={pickerId} type="button" className="business-type-trigger" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <span>{selectedType ? bizLabel(selectedType.slug, selectedType.label) : ''}</span>
        <Icon name="chevron" size={18} />
      </button>
      {open && <div className="business-type-menu">
        <input ref={searchRef} type="search" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Escape') { event.stopPropagation(); close() } }} placeholder={t('dash.search')} aria-label={`${label} ${t('dash.search')}`} />
        <div className="business-type-options" role="listbox" aria-label={label}>
          {filteredTypes.map((type) => <button type="button" role="option" aria-selected={type.slug === value} className={type.slug === value ? 'selected' : ''} key={type.slug} onClick={() => { onChange(type.slug); close() }}>{bizLabel(type.slug, type.label)}</button>)}
          {!filteredTypes.length && <p className="muted business-type-empty">{t('s.noBusinessTypesMatch')}</p>}
        </div>
      </div>}
    </div>
  )
}

function StoreForm({ store, onSaved, onCancel }) {
  const { t, err } = useI18n()
  const { types } = useSeller()
  const [form, setForm] = useState({
    name: store?.name || '',
    description: store?.description || '',
    business_type: store?.business_type || 'clothing',
    categories: store?.categories || [],
    primary_color: store?.primary_color || '#0d8a85',
    secondary_color: store?.secondary_color || '#f2f7f6',
    logo: null,
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        business_type: form.business_type,
        categories: form.categories.map((category) => ({ ...category, name: category.name.trim() })),
        primary_color: form.primary_color,
        secondary_color: form.secondary_color,
      }
      const saved = store ? await api.seller.updateStore(store.id, payload) : await api.seller.createStore(payload)
      if (form.logo) await api.seller.uploadStoreLogo(saved.store_id, form.logo)
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
      <BusinessTypePicker types={types} value={form.business_type} onChange={(business_type) => setForm((current) => ({ ...current, business_type }))} label={t('s.businessType')} />
      <Field label={t('s.storeDesc')}><textarea rows={3} maxLength={10000} value={form.description} onChange={set('description')} /></Field>
      <Field label={t('s.logo')}><input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={(e) => setForm({ ...form, logo: e.target.files?.[0] || null })} /></Field>
      <fieldset className="store-category-editor">
        <legend>{t('s.categoryTabs')}</legend>
        {form.categories.map((category) => <div className="row" key={category.id}>
          <Field label={t('s.categoryName')}><input required maxLength={60} value={category.name} onChange={(event) => setForm((current) => ({ ...current, categories: current.categories.map((item) => item.id === category.id ? { ...item, name: event.target.value } : item) }))} /></Field>
          <button type="button" className="icon-btn" aria-label={t('s.removeCategory')} onClick={() => setForm((current) => ({ ...current, categories: current.categories.filter((item) => item.id !== category.id) }))}><Icon name="trash" size={18} /></button>
        </div>)}
        <Button type="button" size="sm" onClick={() => setForm((current) => ({ ...current, categories: [...current.categories, { id: globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`, name: '' }] }))}><Icon name="plus" size={16} />{t('s.addCategory')}</Button>
      </fieldset>
      <div className="store-color-fields">
        <Field label={t('s.primaryColor')}><input className="store-color-input" type="color" value={form.primary_color} onChange={set('primary_color')} /></Field>
        <Field label={t('s.secondaryColor')}><input className="store-color-input" type="color" value={form.secondary_color} onChange={set('secondary_color')} /></Field>
      </div>
      {error && <p className="notice notice-danger" role="alert">{error}</p>}
      <div className="row">
        <Button type="submit" variant="primary" busy={busy}>{store ? t('save') : t('create')}</Button>
        {onCancel && <Button onClick={onCancel}>{t('cancel')}</Button>}
      </div>
    </form>
  )
}

function StoreAdminRequests({ storeId }) {
  const { t, err } = useI18n()
  const toast = useToast()
  const [requests, setRequests] = useState([])
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')

  const reload = async () => {
    try { setRequests(await api.seller.adminRequests(storeId)); setError('') } catch (cause) { setError(err(cause)) }
  }
  useEffect(() => { reload() }, [storeId])

  const decide = async (request, status) => {
    setBusyId(request.id)
    try {
      await api.seller.decideAdminRequest(storeId, request.id, status)
      await reload()
      toast(status === 'approved' ? t('dash.approve') : t('dash.reject'))
    } catch (cause) {
      toast(err(cause), 'danger')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section className="card stack">
      <h2 className="h3">{t('dash.storeAdminRequests')}</h2>
      {error && <p className="notice notice-danger" role="alert">{error}</p>}
      {!error && !requests.length && <p className="muted">{t('dash.empty')}</p>}
      <ul className="plain-list">{requests.map((request) => <li key={request.id}>
        <span><strong>{request.name || request.email}</strong><br /><span dir="ltr">{request.email}</span><br /><span className="muted">{request.is_verified ? t('dash.verified') : t('auth.verifyTitle')}</span></span>
        <span className="row"><Button size="sm" disabled={!request.is_verified} busy={busyId === request.id} onClick={() => decide(request, 'approved')}>{t('dash.approve')}</Button><Button size="sm" variant="danger" busy={busyId === request.id} onClick={() => decide(request, 'rejected')}>{t('dash.reject')}</Button></span>
      </li>)}</ul>
    </section>
  )
}

function StorePanel({ store, isOwner }) {
  const { t, bizLabel, err } = useI18n()
  const toast = useToast()
  const { reloadStores, select } = useSeller()
  const [modal, setModal] = useState(null)
  const url = `${location.origin}/store/${store.id}`
  const canUpdate = store.permissions?.includes('store.update')
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
        {(canUpdate || isOwner) && <div className="row">
          {canUpdate && <Button size="sm" onClick={() => setModal('edit')}>{t('s.editStore')}</Button>}
          {isOwner && <Button size="sm" onClick={() => setModal('create')}>{t('s.newStore')}</Button>}
        </div>}
      </div>
      <div className="row">
        <span className="muted">{t('s.publicLink')}</span>
        <a href={url} target="_blank" rel="noreferrer" dir="ltr">{url}</a>
        <Button size="sm" onClick={async () => toast((await copyText(url)) ? t('copied') : t('err.generic'))}>{t('copy')}</Button>
      </div>
      {modal && (
        <Modal title={modal === 'edit' ? t('s.editStore') : t('s.newStore')} onClose={() => setModal(null)}>
          <StoreForm key={modal} store={modal === 'edit' ? store : null} onSaved={saved} onCancel={() => setModal(null)} />
          {modal === 'edit' && isOwner && (
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
  const { user } = useAuth()
  const { store, reloadStores, select } = useSeller()
  const isOwner = user?.role === 'store_owner' || user?.role === 'god'
  useSeo({ title: `${t('s.overview')} | NAVA` })
  const data = useAsync(() => (store ? Promise.all([api.seller.orders(store.id), api.seller.products(store.id), api.seller.conversations(store.id)]) : null), [store?.id])

  if (!store) {
    if (!isOwner) return <div className="page-narrow"><Empty title={t('dash.pendingTitle')} hint={t('dash.pendingBody')} /></div>
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
      <StorePanel store={store} isOwner={isOwner} />
      {isOwner && <StoreAdminRequests storeId={store.id} />}
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
