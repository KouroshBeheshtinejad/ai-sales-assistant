import { useState } from 'react'
import { Link, useOutletContext, useParams } from 'react-router-dom'
import { ProductVisual, StockBadge } from '../components/ProductCard'
import { Button, Empty, Icon, useToast } from '../components/ui'
import { useBusinessTypes, useSeo } from '../lib/hooks'
import { useI18n } from '../lib/i18n'

export default function ProductPage() {
  const { shop, ask } = useOutletContext()
  const { productId } = useParams()
  const { t, num, money, err, fieldLabel, optionLabel } = useI18n()
  const toast = useToast()
  const types = useBusinessTypes()
  const [quantity, setQuantity] = useState(1)
  const [busy, setBusy] = useState(false)
  const { store, products } = shop.catalog
  const product = products.find((p) => String(p.id) === productId)

  useSeo({ title: product ? `${product.name} | ${store.name}` : undefined, description: product?.description || undefined })

  const back = <Link className="back-link" to={`/store/${store.id}`}>{t('shop.backToStore')}</Link>
  if (!product) return <>{back}<Empty title={t('shop.productNotFound')} /></>

  const fields = types.find((x) => x.slug === store.business_type)?.fields || []
  // size/color are also real columns; older rows may only have them there.
  const merged = { size: product.size, color: product.color, ...product.attributes }
  const specs = Object.entries(merged).filter(([, v]) => v !== '' && v != null && v !== false)
  const show = (value) => (value === true ? t('yes') : typeof value === 'string' ? optionLabel(value) : num(value))
  const max = Math.min(product.stock, 100)

  const add = async () => {
    setBusy(true)
    try {
      await shop.addToCart(product.id, quantity)
      toast(t('shop.added', { name: product.name }))
    } catch (error) {
      toast(err(error), 'danger')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {back}
      <article className="product-page">
        <ProductVisual product={product} className="product-hero" />
        <div className="stack">
          <h1>{product.name}</h1>
          <p className="price price-lg">{money(product.price)}</p>
          <StockBadge stock={product.stock} />
          {product.description && <p className="lead">{product.description}</p>}

          {product.stock > 0 && (
            <div className="row">
              <div className="qty" role="group" aria-label={t('shop.qty')}>
                <button type="button" disabled={quantity <= 1} aria-label={t('cart.dec', { name: product.name })} onClick={() => setQuantity((q) => q - 1)}><Icon name="minus" size={16} /></button>
                <output>{num(quantity)}</output>
                <button type="button" disabled={quantity >= max} aria-label={t('cart.inc', { name: product.name })} onClick={() => setQuantity((q) => q + 1)}><Icon name="plus" size={16} /></button>
              </div>
              <Button variant="primary" busy={busy} onClick={add}><Icon name="cart" size={18} />{t('shop.add')}</Button>
            </div>
          )}
          <Button variant="ghost" size="sm" onClick={() => ask(t('shop.askProduct', { name: product.name }))}>{t('shop.ask')}</Button>

          {specs.length > 0 && (
            <section>
              <h2 className="h3">{t('shop.attributes')}</h2>
              <dl className="specs">
                {specs.map(([name, value]) => <div key={name}><dt>{fieldLabel(fields.find((f) => f.name === name) || { name })}</dt><dd>{show(value)}</dd></div>)}
              </dl>
            </section>
          )}
        </div>
      </article>
    </>
  )
}
