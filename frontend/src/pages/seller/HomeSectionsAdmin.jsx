import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { HomeSection, sectionStyle } from '../../components/HomeSections'
import { Async, Badge, Button, ConfirmButton, Empty, Field, Modal, Switch, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { groupBusinessTypes } from '../../lib/businessGroups'
import { useAsync, useBusinessTypes, useSeo } from '../../lib/hooks'
import { LOCALES, useI18n } from '../../lib/i18n'
import { cx } from '../../lib/util'

const COLOR_PRESETS = ['#f2f7f6', '#fff4d6', '#ffe3e0', '#e2f0ff', '#e6f7e9', '#efe6ff', '#fde8f3', '#0f2530']
const HEX = /^#[0-9a-fA-F]{6}$/
const EMPTY = { title: '', titles: {}, kind: 'stores', business_types: [], background_color: '#f2f7f6', item_limit: 12, is_active: true }

function toForm(section) {
  return section ? {
    title: section.title,
    titles: { ...(section.titles || {}) },
    kind: section.kind,
    business_types: [...section.business_types],
    background_color: section.background_color,
    item_limit: section.item_limit,
    is_active: section.is_active,
  } : { ...EMPTY, titles: {}, business_types: [] }
}

function TypePicker({ types, value, onChange }) {
  const { t, num, bizLabel } = useI18n()
  const groups = useMemo(() => groupBusinessTypes(types.map((type) => type.slug)), [types])
  const labels = useMemo(() => Object.fromEntries(types.map((type) => [type.slug, bizLabel(type.slug, type.label)])), [types, bizLabel])
  const selected = new Set(value)
  const toggle = (slug) => onChange(selected.has(slug) ? value.filter((item) => item !== slug) : [...value, slug])
  const setGroup = (slugs, on) => onChange(on ? [...new Set([...value, ...slugs])] : value.filter((slug) => !slugs.includes(slug)))

  return (
    <div className="hs-groups" role="group" aria-label={t('homeSec.f.types')}>
      {groups.map((group) => {
        const all = group.slugs.every((slug) => selected.has(slug))
        return (
          <div className="hs-group" key={group.id}>
            <div className="hs-group-head">
              <strong>{t(`bizGroup.${group.id}`)}</strong>
              <Button size="sm" onClick={() => setGroup(group.slugs, !all)}>{all ? t('homeSec.f.clear') : t('homeSec.f.selectAll')}</Button>
            </div>
            <div className="hs-types">
              {group.slugs.map((slug) => (
                <label className="hs-type" key={slug}>
                  <input type="checkbox" checked={selected.has(slug)} onChange={() => toggle(slug)} />
                  <span>{labels[slug]}</span>
                </label>
              ))}
            </div>
          </div>
        )
      })}
      <p className="field-hint" aria-live="polite">{t('homeSec.f.typesCount', { n: num(value.length) })}</p>
    </div>
  )
}

function ColorPicker({ value, onChange }) {
  const { t } = useI18n()
  const [text, setText] = useState(value)
  const typedInvalid = !HEX.test(text)
  const apply = (next) => { setText(next); if (HEX.test(next)) onChange(next.toLowerCase()) }
  return (
    <div className="hs-colors">
      {COLOR_PRESETS.map((color) => (
        <button type="button" key={color} className="hs-swatch" style={{ background: color }} aria-label={color} aria-pressed={value.toLowerCase() === color} onClick={() => apply(color)} />
      ))}
      <input type="color" aria-label={t('homeSec.f.color')} value={HEX.test(value) ? value : '#f2f7f6'} onChange={(event) => apply(event.target.value)} />
      <input type="text" aria-label={t('homeSec.f.colorHex')} aria-invalid={typedInvalid ? true : undefined} value={text} maxLength={7} spellCheck={false} onChange={(event) => apply(event.target.value.trim())} onBlur={() => setText(value)} />
    </div>
  )
}

function SectionForm({ section, types, onSaved, onClose }) {
  const { t, locale, err } = useI18n()
  const toast = useToast()
  const [form, setForm] = useState(() => toForm(section))
  const [busy, setBusy] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const set = (patch) => setForm((current) => ({ ...current, ...patch }))

  const found = {}
  if (!form.title.trim()) found.title = t('homeSec.err.title')
  if (!form.business_types.length) found.types = t('homeSec.err.types')
  const errors = submitted ? found : {}

  const submit = async (event) => {
    event.preventDefault()
    setSubmitted(true)
    if (Object.keys(found).length) return
    const payload = {
      title: form.title.trim(),
      titles: Object.fromEntries(Object.entries(form.titles).map(([code, text]) => [code, text.trim()]).filter(([, text]) => text)),
      kind: form.kind,
      business_types: form.business_types,
      background_color: form.background_color.toLowerCase(),
      item_limit: Math.min(24, Math.max(1, Number(form.item_limit) || 12)),
      is_active: form.is_active,
    }
    setBusy(true)
    try {
      const saved = section ? await api.admin.homeSections.update(section.id, payload) : await api.admin.homeSections.create(payload)
      toast(t('homeSec.saved'))
      onSaved(saved)
    } catch (error) {
      toast(err(error), 'danger')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={section ? t('homeSec.form.edit') : t('homeSec.form.create')} onClose={onClose} className="hs-modal">
      <form className="hs-form" onSubmit={submit} noValidate>
        <Field label={t('homeSec.f.title')} hint={t('homeSec.f.titleHint')} error={errors.title}>
          <input data-autofocus maxLength={120} value={form.title} onChange={(event) => set({ title: event.target.value })} />
        </Field>

        <details className="hs-translations">
          <summary>{t('homeSec.f.translations')}</summary>
          <div className="stack">
            {LOCALES.map((item) => (
              <Field key={item.code} label={item.name}>
                <input dir={item.dir} lang={item.code} maxLength={120} value={form.titles[item.code] || ''} onChange={(event) => set({ titles: { ...form.titles, [item.code]: event.target.value } })} />
              </Field>
            ))}
          </div>
        </details>

        <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
          <legend style={{ fontWeight: 600, fontSize: '.92rem', marginBottom: 6 }}>{t('homeSec.f.kind')}</legend>
          <div className="hs-kind">
            {['stores', 'products'].map((kind) => (
              <label key={kind}><input type="radio" name="hs-kind" checked={form.kind === kind} onChange={() => set({ kind })} />{t(`homeSec.kind.${kind}`)}</label>
            ))}
          </div>
        </fieldset>

        <div className="field">
          <span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.types')}</span>
          <TypePicker types={types} value={form.business_types} onChange={(business_types) => set({ business_types })} />
          {errors.types && <p className="field-error" role="alert">{errors.types}</p>}
        </div>

        <div className="field">
          <span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.color')}</span>
          <ColorPicker value={form.background_color} onChange={(background_color) => set({ background_color })} />
        </div>

        <Field label={t('homeSec.f.limit')} hint={t('homeSec.f.limitHint')}>
          <input type="number" inputMode="numeric" min={1} max={24} value={form.item_limit} onChange={(event) => set({ item_limit: event.target.value })} onBlur={() => set({ item_limit: Math.min(24, Math.max(1, Math.round(Number(form.item_limit)) || 12)) })} />
        </Field>

        <div className="hs-sample" style={sectionStyle(HEX.test(form.background_color) ? form.background_color : '#f2f7f6')} aria-label={t('homeSec.f.sample')}>
          <strong>{form.titles[locale]?.trim() || form.title.trim() || t('homeSec.f.sampleTitle')}</strong>
          <div className="hs-sample-cards" aria-hidden="true"><span /><span /><span /><span /></div>
        </div>

        <div className="row"><span>{t('homeSec.f.active')}</span><Switch checked={form.is_active} label={t('homeSec.f.active')} onChange={(is_active) => set({ is_active })} /></div>

        <div className="hs-form-actions">
          <Button onClick={onClose}>{t('cancel')}</Button>
          <Button type="submit" variant="primary" busy={busy}>{t('save')}</Button>
        </div>
      </form>
    </Modal>
  )
}

function PreviewModal({ section, types, onClose }) {
  const { t, locale } = useI18n()
  const state = useAsync(() => api.admin.homeSections.preview(section.id), [section.id])
  return (
    <Modal title={t('homeSec.previewTitle', { title: section.titles?.[locale] || section.title })} onClose={onClose} className="hs-modal">
      <div className="hs-preview">
        <Async state={state}>{(data) => (data.items?.length ? <HomeSection section={data} types={types} /> : <Empty title={t('homeSec.previewEmpty')} />)}</Async>
      </div>
    </Modal>
  )
}

export default function HomeSectionsAdmin() {
  const { t, num, locale, err, bizLabel } = useI18n()
  const toast = useToast()
  const types = useBusinessTypes()
  const state = useAsync(() => api.admin.homeSections.list(), [])
  const [editing, setEditing] = useState(null)
  const [previewing, setPreviewing] = useState(null)
  const [busyId, setBusyId] = useState(null)
  useSeo({ title: `${t('homeSec.title')} | NAVA` })

  const run = async (id, action) => {
    setBusyId(id)
    try {
      await action()
      await state.reload()
    } catch (error) {
      toast(err(error), 'danger')
    } finally {
      setBusyId(null)
    }
  }

  const move = (sections, index, step) => {
    const ids = sections.map((section) => section.id)
    const target = index + step
    if (target < 0 || target >= ids.length) return
    ;[ids[index], ids[target]] = [ids[target], ids[index]]
    run('order', () => api.admin.homeSections.reorder(ids))
  }

  return (
    <main className="wrap page-narrow hs-admin">
      <header className="page-head"><h1>{t('homeSec.title')}</h1></header>
      <p className="muted">{t('homeSec.lead')}</p>
      <div className="row between">
        <Link className="btn" to="/seller/platform">{t('homeSec.back')}</Link>
        <Button variant="primary" onClick={() => setEditing('new')}>{t('homeSec.new')}</Button>
      </div>

      <Async state={state}>{(sections) => (sections.length === 0
        ? <Empty title={t('homeSec.empty')} />
        : (
          <ul className="hs-admin-list">
            {sections.map((section, index) => {
              const names = section.business_types.slice(0, 3).map((slug) => bizLabel(slug, types.find((type) => type.slug === slug)?.label)).join('، ')
              return (
                <li key={section.id} className={cx('hs-admin-item', !section.is_active && 'is-off')}>
                  <span className="hs-chip" style={{ background: section.background_color }} aria-hidden="true" />
                  <div className="hs-admin-main">
                    <strong>{section.titles?.[locale] || section.title}</strong>
                    <span className="hs-admin-meta">
                      <Badge tone={section.kind === 'stores' ? 'info' : 'ok'}>{t(`homeSec.kind.${section.kind}`)}</Badge>
                      <Badge tone={section.is_active ? 'ok' : 'neutral'}>{section.is_active ? t('homeSec.visible') : t('homeSec.hidden')}</Badge>
                      <span>{t('homeSec.summary', { n: num(section.business_types.length), limit: num(section.item_limit) })}</span>
                    </span>
                    <span className="muted" style={{ fontSize: '.88rem' }}>{names}{section.business_types.length > 3 ? '…' : ''}</span>
                  </div>
                  <div className="hs-admin-actions">
                    <Button size="sm" aria-label={`${t('homeSec.moveUp')}: ${section.title}`} title={t('homeSec.moveUp')} disabled={index === 0 || busyId === 'order'} onClick={() => move(sections, index, -1)}>↑</Button>
                    <Button size="sm" aria-label={`${t('homeSec.moveDown')}: ${section.title}`} title={t('homeSec.moveDown')} disabled={index === sections.length - 1 || busyId === 'order'} onClick={() => move(sections, index, 1)}>↓</Button>
                    <Button size="sm" onClick={() => setPreviewing(section)}>{t('homeSec.preview')}</Button>
                    <Button size="sm" onClick={() => setEditing(section)}>{t('edit')}</Button>
                    <ConfirmButton size="sm" variant="danger" busy={busyId === section.id} onConfirm={() => run(section.id, async () => { await api.admin.homeSections.remove(section.id); toast(t('homeSec.removed')) })}>{t('delete')}</ConfirmButton>
                  </div>
                </li>
              )
            })}
          </ul>
        ))}
      </Async>

      {editing && (
        <SectionForm
          section={editing === 'new' ? null : editing}
          types={types}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); state.reload() }}
        />
      )}
      {previewing && <PreviewModal section={previewing} types={types} onClose={() => setPreviewing(null)} />}
    </main>
  )
}
