import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import BusinessCategories, { BUSINESS_CATEGORY_ICONS, BUSINESS_GROUP_VISUALS } from '../BusinessCategories'
import { BUSINESS_GROUPS } from '../../lib/businessGroups'

vi.mock('../../lib/i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${Object.values(params).join(',')}` : key),
    num: (value) => String(value),
    bizLabel: (slug, label) => label || slug,
  }),
}))
vi.mock('../../components/ui', () => ({ Icon: () => <span aria-hidden="true" /> }))

const ALL_SLUGS = BUSINESS_GROUPS.flatMap((group) => group.types)
const typesOf = (slugs) => slugs.map((slug) => ({ slug, label: `Label ${slug}` }))
const view = (slugs = ALL_SLUGS) => render(<MemoryRouter><BusinessCategories types={typesOf(slugs)} /></MemoryRouter>)
const tile = (group) => screen.getByRole('button', { name: new RegExp(`bizGroup\\.${group}`) })
const popover = (group) => document.getElementById(`biz-pop-${group}`)

afterEach(() => cleanup())

describe('business category icons', () => {
  it('assigns a unique icon to every business category', () => {
    const icons = Object.values(BUSINESS_CATEGORY_ICONS)
    expect(new Set(icons).size).toBe(icons.length)
  })

  it('gives every group its own icon and colours', () => {
    const icons = Object.values(BUSINESS_GROUP_VISUALS).map((visual) => visual.Icon)
    expect(new Set(icons).size).toBe(icons.length)
    for (const group of BUSINESS_GROUPS) expect(BUSINESS_GROUP_VISUALS[group.id]).toBeTruthy()
  })
})

describe('business groups on the home page', () => {
  it('shows one tile per group instead of one per business type', () => {
    view()
    expect(ALL_SLUGS).toHaveLength(48 + 1) // sanity: every real business type is in some group
    expect(screen.getAllByRole('button', { name: /bizGroup\./ })).toHaveLength(BUSINESS_GROUPS.length)
    expect(screen.getByRole('button', { name: /bizGroup\.food.*landing\.groupTypes:6/ })).toBeTruthy()
  })

  it('keeps every business type reachable as a link', () => {
    view()
    for (const slug of ALL_SLUGS) {
      const link = document.querySelector(`a[href="/stores?business_type=${slug}"]`)
      expect(link, slug).toBeTruthy()
    }
  })

  it('puts types that belong to no group into an "other" tile so none is lost', () => {
    view(['cafe', 'brand_new_type'])
    fireEvent.click(tile('other'))
    expect(within(popover('other')).getByRole('link', { name: 'Label brand_new_type' }).getAttribute('href')).toBe('/stores?business_type=brand_new_type')
  })

  it('opens and closes a group panel with correct accessibility state', () => {
    view()
    const food = tile('food')
    expect(food.getAttribute('aria-expanded')).toBe('false')
    expect(food.getAttribute('aria-controls')).toBe('biz-pop-food')
    expect(popover('food').hidden).toBe(true)

    fireEvent.click(food)
    expect(food.getAttribute('aria-expanded')).toBe('true')
    expect(popover('food').hidden).toBe(false)
    expect(within(popover('food')).getAllByRole('link').filter((link) => link.classList.contains('biz-chip'))).toHaveLength(6)

    fireEvent.click(food)
    expect(food.getAttribute('aria-expanded')).toBe('false')
    expect(popover('food').hidden).toBe(true)
  })

  it('links chips to one type and the footer link to the whole group', () => {
    view()
    fireEvent.click(tile('food'))
    const panel = popover('food')
    expect(within(panel).getByRole('link', { name: 'Label cafe' }).getAttribute('href')).toBe('/stores?business_type=cafe')
    const all = panel.querySelector('.biz-all')
    expect(all.getAttribute('href')).toBe('/stores?business_type=restaurant,fast_food,cafe,bakery,grocery,grocery_delivery&group=food')
  })

  it('has no "view all" link when a group offers only one type', () => {
    view(['cafe'])
    fireEvent.click(tile('food'))
    expect(popover('food').querySelector('.biz-all')).toBeNull()
  })

  it('keeps only one panel open at a time', () => {
    view()
    fireEvent.click(tile('food'))
    fireEvent.click(tile('tech'))
    expect(popover('food').hidden).toBe(true)
    expect(popover('tech').hidden).toBe(false)
  })

  it('closes on Escape and returns focus to the tile', () => {
    view()
    const food = tile('food')
    fireEvent.click(food)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(popover('food').hidden).toBe(true)
    expect(document.activeElement).toBe(food)
  })

  it('closes when clicking outside, but not when clicking inside the panel', () => {
    view()
    fireEvent.click(tile('food'))
    fireEvent.pointerDown(popover('food'))
    expect(popover('food').hidden).toBe(false)
    fireEvent.pointerDown(document.body)
    expect(popover('food').hidden).toBe(true)
  })

  it('closes with the close button (used on phones)', () => {
    view()
    fireEvent.click(tile('food'))
    fireEvent.click(within(popover('food')).getByRole('button', { name: 'close' }))
    expect(popover('food').hidden).toBe(true)
  })

  it('renders no tiles while business types are still loading', () => {
    render(<MemoryRouter><BusinessCategories types={[]} /></MemoryRouter>)
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })
})
