import { useEffect, useMemo, useRef, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import ProductCard from '../components/ProductCard'
import { Check, Empty, Icon, Swatch } from '../components/ui'
import { useBusinessTypes } from '../lib/hooks'
import { useI18n } from '../lib/i18n'

function CategoryTabs({ categories, categoryId, onSelect, label }) {
  const { t, meta } = useI18n()
  const tabsRef = useRef(null)
  const [showScrollControls, setShowScrollControls] = useState(false)

  useEffect(() => {
    const tabs = tabsRef.current
    if (!tabs) return undefined
    const updateOverflow = () => setShowScrollControls(tabs.scrollWidth > tabs.clientWidth + 1)
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(updateOverflow)
    observer?.observe(tabs)
    window.addEventListener('resize', updateOverflow)
    updateOverflow()
    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', updateOverflow)
    }
  }, [categories.length])

  const scroll = (direction) => {
    const tabs = tabsRef.current
    if (tabs) tabs.scrollBy({ left: direction * Math.max(180, tabs.clientWidth * 0.75), behavior: 'smooth' })
  }

  return (
    <div className="store-category-rail">
      {showScrollControls && <button type="button" className="store-category-arrow" aria-label={t('shop.scrollLeft')} title={t('shop.scrollLeft')} onClick={() => scroll(-1)}><Icon name="chevron" className="scroll-left" /></button>}
      <div className="store-category-tabs" ref={tabsRef} dir={meta.dir} role="group" aria-label={label}>
        <button type="button" className={categoryId === '' ? 'on' : ''} aria-pressed={categoryId === ''} onClick={() => onSelect('')}>{t('shop.categoryAll')}</button>
        {categories.map((category) => <button type="button" key={category.id} className={categoryId === category.id ? 'on' : ''} aria-pressed={categoryId === category.id} onClick={() => onSelect(category.id)}>{category.name}</button>)}
      </div>
      {showScrollControls && <button type="button" className="store-category-arrow" aria-label={t('shop.scrollRight')} title={t('shop.scrollRight')} onClick={() => scroll(1)}><Icon name="chevron" className="scroll-right" /></button>}
    </div>
  )
}

export default function StoreHome() {
  const { shop, ask } = useOutletContext()
  const { t, bizLabel } = useI18n()
  const types = useBusinessTypes()
  const [query, setQuery] = useState('')
  const [inStockOnly, setInStockOnly] = useState(false)
  const [categoryId, setCategoryId] = useState('')
  const { store, products } = shop.catalog

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return products.filter((p) => (!inStockOnly || p.stock > 0) && (!categoryId || (p.category_ids || []).includes(categoryId)) && (!needle || `${p.name} ${p.description || ''}`.toLowerCase().includes(needle)))
  }, [products, query, inStockOnly, categoryId])

  const typeLabel = bizLabel(store.business_type, types.find((x) => x.slug === store.business_type)?.label)

  return (
    <>
      <section className="store-hero">
        {store.logo_url
          ? <img className="store-mark store-logo" src={store.logo_url} alt={store.name} />
          : <Swatch className="store-mark" seed={store.name} label={store.name} />}
        <div>
          <p className="muted">{typeLabel}</p>
          <h1>{store.name}</h1>
          {store.description && <p className="lead">{store.description}</p>}
        </div>
      </section>

      <div className="toolbar">
        <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('shop.search')} aria-label={t('shop.search')} />
        <Check label={t('shop.inStockOnly')} checked={inStockOnly} onChange={(e) => setInStockOnly(e.target.checked)} />
        <span className="muted" aria-live="polite">{t('shop.count', { n: visible.length })}</span>
      </div>

      {!!store.categories?.length && <CategoryTabs categories={store.categories} categoryId={categoryId} onSelect={setCategoryId} label={t('shop.categories')} />}

      {visible.length ? (
        <div className="product-grid">
          {visible.map((product) => <ProductCard key={product.id} product={product} storeId={store.id} shop={shop} onAsk={ask} />)}
        </div>
      ) : (
        <Empty title={t('shop.empty')} />
      )}
    </>
  )
}
