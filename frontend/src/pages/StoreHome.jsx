import { useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import ProductCard from '../components/ProductCard'
import { Check, Empty, Swatch } from '../components/ui'
import { useBusinessTypes } from '../lib/hooks'
import { useI18n } from '../lib/i18n'

export default function StoreHome() {
  const { shop, ask } = useOutletContext()
  const { t, bizLabel } = useI18n()
  const types = useBusinessTypes()
  const [query, setQuery] = useState('')
  const [inStockOnly, setInStockOnly] = useState(false)
  const { store, products } = shop.catalog

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return products.filter((p) => (!inStockOnly || p.stock > 0) && (!needle || `${p.name} ${p.description || ''}`.toLowerCase().includes(needle)))
  }, [products, query, inStockOnly])

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
