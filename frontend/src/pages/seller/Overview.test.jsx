import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { BusinessTypePicker } from './Overview'

vi.mock('../../lib/i18n', () => ({
  useI18n: () => ({ t: (key) => key, bizLabel: (_slug, label) => label }),
}))

afterEach(() => cleanup())

describe('business type picker', () => {
  it('opens with search above the options and filters the list while typing', () => {
    render(<BusinessTypePicker
      label="Business type"
      value="clothing"
      onChange={vi.fn()}
      types={[
        { slug: 'clothing', label: 'Clothing' },
        { slug: 'restaurant', label: 'Restaurant' },
        { slug: 'books', label: 'Books' },
      ]}
    />)

    fireEvent.click(screen.getByRole('button', { name: 'Business type' }))
    const search = screen.getByRole('searchbox', { name: 'Business type dash.search' })
    const list = screen.getByRole('listbox', { name: 'Business type' })
    expect(search.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()

    fireEvent.change(search, { target: { value: 'rest' } })
    expect(within(list).getByRole('option', { name: 'Restaurant' })).toBeTruthy()
    expect(within(list).queryByRole('option', { name: 'Clothing' })).toBeNull()
    expect(within(list).queryByRole('option', { name: 'Books' })).toBeNull()
  })

  it('selects an option and closes the dropdown', () => {
    const onChange = vi.fn()
    render(<BusinessTypePicker label="Business type" value="clothing" onChange={onChange} types={[
      { slug: 'clothing', label: 'Clothing' },
      { slug: 'restaurant', label: 'Restaurant' },
    ]} />)

    fireEvent.click(screen.getByRole('button', { name: 'Business type' }))
    fireEvent.click(screen.getByRole('option', { name: 'Restaurant' }))

    expect(onChange).toHaveBeenCalledWith('restaurant')
    expect(screen.queryByRole('listbox')).toBeNull()
  })
})