import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import ProductCard from '../components/ProductCard'
import { Check, Empty, Icon, Swatch } from '../components/ui'
import { useAuth } from '../lib/auth'
import { api } from '../lib/api'
import { useBusinessTypes } from '../lib/hooks'
import { useI18n } from '../lib/i18n'

function StarRating({ value, interactive = false, onChange = null, size = 'md' }) {
  const stars = [1, 2, 3, 4, 5]
  return (
    <div className={`star-row ${size} ${interactive ? 'interactive' : ''}`} aria-label={interactive ? 'Select rating' : `Rating ${value} out of 5`}>
      {stars.map((star) => (
        <button
          key={star}
          type="button"
          className={star <= value ? 'star on' : 'star'}
          aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
          disabled={!interactive}
          onClick={() => interactive && onChange?.(star)}
        >
          ★
        </button>
      ))}
    </div>
  )
}

function ReviewCard({ review }) {
  const initials = (review.user_name || 'C')
    .split(/\s+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
  return (
    <article className="review-card">
      <div className="review-head">
        <div className="review-avatar">{initials}</div>
        <div>
          <strong>{review.user_name || 'Customer'}</strong>
          <small>{review.created_at ? new Date(review.created_at).toLocaleDateString() : ''}</small>
        </div>
      </div>
      <div className="review-meta-row">
        <StarRating value={review.rating} />
        {review.product_name && <span className="review-product-tag">{review.product_name}</span>}
      </div>
      {review.title && <h4>{review.title}</h4>}
      <p>{review.comment}</p>
      {review.replies?.length > 0 && (
        <div className="review-replies">
          {review.replies.map((reply) => (
            <div key={reply.id} className="review-reply">
              <div className="review-reply-head">
                <span>{reply.user_name || 'Store reply'}</span>
                <small>{reply.created_at ? new Date(reply.created_at).toLocaleDateString() : ''}</small>
              </div>
              <p>{reply.comment}</p>
            </div>
          ))}
        </div>
      )}
    </article>
  )
}

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
  const { isAuthed } = useAuth()
  const types = useBusinessTypes()
  const [query, setQuery] = useState('')
  const [inStockOnly, setInStockOnly] = useState(false)
  const [categoryId, setCategoryId] = useState('')
  const [reviews, setReviews] = useState({ reviews: [], average_rating: 0, reviews_count: 0, store_name: '' })
  const [reviewsLoading, setReviewsLoading] = useState(false)
  const [reviewSubmitting, setReviewSubmitting] = useState(false)
  const [reviewError, setReviewError] = useState('')
  const [reviewDraft, setReviewDraft] = useState({ title: '', comment: '', rating: 5 })
  const { store, products } = shop.catalog

  const averageStars = Number((store.average_rating ?? reviews.average_rating) || 0)
  const stars = Array.from({ length: 5 }, (_, index) => index < Math.round(averageStars))

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return products.filter((p) => (!inStockOnly || p.stock > 0) && (!categoryId || (p.category_ids || []).includes(categoryId)) && (!needle || `${p.name} ${p.description || ''}`.toLowerCase().includes(needle)))
  }, [products, query, inStockOnly, categoryId])

  const typeLabel = bizLabel(store.business_type, types.find((x) => x.slug === store.business_type)?.label)

  useEffect(() => {
    if (!store?.id) return undefined
    let active = true
    setReviewsLoading(true)
    api.storeReviews(store.id)
      .then((data) => {
        if (active) setReviews(data || { reviews: [], average_rating: 0, reviews_count: 0, store_name: store.name })
      })
      .catch(() => {
        if (active) setReviews({ reviews: [], average_rating: 0, reviews_count: 0, store_name: store.name })
      })
      .finally(() => { if (active) setReviewsLoading(false) })
    return () => { active = false }
  }, [store?.id, store?.name])

  const submitReview = async (event) => {
    event.preventDefault()
    if (!isAuthed) return
    if (!reviewDraft.comment.trim()) {
      setReviewError('Please write a review comment.');
      return
    }
    setReviewError('')
    setReviewSubmitting(true)
    try {
      await api.submitReview(store.id, {
        rating: reviewDraft.rating,
        title: reviewDraft.title.trim() || undefined,
        comment: reviewDraft.comment.trim(),
      })
      setReviewDraft({ title: '', comment: '', rating: 5 })
      const next = await api.storeReviews(store.id)
      setReviews(next || { reviews: [], average_rating: 0, reviews_count: 0, store_name: store.name })
    } catch (error) {
      setReviewError(error.message || 'Could not submit your review.')
    } finally {
      setReviewSubmitting(false)
    }
  }

  return (
    <>
      <section className="store-hero">
        {store.logo_url
          ? <img className="store-mark store-logo" src={store.logo_url} alt={store.name} />
          : <Swatch className="store-mark" seed={store.name} label={store.name} />}
        <div>
          <p className="muted">{typeLabel}</p>
          <h1>{store.name}</h1>
          <div className="store-rating-inline" aria-label={`${averageStars || 0} out of 5 stars`}>
            {stars.map((filled, idx) => <span key={idx} className={filled ? 'filled' : ''}>★</span>)}
            <span>{averageStars ? Number(averageStars).toFixed(1) : '0.0'} ({reviews.reviews_count || store.reviews_count || 0})</span>
          </div>
          {store.description && <p className="lead">{store.description}</p>}
        </div>
      </section>

      {(store.contact_phone || store.address || store.location_name || store.store_hours || store.location_url) && (
        <section className="store-info-panel">
          <div className="store-info-header">
            <h2>{t('shop.storeInfo')}</h2>
            {store.location_url && <a href={store.location_url} target="_blank" rel="noreferrer" className="btn btn-sm btn-secondary">{t('shop.location')}</a>}
          </div>
          <div className="store-info-grid">
            {store.contact_phone && <div><strong>{t('shop.phone')}</strong><p dir="ltr">{store.contact_phone}</p></div>}
            {store.address && <div><strong>{t('shop.address')}</strong><p>{store.address}</p></div>}
            {store.location_name && <div><strong>{t('shop.location')}</strong><p>{store.location_name}</p></div>}
            {store.store_hours && <div><strong>{t('shop.hours')}</strong><p>{store.store_hours}</p></div>}
          </div>
        </section>
      )}

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

      <section className="review-panel">
        <div className="review-summary-row">
          <div>
            <p className="muted">{t('shop.reviews')}</p>
            <h3>{reviews.reviews_count || store.reviews_count || 0} {t('shop.reviews')}</h3>
          </div>
          <div className="review-rating-block">
            <StarRating value={Math.round(averageStars || 0)} />
            <strong>{averageStars ? Number(averageStars).toFixed(1) : '0.0'}</strong>
          </div>
        </div>

        {!isAuthed ? (
          <div className="review-login-card">
            <p>{t('shop.loginToReview')}</p>
            <Link className="btn btn-primary" to="/login">{t('nav.login')}</Link>
          </div>
        ) : (
          <form className="review-form" onSubmit={submitReview}>
            <div className="review-form-head">
              <h4>{t('shop.writeReview')}</h4>
              <StarRating value={reviewDraft.rating} interactive onChange={(value) => setReviewDraft((prev) => ({ ...prev, rating: value }))} />
            </div>
            <input value={reviewDraft.title} onChange={(e) => setReviewDraft((prev) => ({ ...prev, title: e.target.value }))} placeholder={t('shop.reviewTitle')} maxLength={120} />
            <textarea value={reviewDraft.comment} onChange={(e) => setReviewDraft((prev) => ({ ...prev, comment: e.target.value }))} placeholder={t('shop.reviewPlaceholder')} rows={5} maxLength={2000} />
            {reviewError && <p className="review-error">{reviewError}</p>}
            <button type="submit" className="btn btn-primary" disabled={reviewSubmitting}>
              {reviewSubmitting ? t('loading') : t('shop.reviewSubmit')}
            </button>
          </form>
        )}

        <div className="review-list">
          {reviewsLoading ? <p className="muted">{t('loading')}</p> : reviews.reviews.length ? reviews.reviews.map((review) => <ReviewCard key={review.id} review={review} />) : <p className="muted">{t('shop.noReviews')}</p>}
        </div>
      </section>
    </>
  )
}
