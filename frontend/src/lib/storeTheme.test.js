import { describe, expect, it } from 'vitest'
import { storefrontStyle } from './storeTheme'

describe('storefront theme tokens', () => {
  it('uses accessible foregrounds for light and dark choices', () => {
    expect(storefrontStyle({ primary_color: '#ffffff', secondary_color: '#111111' })).toEqual({
      '--store-primary': '#ffffff',
      '--store-secondary': '#111111',
      '--store-on-primary': '#0f2530',
      '--store-on-secondary': '#ffffff',
    })
  })

  it('keeps current site colors as the default theme', () => {
    expect(storefrontStyle(null)['--store-primary']).toBe('#0d8a85')
    expect(storefrontStyle(null)['--store-secondary']).toBe('#f2f7f6')
  })
})