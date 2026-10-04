import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Armchair, BookOpen, Bubbles, BriefcaseBusiness, Building2, CarFront, ChartNoAxesCombined,
  CodeXml, Coffee, Croissant, Dog, Dumbbell, Fish, Flower2, Gem, GraduationCap, Hammer,
  Hand, HardHat, Heart, KeyRound, Laptop, Lamp, NotebookPen, Palette, PartyPopper, PawPrint,
  PersonStanding, Pill, Plane, Printer, Sandwich, Scissors, Shirt, ShoppingBasket, Smile,
  Smartphone, SprayCan, Sprout, Stethoscope, Tent, ToyBrick, Trees, Trophy, Truck, Utensils,
  WashingMachine, Wheat, Sailboat,
} from 'lucide-react'
import { Button, Icon } from '../components/ui'
import { useI18n } from '../lib/i18n'
import { cx } from '../lib/util'

export const BUSINESS_CATEGORY_ICONS = {
  clothing: Shirt,
  fast_food: Sandwich,
  restaurant: Utensils,
  bakery: Croissant,
  cafe: Coffee,
  pharmacy: Pill,
  electronics: Laptop,
  furniture: Armchair,
  grocery: ShoppingBasket,
  cosmetics: SprayCan,
  jewelry: Gem,
  beauty_salon: Scissors,
  home_decor: Lamp,
  stationery: NotebookPen,
  pet_store: PawPrint,
  sports: Trophy,
  fitness: Dumbbell,
  automotive: CarFront,
  books_music: BookOpen,
  toys: ToyBrick,
  hardware: Hammer,
  flowers: Flower2,
  real_estate: Building2,
  travel: Plane,
  medical_clinic: Stethoscope,
  dental: Smile,
  yoga: PersonStanding,
  educational: GraduationCap,
  digital_products: Smartphone,
  software: CodeXml,
  agency: BriefcaseBusiness,
  construction: HardHat,
  landscaping: Trees,
  cleaning: Bubbles,
  laundry: WashingMachine,
  printing: Printer,
  event_planning: PartyPopper,
  wedding: Heart,
  artist_shop: Palette,
  handmade: Hand,
  agricultural: Wheat,
  veterinary: Dog,
  aquarium: Fish,
  garden: Sprout,
  grocery_delivery: Truck,
  productivity: ChartNoAxesCombined,
  car_rental: KeyRound,
  boat: Sailboat,
  camping: Tent,
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
        {types.map((type) => {
          const CategoryIcon = BUSINESS_CATEGORY_ICONS[type.slug]
          return (
            <li key={type.slug}>
              <Link className="business-tile" to={`/stores?business_type=${encodeURIComponent(type.slug)}`}>
                <span className="business-mark">
                  {CategoryIcon
                    ? <CategoryIcon size={25} strokeWidth={1.8} aria-hidden="true" />
                    : <Icon name="store" size={25} />}
                </span>
                <span>{bizLabel(type.slug, type.label)}</span>
              </Link>
            </li>
          )
        })}
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
