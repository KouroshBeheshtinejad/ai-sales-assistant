import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { HomeSection } from '../../components/HomeSections'
import { Async, Badge, Button, ConfirmButton, Empty, Field, Modal, Switch, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { groupBusinessTypes } from '../../lib/businessGroups'
import { useAsync, useBusinessTypes, useSeo } from '../../lib/hooks'
import { LOCALES, useI18n } from '../../lib/i18n'
import { CARD_STYLES, EDGES, LOOKS, PATTERNS, SECTION_ICONS, isHex, sectionStyle } from '../../lib/sectionLook'
import { cx } from '../../lib/util'

const COLOR_PRESETS = ['#f2f7f6', '#fff4d6', '#ffe3e0', '#e2f0ff', '#e6f7e9', '#efe6ff', '#fde8f3', '#0f2530']
const HEX = /^#[0-9a-fA-F]{6}$/
const MAX_PINNED = 24
const EMPTY = {
  title: '', subtitle: '', titles: {}, subtitles: {}, kind: 'stores', business_types: [], pinned: [], fill_random: true,
  background_color: '#f2f7f6', background_color_2: '', pattern: 'none', edge: 'straight', card_style: 'solid',
  icon: '', show_all_link: true, item_limit: 12, is_active: true,
}

function toForm(section) {
  return section ? {
    title: section.title,
    subtitle: section.subtitle || '',
    titles: { ...(section.titles || {}) },
    subtitles: { ...(section.subtitles || {}) },
    kind: section.kind,
    business_types: [...section.business_types],
    pinned: (section.pinned_items || []).map((item) => ({ ...item })),
    fill_random: section.fill_random !== false,
    background_color: section.background_color,
    background_color_2: section.background_color_2 || '',
    pattern: section.pattern || 'none',
    edge: section.edge || 'straight',
    card_style: section.card_style || 'solid',
    icon: section.icon || '',
    show_all_link: section.show_all_link !== false,
    item_limit: section.item_limit,
    is_active: section.is_active,
  } : { ...EMPTY, titles: {}, subtitles: {}, business_types: [], pinned: [] }
}

export const prunePins = (pinned, types) => pinned.filter((item) => types.includes(item.business_type))

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

function ColorPicker({ value, onChange, label }) {
  const { t } = useI18n()
  const [text, setText] = useState(value)
  const typedInvalid = !isHex(text)
  const apply = (next) => { setText(next); if (isHex(next)) onChange(next.toLowerCase()) }
  return (
    <div className="hs-colors">
      {COLOR_PRESETS.map((color) => (
        <button type="button" key={color} className="hs-swatch" style={{ background: color }} aria-label={color} aria-pressed={value.toLowerCase() === color} onClick={() => apply(color)} />
      ))}
      <input type="color" aria-label={label || t('homeSec.f.color')} value={isHex(value) ? value : '#f2f7f6'} onChange={(event) => apply(event.target.value)} />
      <input type="text" aria-label={`${label || t('homeSec.f.color')} (hex)`} aria-invalid={typedInvalid ? true : undefined} value={text} maxLength={7} spellCheck={false} onChange={(event) => apply(event.target.value.trim())} onBlur={() => setText(value)} />
    </div>
  )
}

function Choices({ name, value, options, onChange, label }) {
  return (
    <div className="hs-choices" role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <label className="hs-choice" key={option.id}>
          <input type="radio" name={name} checked={value === option.id} onChange={() => onChange(option.id)} />
          <span>{option.label}</span>
        </label>
      ))}
    </div>
  )
}

function IconPicker({ value, onChange }) {
  const { t } = useI18n()
  return (
    <div className="hs-icons" role="group" aria-label={t('homeSec.f.icon')}>
      <button type="button" className="hs-icon-btn is-none" aria-pressed={value === ''} onClick={() => onChange('')}>{t('homeSec.f.iconNone')}</button>
      {SECTION_ICONS.map((icon) => (
        <button type="button" key={icon} className="hs-icon-btn" aria-pressed={value === icon} onClick={() => onChange(icon)}>{icon}</button>
      ))}
    </div>
  )
}

function useCandidates(kind, types, query) {
  const [state, setState] = useState({ items: [], loading: false, error: false })
  const key = `${kind}|${types.join(',')}|${query}`
  useEffect(() => {
    if (!types.length) {
      setState({ items: [], loading: false, error: false })
      return undefined
    }
    let live = true
    setState((current) => ({ ...current, loading: true, error: false }))
    const timer = setTimeout(() => {
      api.admin.homeSections.candidates(kind, types, query)
        .then((data) => { if (live) setState({ items: data.items || [], loading: false, error: false }) })
        .catch(() => { if (live) setState({ items: [], loading: false, error: true }) })
    }, query ? 250 : 0)
    return () => { live = false; clearTimeout(timer) }
  }, [key])
  return state
}

const itemName = (item) => (item.store_name ? `${item.name} · ${item.store_name}` : item.name)

function PinPicker({ form, set }) {
  const { t, num, bizLabel } = useI18n()
  const [query, setQuery] = useState('')
  const found = useCandidates(form.kind, form.business_types, query.trim())
  const products = form.kind === 'products'
  const picked = new Set(form.pinned.map((item) => item.id))
  const full = form.pinned.length >= MAX_PINNED
  const limit = Math.min(24, Math.max(1, Number(form.item_limit) || 12))

  const add = (item) => {
    if (picked.has(item.id) || full) return
    set({ pinned: [...form.pinned, { id: item.id, name: item.name, store_name: products ? item.store_name : null, business_type: item.business_type, visible: true }] })
  }
  const remove = (id) => set({ pinned: form.pinned.filter((item) => item.id !== id) })
  const move = (index, step) => {
    const next = [...form.pinned]
    const target = index + step
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target], next[index]]
    set({ pinned: next })
  }
  const emptyRow = form.pinned.length === 0 && !form.fill_random

  return (
    <div className="field hs-picks">
      <span style={{ fontWeight: 600, fontSize: '.92rem' }}>{products ? t('homeSec.f.pinnedProducts') : t('homeSec.f.pinnedStores')}</span>
      <p className="field-hint">{t('homeSec.f.pinnedHint')}</p>
      {form.pinned.length > 0 && <p className="field-hint" aria-live="polite">{t('homeSec.f.pinPicked', { n: num(form.pinned.length) })}</p>}
      {form.pinned.length === 0
        ? <p className="muted">{t('homeSec.f.pinNone')}</p>
        : (
          <ul className="hs-picked">
            {form.pinned.map((item, index) => (
              <li key={`${item.business_type}-${item.id}`}>
                <span className="hs-picked-name">
                  <strong>{itemName(item)}</strong>
                  <small>{bizLabel(item.business_type)}</small>
                  {item.visible === false && <small className="field-error">{t('homeSec.f.pinHidden')}</small>}
                </span>
                <span className="hs-picked-actions">
                  <Button size="sm" aria-label={`${t('homeSec.moveUp')}: ${item.name}`} disabled={index === 0} onClick={() => move(index, -1)}>↑</Button>
                  <Button size="sm" aria-label={`${t('homeSec.moveDown')}: ${item.name}`} disabled={index === form.pinned.length - 1} onClick={() => move(index, 1)}>↓</Button>
                  <Button size="sm" aria-label={`${t('homeSec.f.pinRemove')}: ${item.name}`} onClick={() => remove(item.id)}>×</Button>
                </span>
              </li>
            ))}
          </ul>
        )}
      {form.pinned.length > limit && <p className="hs-warn" role="status">{t('homeSec.f.pinOverLimit', { n: num(limit) })}</p>}
      {full && <p className="hs-warn" role="status">{t('homeSec.f.pinLimit', { n: num(MAX_PINNED) })}</p>}
      {form.business_types.length === 0
        ? <p className="muted">{t('homeSec.f.pinNeedTypes')}</p>
        : (
          <>
            <input type="search" aria-label={products ? t('homeSec.f.pinSearchProducts') : t('homeSec.f.pinSearchStores')} placeholder={products ? t('homeSec.f.pinSearchProducts') : t('homeSec.f.pinSearchStores')} value={query} onChange={(event) => setQuery(event.target.value)} />
            {found.error && <p className="field-error" role="alert">{t('homeSec.f.pinLoadError')}</p>}
            {!found.error && !found.loading && found.items.length === 0 && <p className="muted">{t('homeSec.f.pinNoResults')}</p>}
            <ul className="hs-search-results" aria-busy={found.loading || undefined}>
              {found.items.map((item) => (
                <li key={item.id}>
                  <button type="button" className="hs-result" disabled={picked.has(item.id) || full} onClick={() => add(item)} aria-label={`${t('homeSec.f.pinAdd')}: ${itemName(item)}`}>
                    <span className="hs-picked-name"><strong>{itemName(item)}</strong><small>{bizLabel(item.business_type)}</small></span>
                    <span aria-hidden="true">{picked.has(item.id) ? '✓' : '+'}</span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      <div className="row"><span>{t('homeSec.f.fillRandom')}</span><Switch checked={form.fill_random} label={t('homeSec.f.fillRandom')} onChange={(fill_random) => set({ fill_random })} /></div>
      <p className="field-hint">{t('homeSec.f.fillRandomHint')}</p>
      {emptyRow && <p className="hs-warn" role="status">{t('homeSec.f.pinEmptyWarn')}</p>}
    </div>
  )
}

function LivePreview({ form, types }) {
  const { t } = useI18n()
  const box = useRef(null)
  useEffect(() => { if (box.current) box.current.inert = true }, [])
  const type = form.business_types[0] || 'cafe'
  const sample = (index) => (form.kind === 'products'
    ? { id: -index, name: t('homeSec.f.sampleStore'), description: '', image_url: null, price: '120000', stock: 5, store_id: -1, store_name: t('homeSec.f.sampleStore'), business_type: type }
    : { id: -index, name: t('homeSec.f.sampleStore'), description: '', logo_url: null, business_type: type, product_count: 3 })
  const picks = form.pinned.map((item) => (form.kind === 'products'
    ? { id: item.id, name: item.name, description: '', image_url: null, price: '120000', stock: 5, store_id: -1, store_name: item.store_name || '', business_type: item.business_type }
    : { id: item.id, name: item.name, description: '', logo_url: null, business_type: item.business_type, product_count: 3 }))
  const items = [...picks, ...Array.from({ length: Math.max(0, 4 - picks.length) }, (_, index) => sample(index + 1))].slice(0, 6)
  const section = {
    id: 'preview', title: form.title.trim() || t('homeSec.f.sampleTitle'), titles: {}, subtitle: form.subtitle.trim(), subtitles: {},
    kind: form.kind, business_types: form.business_types, background_color: isHex(form.background_color) ? form.background_color : '#f2f7f6',
    background_color_2: form.background_color_2, pattern: form.pattern, edge: form.edge, card_style: form.card_style,
    icon: form.icon, show_all_link: form.show_all_link, items,
  }
  return <div className="hs-live" ref={box} aria-label={t('homeSec.f.livePreview')}><HomeSection section={section} types={types} /></div>
}

function SectionForm({ section, types, onSaved, onClose }) {
  const { t, locale, err } = useI18n()
  const toast = useToast()
  const [form, setForm] = useState(() => toForm(section))
  const [busy, setBusy] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const set = (patch) => setForm((current) => ({ ...current, ...patch }))
  const gradient = form.background_color_2 !== ''
  const setTypes = (business_types) => setForm((current) => ({ ...current, business_types, pinned: prunePins(current.pinned, business_types) }))
  const setKind = (kind) => setForm((current) => (current.kind === kind ? current : { ...current, kind, pinned: [] }))
  const applyLook = (look) => set({ background_color: look.background_color, background_color_2: look.background_color_2, pattern: look.pattern, edge: look.edge, card_style: look.card_style })
  const toggleGradient = (on) => set({ background_color_2: on ? (sectionStyle(form.background_color)['--sec-ink'] === '#ffffff' ? '#1d5563' : '#ffb199') : '' })

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
      subtitle: form.subtitle.trim(),
      titles: Object.fromEntries(Object.entries(form.titles).map(([code, text]) => [code, text.trim()]).filter(([, text]) => text)),
      subtitles: Object.fromEntries(Object.entries(form.subtitles).map(([code, text]) => [code, text.trim()]).filter(([, text]) => text)),
      kind: form.kind,
      business_types: form.business_types,
      pinned_ids: form.pinned.map((item) => item.id),
      fill_random: form.fill_random,
      background_color: form.background_color.toLowerCase(),
      background_color_2: gradient && isHex(form.background_color_2) ? form.background_color_2.toLowerCase() : '',
      pattern: form.pattern,
      edge: form.edge,
      card_style: form.card_style,
      icon: form.icon,
      show_all_link: form.show_all_link,
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
        <Field label={t('homeSec.f.subtitle')}>
          <input maxLength={160} value={form.subtitle} onChange={(event) => set({ subtitle: event.target.value })} />
        </Field>

        <details className="hs-translations">
          <summary>{t('homeSec.f.translations')}</summary>
          <div className="stack">
            {LOCALES.map((item) => (
              <div className="stack" key={item.code}>
                <Field label={`${item.name} · ${t('homeSec.f.title')} `}>
                  <input dir={item.dir} lang={item.code} maxLength={120} value={form.titles[item.code] || ''} onChange={(event) => set({ titles: { ...form.titles, [item.code]: event.target.value } })} />
                </Field>
                <Field label={`${item.name} · ${t('homeSec.f.subtitle')} `}>
                  <input dir={item.dir} lang={item.code} maxLength={160} value={form.subtitles[item.code] || ''} onChange={(event) => set({ subtitles: { ...form.subtitles, [item.code]: event.target.value } })} />
                </Field>
              </div>
            ))}
          </div>
        </details>

        <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
          <legend style={{ fontWeight: 600, fontSize: '.92rem', marginBottom: 6 }}>{t('homeSec.f.kind')}</legend>
          <div className="hs-kind">
            {['stores', 'products'].map((kind) => (
              <label key={kind}><input type="radio" name="hs-kind" checked={form.kind === kind} onChange={() => setKind(kind)} />{t(`homeSec.kind.${kind}`)}</label>
            ))}
          </div>
        </fieldset>

        <div className="field">
          <span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.types')}</span>
          <TypePicker types={types} value={form.business_types} onChange={setTypes} />
          {errors.types && <p className="field-error" role="alert">{errors.types}</p>}
        </div>

        <PinPicker form={form} set={set} />

        <Field label={t('homeSec.f.limit')} hint={t('homeSec.f.limitHint')}>
          <input type="number" inputMode="numeric" min={1} max={24} value={form.item_limit} onChange={(event) => set({ item_limit: event.target.value })} onBlur={() => set({ item_limit: Math.min(24, Math.max(1, Math.round(Number(form.item_limit)) || 12)) })} />
        </Field>

        <div className="hs-section">
          <h3>{t('homeSec.f.look')}</h3>
          <div className="hs-looks" role="group" aria-label={t('homeSec.f.look')}>
            {LOOKS.map((look) => (
              <button type="button" key={look.id} className="hs-look" onClick={() => applyLook(look)}>
                <span className="hs-look-swatch" style={{ background: sectionStyle(look.background_color, look.background_color_2)['--sec-fill'] }} />
                <span>{t(`homeSec.look.${look.id}`)}</span>
              </button>
            ))}
          </div>
          <div className="field">
            <span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.color')}</span>
            <ColorPicker value={form.background_color} label={t('homeSec.f.color')} onChange={(background_color) => set({ background_color })} />
          </div>
          <div className="row"><span>{t('homeSec.f.gradient')}</span><Switch checked={gradient} label={t('homeSec.f.gradient')} onChange={toggleGradient} /></div>
          {gradient && <div className="field"><span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.color2')}</span><ColorPicker value={form.background_color_2} label={t('homeSec.f.color2')} onChange={(background_color_2) => set({ background_color_2 })} /></div>}
          <div className="field"><span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.pattern')}</span><Choices name="hs-pattern" label={t('homeSec.f.pattern')} value={form.pattern} options={PATTERNS.map((id) => ({ id, label: t(`homeSec.pattern.${id}`) }))} onChange={(pattern) => set({ pattern })} /></div>
          <div className="field"><span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.edge')}</span><Choices name="hs-edge" label={t('homeSec.f.edge')} value={form.edge} options={EDGES.map((id) => ({ id, label: t(`homeSec.edge.${id}`) }))} onChange={(edge) => set({ edge })} /></div>
          <div className="field"><span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.cards')}</span><Choices name="hs-cards" label={t('homeSec.f.cards')} value={form.card_style} options={CARD_STYLES.map((id) => ({ id, label: t(`homeSec.cards.${id}`) }))} onChange={(card_style) => set({ card_style })} /></div>
          <div className="field"><span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.icon')}</span><IconPicker value={form.icon} onChange={(icon) => set({ icon })} /></div>
          <div className="row"><span>{t('homeSec.f.showAll')}</span><Switch checked={form.show_all_link} label={t('homeSec.f.showAll')} onChange={(show_all_link) => set({ show_all_link })} /></div>
        </div>

        <div className="field">
          <span style={{ fontWeight: 600, fontSize: '.92rem' }}>{t('homeSec.f.livePreview')}</span>
          <LivePreview form={form} types={types} />
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
