import { describe, expect, it } from 'vitest'
import { BUSINESS_GROUPS, groupBusinessTypes } from './businessGroups'

describe('business groups', () => {
  it('never lists the same type twice', () => {
    const all = BUSINESS_GROUPS.flatMap((group) => group.types)
    expect(new Set(all).size).toBe(all.length)
  })

  it('keeps only the types the API returned, in group order', () => {
    const groups = groupBusinessTypes(['cafe', 'clothing', 'restaurant'])
    expect(groups).toEqual([
      { id: 'food', slugs: ['restaurant', 'cafe'] },
      { id: 'fashion', slugs: ['clothing'] },
    ])
  })

  it('puts unknown or newly added types into "other" so nothing becomes unselectable', () => {
    const groups = groupBusinessTypes(['cafe', 'brand_new_type'])
    expect(groups.at(-1)).toEqual({ id: 'other', slugs: ['brand_new_type'] })
  })

  it('returns no groups for no types', () => {
    expect(groupBusinessTypes([])).toEqual([])
  })
})
