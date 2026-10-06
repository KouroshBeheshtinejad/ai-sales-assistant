import { describe, expect, it } from 'vitest'
import {
  CARD_STYLES, EDGES, INK_DARK, INK_LIGHT, LOOKS, PATTERNS, SECTION_ICONS,
  contrastRatio, inkFor, isHex, safeCards, safeEdge, safeIcon, safePattern, sectionStyle,
} from './sectionLook'

describe('section decoration helpers', () => {
  it('calculates WCAG contrast and chooses the safest text ink across gradients', () => {
    expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 0)
    expect(inkFor(['#ffffff'])).toBe(INK_DARK)
    expect(inkFor(['#0f2530'])).toBe(INK_LIGHT)
    const colors = ['#b0b0b0', '#1a1a1a']
    expect(inkFor(colors)).toBe(INK_LIGHT)
  })

  it('only accepts six-digit hex colours and safely falls back for invalid values', () => {
    expect(['#fff4d6', '#FFF4D6'].every(isHex)).toBe(true)
    expect(['', null, 'red', '#fff', 'url(x)'].some(isHex)).toBe(false)
    expect(sectionStyle('url(x)', 'red')).toMatchObject({ '--sec-bg': '#f2f7f6', '--sec-fill': '#f2f7f6' })
  })

  it('creates plain and gradient fills with readable text for every preset', () => {
    expect(sectionStyle('#ffe29a')['--sec-fill']).toBe('#ffe29a')
    expect(sectionStyle('#ffe29a', '#ffb199')['--sec-fill']).toBe('linear-gradient(135deg, #ffe29a, #ffb199)')
    for (const look of LOOKS) {
      const style = sectionStyle(look.background_color, look.background_color_2)
      for (const color of [look.background_color, look.background_color_2].filter(Boolean)) {
        expect(contrastRatio(style['--sec-ink'], color), `${look.id} ${color}`).toBeGreaterThanOrEqual(4.5)
      }
    }
  })

  it('clamps decorative values to closed server-aligned vocabularies', () => {
    expect(safePattern('unknown')).toBe('none')
    expect(safePattern('dots')).toBe('dots')
    expect(safeEdge('zigzag')).toBe('straight')
    expect(safeCards('neon')).toBe('solid')
    expect(safeIcon('<img src=x>')).toBe('')
    expect(safeIcon('🔥')).toBe('🔥')
    expect(new Set(PATTERNS.map(safePattern)).size).toBe(PATTERNS.length)
    expect(new Set(EDGES.map(safeEdge)).size).toBe(EDGES.length)
    expect(new Set(CARD_STYLES.map(safeCards)).size).toBe(CARD_STYLES.length)
    expect(new Set(SECTION_ICONS).size).toBe(SECTION_ICONS.length)
  })
})
