import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import StoreDirectory from './StoreDirectory'
import { api } from '../lib/api'

vi.mock('../lib/api', () => ({ api: { storesByBusinessType: vi.fn() } }))
vi.mock('../lib/hooks', async () => ({
  ...(await vi.importActual('../lib/hooks')),
  useBusinessTypes: () => [{ slug: 'cafe', label: 'Cafe type' }],
  useSeo: () => {},
}))
vi.mock('../lib/i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${params.n}` : key),
    num: (value) => String(value),
    bizLabel: (slug, label) => label || slug,
    err: () => 'error',
  }),
}))

const store = (id, name) => ({ id, name, description: '', logo_url: null, product_count: 1 })
const bySlug = { cafe: [store(1, 'Cafe One')], bakery: [store(2, 'Bakery Two')], pharmacy: [store(3, 'Pharmacy Three')] }
const page = (search) => render(<MemoryRouter initialEntries={[`/stores${search}`]}><StoreDirectory /></MemoryRouter>)

beforeEach(() => {
  api.storesByBusinessType.mockReset()
  api.storesByBusinessType.mockImplementation(async (slug) => ({ stores: bySlug[slug] || [], total: (bySlug[slug] || []).length }))
})
afterEach(() => cleanup())

describe('store directory with one or several business types', () => {
  it('loads a single type exactly as before and titles the page with its label', async () => {
    page('?business_type=cafe')
    await screen.findByText('Cafe One')
    expect(api.storesByBusinessType).toHaveBeenCalledTimes(1)
    expect(api.storesByBusinessType).toHaveBeenCalledWith('cafe')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Cafe type')
  })

  it('merges the stores of several comma-separated types and counts them together', async () => {
    page('?business_type=cafe,bakery,pharmacy')
    await screen.findByText('Pharmacy Three')
    expect(screen.getByText('Cafe One')).toBeTruthy()
    expect(screen.getByText('Bakery Two')).toBeTruthy()
    expect(screen.getByText('landing.categoryStoreCount:3')).toBeTruthy()
  })

  it('uses the group name as the title when a known group is given', async () => {
    page('?business_type=cafe,bakery&group=food')
    await screen.findByText('Cafe One')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('bizGroup.food')
  })

  it('ignores an unknown group name instead of showing it', async () => {
    page('?business_type=cafe,bakery&group=<b>evil</b>')
    await screen.findByText('Cafe One')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('landing.browseBusinesses')
  })

  it('still shows the other types when one of them fails to load', async () => {
    api.storesByBusinessType.mockImplementation(async (slug) => {
      if (slug === 'bakery') throw new Error('boom')
      return { stores: bySlug[slug], total: bySlug[slug].length }
    })
    page('?business_type=cafe,bakery,pharmacy')
    await screen.findByText('Cafe One')
    expect(screen.getByText('Pharmacy Three')).toBeTruthy()
    expect(screen.queryByText('Bakery Two')).toBeNull()
  })

  it('removes duplicates, trims blanks and never requests more than 12 types', async () => {
    const many = Array.from({ length: 20 }, (_, index) => `type_${index}`).join(',')
    page(`?business_type=cafe,, cafe ,${many}`)
    await waitFor(() => expect(api.storesByBusinessType).toHaveBeenCalled())
    const slugs = api.storesByBusinessType.mock.calls.map(([slug]) => slug)
    expect(slugs).toHaveLength(12)
    expect(new Set(slugs).size).toBe(12)
    expect(slugs).toContain('cafe')
  })

  it('does not request anything without a business type', async () => {
    page('')
    await screen.findByText('landing.categoryEmpty')
    expect(api.storesByBusinessType).not.toHaveBeenCalled()
  })
})
