import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { HomeSection, sectionStyle, sectionTitle } from './HomeSections'

vi.mock('../lib/i18n', () => ({
  useI18n: () => ({
    locale: 'en',
    meta: { dir: 'ltr' },
    t: (key, params) => (params ? `${key}:${Object.values(params).join(',')}` : key),
    num: (value) => String(value),
    money: (value) => `$${value}`,
    bizLabel: (slug, label) => label || slug,
  }),
}))
vi.mock('./ui', () => ({ Icon: () => <span aria-hidden="true" />, Swatch: () => <span /> }))
vi.mock('./ProductCard', () => ({ ProductVisual: () => <span />, StockBadge: () => <span /> }))

afterEach(() => cleanup())

const store = (id) => ({ id, name: `Store ${id}`, description: 'About', business_type: 'cafe', product_count: 3 })
const product = (id) => ({ id, name: `Product ${id}`, price: '10', stock: 4, store_id: 7, store_name: 'Cafe' })
const section = (patch = {}) => ({ id: 1, title: 'Hungry?', titles: {}, kind: 'stores', background_color: '#fff4d6', items: [store(1), store(2)], ...patch })
const view = (value) => render(<MemoryRouter><HomeSection section={value} types={[]} /></MemoryRouter>)

describe('home section colours and titles', () => {
  it('derives a readable text colour from the band colour', () => {
    expect(sectionStyle('#ffffff')['--sec-bg']).toBe('#ffffff')
    expect(sectionStyle('#ffffff')['--sec-ink']).not.toBe(sectionStyle('#0f2530')['--sec-ink'])
  })

  it('falls back to the default band colour for anything that is not a #rrggbb value', () => {
    for (const bad of [undefined, null, '', 'red', '#fff', 'url(javascript:alert(1))']) {
      expect(sectionStyle(bad)['--sec-bg']).toBe('#f2f7f6')
    }
  })

  it('uses the visitor language when translated and the default title otherwise', () => {
    expect(sectionTitle({ title: 'Hungry?', titles: { fa: 'گرسنه‌ای؟' } }, 'fa')).toBe('گرسنه‌ای؟')
    expect(sectionTitle({ title: 'Hungry?', titles: { fa: 'گرسنه‌ای؟' } }, 'en')).toBe('Hungry?')
    expect(sectionTitle({ title: 'Hungry?' }, 'de')).toBe('Hungry?')
  })
})

describe('home section rendering', () => {
  it('renders nothing for a section without items', () => {
    const { container } = view(section({ items: [] }))
    expect(container.firstChild).toBeNull()
  })

  it('shows the title as a heading and links every store to its storefront', () => {
    view(section({ titles: { en: 'Hungry? Start here' } }))
    expect(screen.getByRole('heading', { level: 2, name: 'Hungry? Start here' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Store 1' }).getAttribute('href')).toBe('/store/1')
    expect(screen.getByRole('link', { name: 'Store 2' }).getAttribute('href')).toBe('/store/2')
  })

  it('links products to their own page inside their store', () => {
    view(section({ kind: 'products', items: [product(5)] }))
    expect(screen.getByRole('link', { name: 'Product 5' }).getAttribute('href')).toBe('/store/7/product/5')
  })

  it('exposes the row as a labelled, keyboard-focusable scroll region', () => {
    const { container } = view(section())
    const track = container.querySelector('.hs-track')
    expect(track.getAttribute('tabindex')).toBe('0')
    expect(track.getAttribute('aria-label')).toBe('Hungry?')
    expect(container.querySelector('section').style.getPropertyValue('--sec-bg')).toBe('#fff4d6')
  })
})
