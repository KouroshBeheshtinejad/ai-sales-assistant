import { useState } from 'react'
import { Async, Badge, Button, Check, ConfirmButton, Empty, Field, Modal, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { cx } from '../../lib/util'
import { useSeller } from './SellerContext'
import { NeedStore, PageHead } from './SellerLayout'

// Knowledge entries and FAQs share the same shape; only the field names differ.
const KINDS = {
  knowledge: { head: ['title', 'k.title', 255], body: ['content', 'k.content', 10000], empty: 'k.emptyKnowledge', tab: 'k.tabKnowledge' },
  faqs: { head: ['question', 'k.question', 500], body: ['answer', 'k.answer', 10000], empty: 'k.emptyFaqs', tab: 'k.tabFaqs' },
}

function EntryForm({ kind, storeId, entry, onSaved, onClose }) {
  const { t, err } = useI18n()
  const [headName, headLabel, headMax] = KINDS[kind].head
  const [bodyName, bodyLabel, bodyMax] = KINDS[kind].body
  const [form, setForm] = useState({ [headName]: entry?.[headName] || '', [bodyName]: entry?.[bodyName] || '', is_active: entry?.is_active ?? true })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (entry) await api.seller.update(storeId, kind, entry.id, form)
      else await api.seller.create(storeId, kind, form)
      await onSaved()
    } catch (e) {
      setError(err(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <Field label={t(headLabel)}><input required maxLength={headMax} value={form[headName]} onChange={(e) => setForm({ ...form, [headName]: e.target.value })} data-autofocus /></Field>
      <Field label={t(bodyLabel)}><textarea required rows={6} maxLength={bodyMax} value={form[bodyName]} onChange={(e) => setForm({ ...form, [bodyName]: e.target.value })} /></Field>
      <Check label={t('k.active')} checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
      {error && <p className="notice notice-danger" role="alert">{error}</p>}
      <div className="row">
        <Button type="submit" variant="primary" busy={busy}>{entry ? t('save') : t('create')}</Button>
        <Button onClick={onClose}>{t('cancel')}</Button>
      </div>
    </form>
  )
}

function EntryList({ kind, store }) {
  const { t, err } = useI18n()
  const toast = useToast()
  const [modal, setModal] = useState(null)
  const state = useAsync(() => api.seller.list(store.id, kind), [store.id, kind])
  const [headName] = KINDS[kind].head
  const [bodyName] = KINDS[kind].body

  const remove = async (entry) => {
    try {
      await api.seller.remove(store.id, kind, entry.id)
      state.setData(state.data.filter((e) => e.id !== entry.id))
      toast(t('deleted'))
    } catch (e) {
      toast(err(e), 'danger')
    }
  }
  const saved = async () => { toast(t('saved')); setModal(null); await state.reload() }

  return (
    <div role="tabpanel">
      <div className="row end"><Button variant="primary" onClick={() => setModal('new')}>{t('k.add')}</Button></div>
      <Async state={state}>
        {(entries) => !entries.length ? <Empty title={t(KINDS[kind].empty)} /> : (
          <ul className="list-cards">
            {entries.map((entry) => (
              <li key={entry.id} className={cx('card', !entry.is_active && 'dim')}>
                <div className="row between">
                  <h3 className="h4">{entry[headName]}</h3>
                  {!entry.is_active && <Badge>{t('inactive')}</Badge>}
                </div>
                <p className="clamp pre">{entry[bodyName]}</p>
                <div className="row">
                  <Button size="sm" onClick={() => setModal(entry)}>{t('edit')}</Button>
                  <ConfirmButton onConfirm={() => remove(entry)}>{t('delete')}</ConfirmButton>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Async>
      {modal && (
        <Modal title={modal === 'new' ? t('k.add') : t('k.editEntry')} onClose={() => setModal(null)}>
          <EntryForm kind={kind} storeId={store.id} entry={modal === 'new' ? null : modal} onSaved={saved} onClose={() => setModal(null)} />
        </Modal>
      )}
    </div>
  )
}

export default function Knowledge() {
  const { t } = useI18n()
  const { store } = useSeller()
  const [kind, setKind] = useState('knowledge')
  useSeo({ title: `${t('s.knowledge')} | NAVA` })
  if (!store) return <NeedStore />

  return (
    <>
      <PageHead title={t('s.knowledge')} />
      <p className="muted">{t('k.lead')}</p>
      <div className="tabs" role="tablist">
        {Object.entries(KINDS).map(([key, config]) => (
          <button key={key} type="button" role="tab" aria-selected={kind === key} className={cx('tab', kind === key && 'on')} onClick={() => setKind(key)}>{t(config.tab)}</button>
        ))}
      </div>
      <EntryList key={`${store.id}-${kind}`} kind={kind} store={store} />
    </>
  )
}
