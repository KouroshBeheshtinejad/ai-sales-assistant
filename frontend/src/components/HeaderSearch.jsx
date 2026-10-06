import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowUpRight, Package, Search, Store, X } from 'lucide-react'
import { ProductVisual } from './ProductCard'
import { Swatch } from './ui'
import { api } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { cx } from '../lib/util'

function StoreOption({ store, active, id, onChoose }) {
  const { t, num } = useI18n()
  return (
    <Link
      id={id}
      role="option"
      aria-selected={active}
      className={cx('global-search-option', active && 'is-active')}
      to={`/store/${store.id}`}
      onClick={onChoose}
    >
      {store.logo_url
        ? <img className="global-search-thumb" src={store.logo_url} alt="" loading="lazy" />
        : <Swatch className="global-search-thumb" seed={store.name} label={store.name} />}
      <span className="global-search-copy">
        <strong>{store.name}</strong>
        <small>{store.description || t('search.storeMeta', { n: num(store.product_count) })}</small>
      </span>
      <ArrowUpRight size={16} aria-hidden="true" />
    </Link>
  )
}

function ProductOption({ product, active, id, onChoose }) {
  const { t, money } = useI18n()
  return (
    <Link
      id={id}
      role="option"
      aria-selected={active}
      className={cx('global-search-option', active && 'is-active')}
      to={`/store/${product.store_id}/product/${product.id}`}
      onClick={onChoose}
    >
      <ProductVisual product={product} className="global-search-thumb" />
      <span className="global-search-copy">
        <strong>{product.name}</strong>
        <small>{t('search.productMeta', { store: product.store_name })}</small>
      </span>
      <span className="global-search-price">{money(product.price, product.currency)}</span>
    </Link>
  )
}

export default function HeaderSearch() {
  const { t } = useI18n()
  const location = useLocation()
  const navigate = useNavigate()
  const root = useRef(null)
  const input = useRef(null)
  const listId = useId()
  const [query, setQuery] = useState('')
  const [focused, setFocused] = useState(false)
  const [results, setResults] = useState({ stores: [], products: [] })
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const term = query.trim()
  const open = focused && Boolean(term)
  const options = useMemo(() => [
    ...(results.stores || []).map((item) => ({ ...item, kind: 'store', to: `/store/${item.id}` })),
    ...(results.products || []).map((item) => ({ ...item, kind: 'product', to: `/store/${item.store_id}/product/${item.id}` })),
  ], [results])

  useEffect(() => {
    if (!open) {
      setLoading(false)
      return undefined
    }
    let current = true
    setLoading(true)
    setFailed(false)
    const timer = setTimeout(() => {
      api.search(term, 4)
        .then((data) => {
          if (current) setResults({ stores: data.stores || [], products: data.products || [] })
        })
        .catch(() => {
          if (current) {
            setResults({ stores: [], products: [] })
            setFailed(true)
          }
        })
        .finally(() => { if (current) setLoading(false) })
    }, 220)
    return () => { current = false; clearTimeout(timer) }
  }, [open, term])

  useEffect(() => {
    setFocused(false)
    setActiveIndex(-1)
  }, [location.pathname, location.search])

  useEffect(() => {
    const dismissOutside = (event) => {
      if (!root.current?.contains(event.target)) setFocused(false)
    }
    document.addEventListener('pointerdown', dismissOutside)
    return () => document.removeEventListener('pointerdown', dismissOutside)
  }, [])

  useEffect(() => setActiveIndex(-1), [term, results])

  const choose = () => {
    setFocused(false)
    setActiveIndex(-1)
  }

  const onKeyDown = (event) => {
    if (event.key === 'Escape' && open) {
      event.preventDefault()
      setFocused(false)
      setActiveIndex(-1)
    } else if (event.key === 'ArrowDown' && open && options.length) {
      event.preventDefault()
      setActiveIndex((current) => Math.min(current + 1, options.length - 1))
    } else if (event.key === 'ArrowUp' && open && options.length) {
      event.preventDefault()
      setActiveIndex((current) => Math.max(current - 1, 0))
    } else if (event.key === 'Enter' && open && options[activeIndex]) {
      event.preventDefault()
      navigate(options[activeIndex].to)
      choose()
    }
  }

  const clear = () => {
    setQuery('')
    setResults({ stores: [], products: [] })
    setActiveIndex(-1)
    input.current?.focus()
  }

  let optionIndex = 0
  return (
    <div className="global-search" ref={root}>
      <form className={cx('global-search-form', open && 'is-open')} role="search" onSubmit={(event) => event.preventDefault()}>
        <Search className="global-search-icon" size={19} aria-hidden="true" />
        <label className="sr-only" htmlFor={`${listId}-input`}>{t('search.label')}</label>
        <input
          ref={input}
          id={`${listId}-input`}
          type="search"
          role="combobox"
          aria-autocomplete="list"
          aria-controls={listId}
          aria-expanded={open}
          aria-activedescendant={activeIndex >= 0 ? `${listId}-option-${activeIndex}` : undefined}
          placeholder={t('search.placeholder')}
          value={query}
          onFocus={() => setFocused(true)}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={onKeyDown}
        />
        {query && <button type="button" className="global-search-clear" aria-label={t('search.clear')} onClick={clear}><X size={16} /></button>}
      </form>
      {open && (
        <div className="global-search-panel" id={listId} role="listbox" aria-label={t('search.results')} aria-busy={loading || undefined}>
          {loading && <div className="global-search-state" role="status"><span className="spinner" />{t('search.loading')}</div>}
          {!loading && failed && <p className="global-search-state" role="status">{t('search.error')}</p>}
          {!loading && !failed && options.length === 0 && <p className="global-search-state" role="status">{t('search.empty')}</p>}
          {!loading && !failed && results.stores?.length > 0 && (
            <section className="global-search-group" role="group" aria-labelledby={`${listId}-stores`}>
              <h2 id={`${listId}-stores`}><Store size={16} aria-hidden="true" />{t('search.stores')}<span>{results.stores.length}</span></h2>
              {results.stores.map((store) => {
                const index = optionIndex++
                return <StoreOption key={store.id} store={store} id={`${listId}-option-${index}`} active={activeIndex === index} onChoose={choose} />
              })}
            </section>
          )}
          {!loading && !failed && results.products?.length > 0 && (
            <section className="global-search-group" role="group" aria-labelledby={`${listId}-products`}>
              <h2 id={`${listId}-products`}><Package size={16} aria-hidden="true" />{t('search.products')}<span>{results.products.length}</span></h2>
              {results.products.map((product) => {
                const index = optionIndex++
                return <ProductOption key={product.id} product={product} id={`${listId}-option-${index}`} active={activeIndex === index} onChoose={choose} />
              })}
            </section>
          )}
        </div>
      )}
    </div>
  )
}
