import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useBusinessTypes, useHomeSections } from '../lib/hooks'
import { useI18n } from '../lib/i18n'
import { safeCards, safeEdge, safeIcon, safePattern, sectionStyle } from '../lib/sectionLook'
import { cx } from '../lib/util'
import { ProductVisual, StockBadge } from './ProductCard'
import { Icon, Swatch } from './ui'

export { sectionStyle }

export function sectionTitle(section, locale) {
  return section.titles?.[locale] || section.title
}

export function sectionSubtitle(section, locale) {
  return section.subtitles?.[locale] || section.subtitle || ''
}

export function Rail({ label, children, count }) {
  const { t, meta } = useI18n()
  const track = useRef(null)
  const drag = useRef(null)
  const wasDragged = useRef(false)
  const [dragging, setDragging] = useState(false)
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

  const startDrag = (event) => {
    if ((event.pointerType && event.pointerType !== 'mouse') || event.button !== 0) return
    drag.current = { pointerId: event.pointerId, startX: event.clientX, startScrollLeft: track.current.scrollLeft, moved: false }
    track.current.setPointerCapture?.(event.pointerId)
  }

  const moveDrag = (event) => {
    const active = drag.current
    if (!active || active.pointerId !== event.pointerId) return
    const delta = event.clientX - active.startX
    if (!active.moved && Math.abs(delta) > 4) {
      active.moved = true
      setDragging(true)
    }
    if (active.moved) {
      track.current.scrollLeft = active.startScrollLeft - delta * (meta.dir === 'rtl' ? -1 : 1)
      event.preventDefault()
    }
  }

  const endDrag = (event) => {
    if (!drag.current || drag.current.pointerId !== event.pointerId) return
    wasDragged.current = drag.current.moved
    drag.current = null
    setDragging(false)
    if (wasDragged.current) window.setTimeout(() => { wasDragged.current = false }, 0)
    update()
  }

  const suppressDraggedClick = (event) => {
    if (!wasDragged.current) return
    event.preventDefault()
    event.stopPropagation()
    wasDragged.current = false
  }

  return (
    <div className={cx('hs-rail', edge.overflow && 'is-scrollable', edge.start && 'at-start', edge.end && 'at-end')}>
      <button type="button" className="hs-arrow hs-prev" aria-label={t('homeSec.prev')} tabIndex={-1} disabled={edge.start} onClick={() => go(-1)}><Icon name="chevron" size={22} /></button>
      <ul className={cx('hs-track', dragging && 'is-dragging')} ref={track} tabIndex={0} aria-label={label} onScroll={update} onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag} onClickCapture={suppressDraggedClick}>{children}</ul>
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

const EDGE_PATHS = {
  wave: 'M0 0H1200V24C1100 8 1000 8 900 24S700 40 600 24S400 8 300 24S100 40 0 24Z',
  curve: 'M0 0H1200V40Q600 -8 0 40Z',
}

function Edge({ shape, position }) {
  if (shape === 'straight') return null
  return (
    <svg className={`hs-edge hs-edge-${position}`} viewBox="0 0 1200 48" preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <path d={EDGE_PATHS[shape]} fill="currentColor" />
    </svg>
  )
}

export function HomeSection({ section, types = [] }) {
  const { t, locale } = useI18n()
  const title = sectionTitle(section, locale)
  const subtitle = sectionSubtitle(section, locale)
  const items = section.items || []
  const titleId = `home-sec-${section.id}`
  if (!items.length) return null
  const edge = safeEdge(section.edge)
  const icon = safeIcon(section.icon)
  const slugs = (section.business_types || []).slice(0, 12)
  const showAll = section.show_all_link !== false && slugs.length > 0
  return (
    <section
      className={cx('home-sec', `hs-pattern-${safePattern(section.pattern)}`, `hs-cards-${safeCards(section.card_style)}`, edge !== 'straight' && 'has-edge')}
      style={sectionStyle(section.background_color, section.background_color_2)}
      aria-labelledby={titleId}
    >
      <Edge shape={edge} position="top" />
      <Edge shape={edge} position="bottom" />
      <div className="wrap">
        <header className="hs-head">
          <div className="hs-titles">
            {icon && <span className="hs-icon" aria-hidden="true">{icon}</span>}
            <div>
              <h2 id={titleId}>{title}</h2>
              {subtitle && <p className="hs-sub">{subtitle}</p>}
            </div>
          </div>
          {showAll && <Link className="hs-all" to={`/stores?business_type=${slugs.map(encodeURIComponent).join(',')}`}>{t('homeSec.viewAll')}<Icon name="arrow" size={16} className="flip-rtl" /></Link>}
        </header>
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
