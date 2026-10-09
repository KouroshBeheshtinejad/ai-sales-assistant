import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'
import { Swatch } from '../components/ui'
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
const authState = vi.hoisted(() => ({ isAuthed: false }))

vi.mock('../components/ProductCard', () => ({ default: ({ product }) => <article>{product.name}</article> }))
vi.mock('../lib/hooks', () => ({ useBusinessTypes: () => [] }))
vi.mock('../lib/auth', () => ({ useAuth: () => authState }))
vi.mock('../lib/i18n', () => ({
  useI18n: () => ({
    t: (key, params) => key === 'shop.count' ? `${params.n} products` : key,
    bizLabel: (value) => value,
    meta: { dir: 'rtl' },
  }),
}))

function StoreContext({ value = shop }) {
  return <Outlet context={{ shop: value, ask: vi.fn() }} />
}

afterEach(() => { cleanup(); authState.isAuthed = false })

describe('public store category tabs', () => {
  it('returns to the same store after signing in to write a review', () => {
    render(<MemoryRouter initialEntries={['/store/7']}><Routes>
      <Route element={<StoreContext />}><Route path="/store/:id" element={<StoreHome />} /></Route>
    </Routes></MemoryRouter>)

    expect(screen.getByRole('link', { name: 'nav.login' }).getAttribute('href')).toBe('/login?next=%2Fstore%2F7')
  })

  it('shows all products first and filters products by selected tab', () => {
    render(<MemoryRouter initialEntries={['/store']}><Routes>
      <Route element={<StoreContext />}><Route path="/store" element={<StoreHome />} /></Route>
    </Routes></MemoryRouter>)

    expect(screen.getByText('Espresso')).toBeTruthy()
    expect(screen.getByText('Croissant')).toBeTruthy()
    const tabs = screen.getByRole('group', { name: 'shop.categories' })
    expect(tabs.getAttribute('dir')).toBe('rtl')
    expect(within(tabs).getAllByRole('button')[0].textContent).toBe('shop.categoryAll')

    fireEvent.click(within(tabs).getByRole('button', { name: 'Coffee' }))
    expect(screen.getByText('Espresso')).toBeTruthy()
    expect(screen.queryByText('Croissant')).toBeNull()
  })

  it('filters by a price range and sorts the matching products', () => {
    const pricedShop = {
      ...shop,
      catalog: {
        ...shop.catalog,
        products: [
          { id: 1, name: 'Budget', price: '10', stock: 2, category_ids: [] },
          { id: 2, name: 'Midrange', price: '25', stock: 2, category_ids: [] },
          { id: 3, name: 'Premium', price: '50', stock: 2, category_ids: [] },
        ],
      },
    }

    render(<MemoryRouter initialEntries={['/store']}><Routes>
      <Route element={<StoreContext value={pricedShop} />}><Route path="/store" element={<StoreHome />} /></Route>
    </Routes></MemoryRouter>)

    fireEvent.change(screen.getByLabelText('shop.priceMin'), { target: { value: '20' } })
    fireEvent.change(screen.getByLabelText('shop.priceMax'), { target: { value: '60' } })
    expect(screen.queryByText('Budget')).toBeNull()
    expect(screen.getByText('Midrange')).toBeTruthy()
    expect(screen.getByText('Premium')).toBeTruthy()

    fireEvent.change(screen.getByLabelText('shop.sortPrice'), { target: { value: 'descending' } })
    expect(screen.getAllByRole('article').map((item) => item.textContent)).toEqual(['Premium', 'Midrange'])
  })

  it('offers the remaining products after the first twelve', () => {
    const expandedCatalog = {
      ...shop,
      catalog: {
        ...shop.catalog,
        products: [...shop.catalog.products, ...Array.from({ length: 11 }, (_, index) => ({
          id: index + 3,
          name: `Product ${index + 3}`,
          stock: 2,
          category_ids: [],
        }))],
      },
    }

    render(<MemoryRouter initialEntries={['/store']}><Routes>
      <Route element={<StoreContext value={expandedCatalog} />}><Route path="/store" element={<StoreHome />} /></Route>
    </Routes></MemoryRouter>)

    expect(screen.getByText('Product 12')).toBeTruthy()
    expect(screen.queryByText('Product 13')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'shop.viewAllProducts' }))
    expect(screen.getByText('Product 13')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'shop.viewAllProducts' })).toBeNull()
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

  it('keeps the fallback avatar letter centered in its placeholder box', () => {
    render(<Swatch seed="Cafe Nima" label="Cafe Nima" />)

    const swatch = document.querySelector('.swatch')
    const letter = screen.getByText('C')

    expect(swatch.style.display).toBe('grid')
    expect(swatch.style.placeItems).toBe('center')
    expect(letter.style.display).toBe('grid')
    expect(letter.style.placeItems).toBe('center')
    expect(letter.style.width).toBe('100%')
    expect(letter.style.height).toBe('100%')
  })
})