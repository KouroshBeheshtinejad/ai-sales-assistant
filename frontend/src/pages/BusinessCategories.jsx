import { Link } from 'react-router-dom'
import { Icon } from '../components/ui'
import { useI18n } from '../lib/i18n'

const CATEGORY_ICONS = {
  clothing: 'tag', fast_food: 'store', restaurant: 'store', bakery: 'box', cafe: 'sparkle',
  pharmacy: 'plus', electronics: 'bolt', furniture: 'store', grocery: 'cart', cosmetics: 'sparkle',
  jewelry: 'sparkle', beauty_salon: 'user', home_decor: 'store', stationery: 'doc', pet_store: 'heart',
  sports: 'bolt', fitness: 'users', automotive: 'truck', books_music: 'doc', toys: 'sparkle',
  hardware: 'box', flowers: 'sparkle', real_estate: 'home', travel: 'globe', medical_clinic: 'plus',
  dental: 'plus', yoga: 'users', educational: 'doc', digital_products: 'code', software: 'code',
  agency: 'users', construction: 'store', landscaping: 'home', cleaning: 'sparkle', laundry: 'refresh',
  printing: 'doc', event_planning: 'users', wedding: 'sparkle', artist_shop: 'sparkle', handmade: 'tag',
  agricultural: 'home', veterinary: 'heart', aquarium: 'globe', garden: 'home', grocery_delivery: 'truck',
  productivity: 'layers', car_rental: 'truck', boat: 'truck', camping: 'home',
}

export default function BusinessCategories({ types = [] }) {
  const { t, bizLabel } = useI18n()
  return (
    <section className="wrap section business-directory" id="business-types" aria-labelledby="business-types-title">
      <div className="section-head">
        <div>
          <h1 id="business-types-title">{t('landing.browseBusinesses')}</h1>
          <p className="lead">{t('landing.browseBusinessesLead')}</p>
        </div>
      </div>
      <ul className="business-grid">
        {types.map((type) => (
          <li key={type.slug}>
            <Link className="business-tile" to={`/stores?business_type=${encodeURIComponent(type.slug)}`}>
              <span className="business-mark"><Icon name={CATEGORY_ICONS[type.slug] || 'store'} size={25} /></span>
              <span>{bizLabel(type.slug, type.label)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
