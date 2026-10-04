import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Icon } from '../components/ui'
import { useI18n } from '../lib/i18n'
import { cx } from '../lib/util'

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

// Two full rows on desktop (7 columns); the CSS trims to whole rows on tablet and phone too.
const COLLAPSED_COUNT = 14

export default function BusinessCategories({ types = [] }) {
  const { t, num, bizLabel } = useI18n()
  const [expanded, setExpanded] = useState(false)
  const collapsible = types.length > COLLAPSED_COUNT
  return (
    <section className="wrap section business-directory" id="business-types" aria-labelledby="business-types-title">
      <div className="section-head">
        <div>
          <h2 id="business-types-title">{t('landing.browseBusinesses')}</h2>
          <p className="lead">{t('landing.browseBusinessesLead')}</p>
        </div>
      </div>
      <ul id="business-grid" className={cx('business-grid', collapsible && !expanded && 'is-collapsed')}>
        {types.map((type) => (
          <li key={type.slug}>
            <Link className="business-tile" to={`/stores?business_type=${encodeURIComponent(type.slug)}`}>
              <span className="business-mark"><Icon name={CATEGORY_ICONS[type.slug] || 'store'} size={25} /></span>
              <span>{bizLabel(type.slug, type.label)}</span>
            </Link>
          </li>
        ))}
      </ul>
      {collapsible && (
        <div className="business-more">
          <Button aria-expanded={expanded} aria-controls="business-grid" onClick={() => setExpanded(!expanded)}>
            {expanded ? t('landing.showFewer') : t('landing.showAllTypes', { n: num(types.length) })}
            <Icon name="chevron" size={16} className={expanded ? 'flip-up' : undefined} />
          </Button>
        </div>
      )}
    </section>
  )
}
