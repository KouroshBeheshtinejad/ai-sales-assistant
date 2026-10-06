import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Armchair, BookOpen, Bubbles, BriefcaseBusiness, Building2, CarFront, ChartNoAxesCombined,
  CodeXml, Coffee, Croissant, Dog, Dumbbell, Fish, Flower2, Gem, GraduationCap, Hammer,
  Hand, HardHat, Heart, KeyRound, Laptop, Lamp, NotebookPen, Palette, PartyPopper, PawPrint,
  PersonStanding, Pill, Plane, Printer, Sandwich, Scissors, Shirt, ShoppingBasket, Smile,
  Smartphone, SprayCan, Sprout, Stethoscope, Tent, ToyBrick, Trees, Trophy, Truck, Utensils,
  WashingMachine, Wheat, Sailboat,
  ChevronDown, HeartPulse, House, LayoutGrid, Leaf, UtensilsCrossed, X,
} from 'lucide-react'
import { Icon } from '../components/ui'
import { groupBusinessTypes } from '../lib/businessGroups'
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

// One icon and colour pair per group of related business types.
export const BUSINESS_GROUP_VISUALS = {
  food: { Icon: UtensilsCrossed, from: '#f59e0b', to: '#ef4444' },
  fashion: { Icon: Shirt, from: '#ec4899', to: '#a855f7' },
  home: { Icon: House, from: '#14b8a6', to: '#0e7490' },
  tech: { Icon: Laptop, from: '#3b82f6', to: '#6366f1' },
  health: { Icon: HeartPulse, from: '#22c55e', to: '#0d9488' },
  nature: { Icon: Leaf, from: '#84cc16', to: '#16a34a' },
  arts: { Icon: Palette, from: '#8b5cf6', to: '#d946ef' },
  travel: { Icon: Plane, from: '#0ea5e9', to: '#2563eb' },
  events: { Icon: PartyPopper, from: '#f43f5e', to: '#f59e0b' },
  other: { Icon: LayoutGrid, from: '#64748b', to: '#334155' },
}

const storesUrl = (slugs, group) => `/stores?business_type=${slugs.map(encodeURIComponent).join(',')}${group ? `&group=${group}` : ''}`

// Nine group tiles replace the old wall of ~50 tiles. Choosing one opens a small panel with its
// business types: a popover next to the tile on larger screens, a bottom sheet on phones.
export default function BusinessCategories({ types = [] }) {
  const { t, num, bizLabel } = useI18n()
  const groups = useMemo(() => groupBusinessTypes(types.map((type) => type.slug)), [types])
  const labels = useMemo(() => Object.fromEntries(types.map((type) => [type.slug, bizLabel(type.slug, type.label)])), [types, bizLabel])
  const [openId, setOpenId] = useState(null)
  const root = useRef(null)
  const tiles = useRef({})

  useEffect(() => {
    if (!openId) return undefined
    const onKey = (event) => {
      if (event.key !== 'Escape') return
      setOpenId(null)
      tiles.current[openId]?.focus()
    }
    const onPointer = (event) => { if (!root.current?.contains(event.target)) setOpenId(null) }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onPointer)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onPointer)
    }
  }, [openId])

  return (
    <section className="wrap section business-directory" id="business-types" aria-labelledby="business-types-title">
      <div className="section-head">
        <div>
          <h2 id="business-types-title">{t('landing.browseBusinesses')}</h2>
          <p className="lead">{t('landing.browseBusinessesLead')}</p>
        </div>
      </div>
      <ul className="biz-groups" ref={root}>
        {groups.map((group) => (
          <GroupTile
            key={group.id}
            group={group}
            labels={labels}
            open={openId === group.id}
            onToggle={() => setOpenId(openId === group.id ? null : group.id)}
            onClose={() => { setOpenId(null); tiles.current[group.id]?.focus() }}
            buttonRef={(node) => { tiles.current[group.id] = node }}
            t={t}
            num={num}
          />
        ))}
      </ul>
    </section>
  )
}

function GroupTile({ group, labels, open, onToggle, onClose, buttonRef, t, num }) {
  const visual = BUSINESS_GROUP_VISUALS[group.id] || BUSINESS_GROUP_VISUALS.other
  const GroupIcon = visual.Icon
  const name = t(`bizGroup.${group.id}`)
  const popId = `biz-pop-${group.id}`
  const pop = useRef(null)
  const item = useRef(null)

  // Larger screens: keep the popover inside the viewport and point its arrow at the tile.
  useLayoutEffect(() => {
    const el = pop.current
    if (!open || !el) return
    el.style.removeProperty('--pop-shift')
    if (!window.matchMedia?.('(min-width: 641px)').matches) return
    const margin = 12
    const box = el.getBoundingClientRect()
    const anchor = item.current.getBoundingClientRect()
    let shift = 0
    if (box.left < margin) shift = margin - box.left
    else if (box.right > window.innerWidth - margin) shift = window.innerWidth - margin - box.right
    el.style.setProperty('--pop-shift', `${Math.round(shift)}px`)
    const arrow = anchor.left + anchor.width / 2 - (box.left + shift)
    el.style.setProperty('--pop-arrow', `${Math.round(Math.min(Math.max(arrow, 22), box.width - 22))}px`)
    el.scrollIntoView?.({ block: 'nearest', inline: 'nearest' })
  }, [open])

  return (
    <li className={cx('biz-group', open && 'is-open')} ref={item} style={{ '--g1': visual.from, '--g2': visual.to }}>
      <button type="button" className="biz-tile" ref={buttonRef} aria-expanded={open} aria-controls={popId} onClick={onToggle}>
        <span className="biz-mark"><GroupIcon size={28} strokeWidth={1.8} aria-hidden="true" /></span>
        <span className="biz-name">{name}</span>
        <span className="biz-count">{t('landing.groupTypes', { n: num(group.slugs.length) })}</span>
        <ChevronDown className="biz-caret" size={16} aria-hidden="true" />
      </button>
      {open && <div className="biz-backdrop" aria-hidden="true" onClick={onClose} />}
      <div id={popId} ref={pop} className="biz-pop" role="group" aria-label={t('landing.groupPopoverLabel', { group: name })} hidden={!open}>
        <div className="biz-pop-head">
          <strong>{name}</strong>
          <button type="button" className="icon-btn biz-pop-close" onClick={onClose} aria-label={t('close')}><X size={18} aria-hidden="true" /></button>
        </div>
        <ul className="biz-chips">
          {group.slugs.map((slug) => {
            const TypeIcon = BUSINESS_CATEGORY_ICONS[slug]
            return (
              <li key={slug}>
                <Link className="biz-chip" to={storesUrl([slug])}>
                  {TypeIcon ? <TypeIcon size={18} strokeWidth={1.8} aria-hidden="true" /> : <Icon name="store" size={18} />}
                  <span>{labels[slug]}</span>
                </Link>
              </li>
            )
          })}
        </ul>
        {group.slugs.length > 1 && (
          <Link className="biz-all" to={storesUrl(group.slugs, group.id)}>
            {t('landing.groupViewAll', { group: name })}<Icon name="arrow" size={16} className="flip-rtl" />
          </Link>
        )}
      </div>
    </li>
  )
}
