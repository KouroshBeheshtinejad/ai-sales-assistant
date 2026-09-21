import { useState } from 'react'
import { Async, Badge, Button, Check, ConfirmButton, Empty, Field, Modal, Switch, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { toLatinDigits } from '../../lib/util'
import { useSeller } from './SellerContext'
import { NeedStore, PageHead } from './SellerLayout'

function AttributeField({ definition, value, onChange }) {
  const { t, fieldLabel, optionLabel } = useI18n()
  const label = fieldLabel(definition)
  switch (definition.type) {
    case 'checkbox':
      return <Check label={label} checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
    case 'select':
      return (
        <Field label={label}>
          <select value={value ?? ''} onChange={(e) => onChange(e.target.value)}>
            <option value="">{t('select')}</option>
            {definition.options.map((option) => <option key={option} value={option}>{optionLabel(option)}</option>)}
          </select>
        </Field>
      )
    case 'textarea':
      return <Field label={label} className="full"><textarea rows={2} placeholder={definition.placeholder} value={value ?? ''} onChange={(e) => onChange(e.target.value)} /></Field>
    default:
      return <Field label={label}><input type={definition.type} step={definition.type === 'number' ? 'any' : undefined} placeholder={definition.placeholder} value={value ?? ''} onChange={(e) => onChange(e.target.value)} /></Field>
  }
}

function ProductForm({ product, store, businessType, onSaved, onClose }) {
  const { t, err, bizLabel } = useI18n()
  const fields = businessType?.fields || []
  const [form, setForm] = useState({
    name: product?.name || '',
    description: product?.description || '',
    price: product ? String(product.price) : '',
    stock: product ? String(product.stock) : '0',
    // size/color also live in real columns; keep old rows editable.
    attributes: { ...(product?.size ? { size: product.size } : {}), ...(product?.color ? { color: product.color } : {}), ...(product?.attributes || {}) },
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value })

  const submit = async (event) => {
    event.preventDefault()
    const price = Number(toLatinDigits(form.price))
    const stock = Number(toLatinDigits(form.stock))
    const next = {}
    if (!form.name.trim()) next.name = t('form.required')
    if (form.price.trim() === '' || !Number.isFinite(price) || price < 0) next.price = t('form.price')
    if (!Number.isInteger(stock) || stock < 0) next.stock = t('form.stock')
    setErrors(next)
    if (Object.keys(next).length) return

    // Start from the stored attributes so keys of a previous business type are not lost.
    const attributes = { ...form.attributes }
    for (const definition of fields) {
      const value = form.attributes[definition.name]
      if (definition.type === 'checkbox') attributes[definition.name] = Boolean(value)
      else if (value === '' || value == null) delete attributes[definition.name]
      else attributes[definition.name] = definition.type === 'number' ? Number(toLatinDigits(value)) : value
    }
    const payload = { name: form.name.trim(), description: form.description.trim() || null, price, stock, attributes }

    setBusy(true)
    setFormError('')
    try {
      if (product) await api.seller.updateProduct(product.id, payload)
      else await api.seller.createProduct({ ...payload, store_id: store.id })
      await onSaved()
    } catch (e) {
      setFormError(err(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="form-grid" onSubmit={submit} noValidate>
      <Field label={t('p.name')} error={errors.name} className="full"><input required maxLength={255} value={form.name} onChange={set('name')} data-autofocus /></Field>
      <Field label={t('p.price')} error={errors.price}><input inputMode="decimal" dir="ltr" value={form.price} onChange={set('price')} /></Field>
      <Field label={t('p.stock')} error={errors.stock}><input inputMode="numeric" dir="ltr" value={form.stock} onChange={set('stock')} /></Field>
      <Field label={t('p.desc')} className="full"><textarea rows={3} maxLength={10000} value={form.description} onChange={set('description')} /></Field>
      {fields.length > 0 && <h3 className="h4 full">{t('p.typeFields', { type: bizLabel(businessType.slug, businessType.label) })}</h3>}
      {fields.map((definition) => (
        <AttributeField key={definition.name} definition={definition} value={form.attributes[definition.name]}
          onChange={(value) => setForm((f) => ({ ...f, attributes: { ...f.attributes, [definition.name]: value } }))} />
      ))}
      {formError && <p className="notice notice-danger full" role="alert">{formError}</p>}
      <div className="row full">
        <Button type="submit" variant="primary" busy={busy}>{product ? t('save') : t('create')}</Button>
        <Button onClick={onClose}>{t('cancel')}</Button>
      </div>
    </form>
  )
}

export default function Products() {
  const { t, num, money, err } = useI18n()
  const toast = useToast()
  const { store, businessType } = useSeller()
  const [modal, setModal] = useState(null) // null | 'new' | product
  useSeo({ title: `${t('s.products')} | NAVA` })
  const state = useAsync(() => (store ? api.seller.products(store.id) : null), [store?.id])
  if (!store) return <NeedStore />

  const guard = async (action, message) => {
    try { await action(); if (message) toast(message) } catch (e) { toast(err(e), 'danger') }
  }
  const toggle = (product) => guard(async () => {
    const updated = await api.seller.updateProduct(product.id, { is_active: !product.is_active })
    state.setData(state.data.map((p) => (p.id === product.id ? updated : p)))
  })
  const remove = (product) => guard(async () => {
    await api.seller.deleteProduct(product.id)
    state.setData(state.data.filter((p) => p.id !== product.id))
  }, t('p.deleted'))
  const saved = async () => {
    toast(modal === 'new' ? t('p.created') : t('p.updated'))
    setModal(null)
    await state.reload()
  }

  return (
    <>
      <PageHead title={t('s.products')} actions={<Button variant="primary" onClick={() => setModal('new')}>{t('p.add')}</Button>} />
      <Async state={state}>
        {(products) => !products.length ? (
          <Empty title={t('p.empty')} hint={t('p.emptyHint')} action={<Button variant="primary" onClick={() => setModal('new')}>{t('p.add')}</Button>} />
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th scope="col">{t('p.name')}</th><th scope="col">{t('p.price')}</th><th scope="col">{t('p.stock')}</th><th scope="col">{t('p.status')}</th><th scope="col"><span className="sr-only">{t('edit')}</span></th></tr></thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className={p.is_active ? '' : 'dim'}>
                    <td>{p.name}</td>
                    <td>{money(p.price)}</td>
                    <td>
                      {p.stock === 0 ? <Badge tone="danger">{t('shop.outOfStock')}</Badge> : num(p.stock)}
                      {p.reserved_stock > 0 && <small>{t('p.reserved', { n: p.reserved_stock })}</small>}
                    </td>
                    <td><Switch checked={p.is_active} label={`${p.name}: ${p.is_active ? t('active') : t('inactive')}`} onChange={() => toggle(p)} /></td>
                    <td className="actions">
                      <Button size="sm" onClick={() => setModal(p)}>{t('edit')}</Button>
                      <ConfirmButton onConfirm={() => remove(p)}>{t('delete')}</ConfirmButton>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Async>
      {modal && (
        <Modal title={modal === 'new' ? t('p.add') : t('p.edit')} onClose={() => setModal(null)}>
          <ProductForm product={modal === 'new' ? null : modal} store={store} businessType={businessType} onSaved={saved} onClose={() => setModal(null)} />
        </Modal>
      )}
    </>
  )
}
