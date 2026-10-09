import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import CountryPhoneInput from './CountryPhoneInput'

vi.mock('../lib/i18n', () => ({ useI18n: () => ({ locale: 'en', t: (key) => key }) }))

afterEach(() => cleanup())

describe('country-aware phone input', () => {
  it('offers localized country calling codes and reports the selected country', () => {
    const onCountryChange = vi.fn()
    render(<CountryPhoneInput id="phone" value="" country="IR" onCountryChange={onCountryChange} onValueChange={vi.fn()} />)

    const select = screen.getByRole('combobox', { name: 'auth.phoneCountry' })
    expect(select.options.length).toBeGreaterThan(200)
    expect(screen.getByRole('option', { name: /🇺🇸 United States \(\+1\)/ })).toBeTruthy()
    fireEvent.change(select, { target: { value: 'US' } })
    expect(onCountryChange).toHaveBeenCalledOnce()
    expect(screen.getByRole('textbox').id).toBe('phone')
  })
})