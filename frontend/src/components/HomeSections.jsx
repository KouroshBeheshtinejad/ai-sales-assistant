import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useBusinessTypes, useHomeSections } from '../lib/hooks'
import { useI18n } from '../lib/i18n'
import { readableColor } from '../lib/storeTheme'
import { cx } from '../lib/util'
import { ProductVisual, StockBadge } from './ProductCard'
import { Icon, Swatch } from './ui'

export function sectionStyle(color) {
  const safe = /^#[0-9a-f]{6}$/i.test(color || '') ? color : '#f2f7f6'
  return { '--sec-bg': safe, '--sec-ink': readableColor(safe) }
}

export function sectionTitle(section, locale) {
  return section.titles?.[locale] || section.title
}

export function Rail({ label, children, count }) {
  const { t, meta } = useI18n()
  const track = useRef(null)
  const [edge, setEdge] = useState({ start: true, end: true, overflow: false })

  const update = useCallback(() => {
    const el = track.current
    if (!el) return
    const max = el.scrollWidth - el.clientWidth
    const position = Math.abs(el.scrollLeft)
    setEdge((current) => {
      const next = { start: position <= 2, end: position >= max - 2, overflow: max > 2 }
      return current.start === next.start && current.end === next.end && current.overflow === next.overflow ? current : next
    })
  }, [])

  useEffect(() => {
    const el = track.current
    if (!el) return undefined
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(update)
    observer?.observe(el)
    window.addEventListener('resize', update)
    update()
    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', update)
    }
  }, [update, count])

  const go = (direction) => {
    const el = track.current
    if (!el) return
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const sign = meta.dir === 'rtl' ? -1 : 1
    el.scrollBy({ left: direction * sign * Math.max(200, el.clientWidth * 0.85), behavior: reduce ? 'auto' : 'smooth' })
  }

  return (
    <div className={cx('hs-rail', edge.overflow && 'is-scrollable', edge.start && 'at-start', edge.end && 'at-end')}>
      <button type="button" className="hs-arrow hs-prev" aria-label={t('homeSec.prev')} tabIndex={-1} disabled={edge.start} onClick={() => go(-1)}><Icon name="chevron" size={22} /></button>
      <ul className="hs-track" ref={track} tabIndex={0} aria-label={label} onScroll={update}>{children}</ul>
      <button type="button" className="hs-arrow hs-next" aria-label={t('homeSec.next')} tabIndex={-1} disabled={edge.end} onClick={() => go(1)}><Icon name="chevron" size={22} /></button>
    </div>
  )
}

function RailStore({ store, types }) {
  const { t, num, bizLabel } = useI18n()
  const label = bizLabel(store.business_type, types.find((x) => x.slug === store.business_type)?.label)
  return (
    <li className="store-card hs-item">
      {store.logo_url
        ? <img className="store-mark" src={store.logo_url} alt="" loading="lazy" />
        : <Swatch className="store-mark" seed={store.name} label={store.name} />}
      <div className="store-card-body">
        <h3><Link className="cover-link" to={`/store/${store.id}`}>{store.name}</Link></h3>
        <p className="muted">{label} · {t('landing.productsCount', { n: num(store.product_count) })}</p>
        {store.description && <p className="clamp">{store.description}</p>}
        <span className="store-card-cta">{t('landing.visit')}<Icon name="arrow" size={16} className="flip-rtl" /></span>
      </div>
    </li>
  )
}

function RailProduct({ product }) {
  const { t, money } = useI18n()
  return (
    <li className="mini-product hs-item">
      <div className="mini-media"><ProductVisual product={product} /></div>
      <div className="mini-body">
        <h3><Link className="cover-link" to={`/store/${product.store_id}/product/${product.id}`}>{product.name}</Link></h3>
        <p className="muted">{t('landing.by', { store: product.store_name })}</p>
        <div className="product-meta">
          <strong className="price">{money(product.price)}</strong>
          <StockBadge stock={product.stock} />
        </div>
      </div>
    </li>
  )
}

export function HomeSection({ section, types = [] }) {
  const { locale } = useI18n()
  const title = sectionTitle(section, locale)
  const items = section.items || []
  const titleId = `home-sec-${section.id}`
  if (!items.length) return null
  return (
    <section className="home-sec" style={sectionStyle(section.background_color)} aria-labelledby={titleId}>
      <div className="wrap">
        <h2 id={titleId}>{title}</h2>
        <Rail label={title} count={items.length}>
          {section.kind === 'products'
            ? items.map((product) => <RailProduct key={product.id} product={product} />)
            : items.map((store) => <RailStore key={store.id} store={store} types={types} />)}
        </Rail>
      </div>
    </section>
  )
}

export default function HomeSections() {
  const { sections } = useHomeSections()
  const types = useBusinessTypes()
  return sections.map((section) => <HomeSection key={section.id} section={section} types={types} />)
}
