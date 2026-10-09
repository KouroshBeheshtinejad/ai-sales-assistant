import { Link, useOutletContext } from 'react-router-dom'
import StoreLocationMap from '../components/StoreLocationMap'
import { useI18n } from '../lib/i18n'

export default function StoreInformation() {
  const { shop } = useOutletContext()
  const { t } = useI18n()
  const { store } = shop.catalog
  const details = [
    store.contact_phone && [t('shop.phone'), <p dir="ltr">{store.contact_phone}</p>],
    store.address && [t('shop.address'), <p>{store.address}</p>],
    store.store_hours && [t('shop.hours'), <p>{store.store_hours}</p>],
  ].filter(Boolean)

  return (
    <section className="store-information">
      <Link className="back-link" to={`/store/${store.id}`}>{store.name}</Link>
      <h1>{t('shop.storeInfo')}</h1>
      {store.description && <p className="lead">{store.description}</p>}
      {details.length > 0 && <dl className="store-information-details">
        {details.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      </dl>}
      <section className="store-information-location" aria-labelledby="store-location-heading">
        <h2 id="store-location-heading">{t('shop.location')}</h2>
        {store.location
          ? <StoreLocationMap location={store.location} />
          : <p className="muted">{t('shop.locationMissing')}</p>}
      </section>
    </section>
  )
}