import { describe, expect, it } from 'vitest'
import { prunePins } from './HomeSectionsAdmin'

describe('hand-picked items follow selected business types', () => {
  const pinned = [
    { id: 1, name: 'Cafe A', business_type: 'cafe' },
    { id: 2, name: 'Diner', business_type: 'restaurant' },
    { id: 3, name: 'Cafe B', business_type: 'cafe' },
  ]

  it('drops picks outside selected types and preserves the remaining order', () => {
    expect(prunePins(pinned, ['cafe']).map((item) => item.id)).toEqual([1, 3])
    expect(prunePins(pinned, ['cafe', 'restaurant']).map((item) => item.id)).toEqual([1, 2, 3])
  })

  it('drops every pick when there are no selected types', () => {
    expect(prunePins(pinned, [])).toEqual([])
  })
})
