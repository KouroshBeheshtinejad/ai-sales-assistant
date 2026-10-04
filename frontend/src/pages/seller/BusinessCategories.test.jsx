import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import BusinessCategories from '../BusinessCategories'

vi.mock('../../lib/i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${params.n}` : key),
    num: (value) => String(value),
    bizLabel: (slug, label) => label || slug,
  }),
}))
vi.mock('../../components/ui', () => ({
  Button: ({ children, ...rest }) => <button type="button" {...rest}>{children}</button>,
  Icon: () => <span aria-hidden="true" />,
}))

const makeTypes = (count) => Array.from({ length: count }, (_, i) => ({ slug: `type_${i}`, label: `Type ${i}` }))

afterEach(() => cleanup())

describe('business category grid', () => {
  it('keeps every category in the DOM and links each one to its store list', () => {
    render(<MemoryRouter><BusinessCategories types={makeTypes(30)} /></MemoryRouter>)
    expect(screen.getAllByRole('link')).toHaveLength(30)
    expect(screen.getByRole('link', { name: 'Type 3' }).getAttribute('href')).toBe('/stores?business_type=type_3')
  })

  it('starts collapsed and toggles with an accessible button', () => {
    const { container } = render(<MemoryRouter><BusinessCategories types={makeTypes(30)} /></MemoryRouter>)
    const grid = container.querySelector('#business-grid')
    const toggle = screen.getByRole('button', { name: /landing\.showAllTypes:30/ })
    expect(grid.classList.contains('is-collapsed')).toBe(true)
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(toggle.getAttribute('aria-controls')).toBe('business-grid')

    fireEvent.click(toggle)
    expect(grid.classList.contains('is-collapsed')).toBe(false)
    expect(screen.getByRole('button', { name: /landing\.showFewer/ }).getAttribute('aria-expanded')).toBe('true')
  })

  it('shows no toggle when everything already fits in two rows', () => {
    render(<MemoryRouter><BusinessCategories types={makeTypes(14)} /></MemoryRouter>)
    expect(screen.queryByRole('button')).toBeNull()
  })
})
