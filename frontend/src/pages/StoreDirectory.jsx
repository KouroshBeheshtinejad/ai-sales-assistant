import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Async, Empty, Field, Swatch } from '../components/ui'
import { api } from '../lib/api'
import { useAsync, useBusinessTypes, useSeo } from '../lib/hooks'
import { useI18n } from '../lib/i18n'

export default function StoreDirectory() {
  const [params] = useSearchParams()
  const businessType = params.get('business_type') || ''
  const [search, setSearch] = useState('')
  const { t, bizLabel, num } = useI18n()
  const types = useBusinessTypes()
  const type = types.find((item) => item.slug === businessType)
  const stores = useAsync(() => businessType ? api.storesByBusinessType(businessType) : Promise.resolve({ stores: [], total: 0 }), [businessType])
  const title = type ? bizLabel(type.slug, type.label) : t('landing.browseBusinesses')
  useSeo({ title: `${title} | NAVA` })

  return (
    <div className="wrap section directory-page">
      <Link className="back-link" to="/">{t('landing.backToBusinesses')}</Link>
      <div className="section-head">
        <div><h1>{title}</h1><p className="lead">{t('landing.categoryStoreCount', { n: num(stores.data?.total || 0) })}</p></div>
      </div>
      <Field label={t('landing.searchStores')}><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></Field>
      <Async state={stores}>{(data) => {
        const visible = data.stores.filter((store) => `${store.name} ${store.description || ''}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
        return visible.length ? (
          <ul className="store-grid">
            {visible.map((store) => <li key={store.id} className="store-card">
              {store.logo_url ? <img className="store-mark" src={store.logo_url} alt="" loading="lazy" /> : <Swatch className="store-mark" seed={store.name} label={store.name} />}
              <div className="store-card-body">
                <h2><Link className="cover-link" to={`/store/${store.id}`}>{store.name}</Link></h2>
                <p className="muted">{t('landing.productsCount', { n: num(store.product_count) })}</p>
                {store.description && <p className="clamp">{store.description}</p>}
                <Link className="store-card-cta" to={`/store/${store.id}`}>{t('landing.visit')}</Link>
              </div>
            </li>)}
          </ul>
        ) : <Empty title={search ? t('landing.noStoreMatches') : t('landing.categoryEmpty')} />
      }}</Async>
    </div>
  )
}