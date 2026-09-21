import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../lib/i18n'
import { Badge, Button, Icon, Swatch, useToast } from './ui'

export function StockBadge({ stock }) {
  const { t } = useI18n()
  if (stock <= 0) return <Badge tone="danger">{t('shop.outOfStock')}</Badge>
  if (stock <= 3) return <Badge tone="warn">{t('shop.lowStock', { n: stock })}</Badge>
  return <Badge tone="ok">{t('shop.inStock', { n: stock })}</Badge>
}

export default function ProductCard({ product, storeId, shop, onAsk }) {
  const { t, money, err } = useI18n()
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const soldOut = product.stock <= 0

  const add = async () => {
    setBusy(true)
    try {
      await shop.addToCart(product.id, 1)
      toast(t('shop.added', { name: product.name }))
    } catch (error) {
      toast(err(error), 'danger')
    } finally {
      setBusy(false)
    }
  }

  return (
    <article className="product">
      <Link to={`/store/${storeId}/product/${product.id}`} className="product-media" aria-label={product.name} tabIndex={-1}>
        <Swatch seed={product.name} label={product.name} />
      </Link>
      <div className="product-body">
        <h3><Link to={`/store/${storeId}/product/${product.id}`}>{product.name}</Link></h3>
        {product.description && <p className="clamp">{product.description}</p>}
        <div className="product-meta">
          <strong className="price">{money(product.price)}</strong>
          <StockBadge stock={product.stock} />
        </div>
        <div className="product-actions">
          <Button variant="primary" size="sm" busy={busy} disabled={soldOut} onClick={add}><Icon name="plus" size={16} />{t('shop.add')}</Button>
          <Button size="sm" onClick={() => onAsk(t('shop.askProduct', { name: product.name }))}>{t('shop.ask')}</Button>
        </div>
      </div>
    </article>
  )
}
