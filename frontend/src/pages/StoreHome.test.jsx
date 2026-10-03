import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'
import StoreHome from './StoreHome'

const shop = {
  catalog: {
    store: {
      id: 7,
      name: 'Cafe Nima',
      business_type: 'restaurant',
      categories: [{ id: 'coffee', name: 'Coffee' }, { id: 'pastry', name: 'Pastry' }],
    },
    products: [
      { id: 1, name: 'Espresso', description: 'Dark roast', stock: 8, category_ids: ['coffee'] },
      { id: 2, name: 'Croissant', description: 'Butter pastry', stock: 4, category_ids: ['pastry'] },
    ],
  },
}

vi.mock('../components/ProductCard', () => ({ default: ({ product }) => <article>{product.name}</article> }))
vi.mock('../lib/hooks', () => ({ useBusinessTypes: () => [] }))
vi.mock('../lib/i18n', () => ({
  useI18n: () => ({
    t: (key, params) => key === 'shop.count' ? `${params.n} products` : key,
    bizLabel: (value) => value,
  }),
}))

function StoreContext() {
  return <Outlet context={{ shop, ask: vi.fn() }} />
}

afterEach(() => cleanup())

describe('public store category tabs', () => {
  it('shows all products first and filters products by selected tab', () => {
    render(<MemoryRouter initialEntries={['/store']}><Routes>
      <Route element={<StoreContext />}><Route path="/store" element={<StoreHome />} /></Route>
    </Routes></MemoryRouter>)

    expect(screen.getByText('Espresso')).toBeTruthy()
    expect(screen.getByText('Croissant')).toBeTruthy()
    const tabs = screen.getByRole('group', { name: 'shop.categories' })
    expect(within(tabs).getAllByRole('button')[0].textContent).toBe('shop.categoryAll')

    fireEvent.click(within(tabs).getByRole('button', { name: 'Coffee' }))
    expect(screen.getByText('Espresso')).toBeTruthy()
    expect(screen.queryByText('Croissant')).toBeNull()
  })

  it('shows left and right controls when the category list overflows', () => {
    render(<MemoryRouter initialEntries={['/store']}><Routes>
      <Route element={<StoreContext />}><Route path="/store" element={<StoreHome />} /></Route>
    </Routes></MemoryRouter>)

    const tabs = screen.getByRole('group', { name: 'shop.categories' })
    Object.defineProperties(tabs, {
      scrollWidth: { configurable: true, value: 500 },
      clientWidth: { configurable: true, value: 200 },
    })
    tabs.scrollBy = vi.fn()
    fireEvent(window, new Event('resize'))

    fireEvent.click(screen.getByRole('button', { name: 'shop.scrollLeft' }))
    expect(tabs.scrollBy).toHaveBeenCalledWith({ left: -180, behavior: 'smooth' })
    expect(screen.getByRole('button', { name: 'shop.scrollRight' })).toBeTruthy()
  })
})