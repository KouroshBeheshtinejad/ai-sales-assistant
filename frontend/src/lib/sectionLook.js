// Safe visual options for curated home-page sections.
export const PATTERNS = ['none', 'dots', 'grid', 'diagonal', 'waves', 'zellij']
export const EDGES = ['straight', 'wave', 'curve']
export const CARD_STYLES = ['solid', 'glass']
export const SECTION_ICONS = [
  '🍔', '🍕', '☕', '🍰', '🥗', '🛒', '👗', '👟', '💄', '💎', '🏠', '🔧', '💻', '📱',
  '💊', '🐾', '🌿', '🌸', '🎨', '📚', '🎁', '🎉', '🚗', '✨', '🔥', '⭐', '💖', '🎓', '🧸', '🎵', '⚽',
]

export const DEFAULT_BG = '#f2f7f6'
export const INK_DARK = '#0f2530'
export const INK_LIGHT = '#ffffff'
export const LOOKS = [
  { id: 'plain', background_color: '#f2f7f6', background_color_2: '', pattern: 'none', edge: 'straight', card_style: 'solid' },
  { id: 'sunrise', background_color: '#ffe29a', background_color_2: '#ffb199', pattern: 'dots', edge: 'wave', card_style: 'solid' },
  { id: 'ocean', background_color: '#cfeaff', background_color_2: '#9bd0ff', pattern: 'waves', edge: 'curve', card_style: 'solid' },
  { id: 'forest', background_color: '#d8f3dc', background_color_2: '#a7dbb4', pattern: 'zellij', edge: 'wave', card_style: 'solid' },
  { id: 'candy', background_color: '#ffe0f0', background_color_2: '#e3d4ff', pattern: 'diagonal', edge: 'straight', card_style: 'glass' },
  { id: 'night', background_color: '#0f2530', background_color_2: '#1d5563', pattern: 'grid', edge: 'curve', card_style: 'glass' },
]

export const isHex = (value) => /^#[0-9a-f]{6}$/i.test(value || '')

function luminance(hex) {
  const channels = hex.match(/[\da-f]{2}/gi).map((channel) => parseInt(channel, 16) / 255)
  const [r, g, b] = channels.map((channel) => (channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4))
  return r * 0.2126 + g * 0.7152 + b * 0.0722
}

export function contrastRatio(first, second) {
  const [light, dark] = [luminance(first), luminance(second)].sort((a, b) => b - a)
  return (light + 0.05) / (dark + 0.05)
}

export function inkFor(colors) {
  const valid = colors.filter(isHex)
  if (!valid.length) return INK_DARK
  const worst = (ink) => Math.min(...valid.map((color) => contrastRatio(ink, color)))
  return worst(INK_DARK) >= worst(INK_LIGHT) ? INK_DARK : INK_LIGHT
}

export function sectionStyle(color, color2) {
  const first = isHex(color) ? color : DEFAULT_BG
  const second = isHex(color2) ? color2 : ''
  return {
    '--sec-bg': first,
    '--sec-fill': second ? `linear-gradient(135deg, ${first}, ${second})` : first,
    '--sec-ink': inkFor(second ? [first, second] : [first]),
  }
}

export const safePattern = (value) => (PATTERNS.includes(value) ? value : 'none')
export const safeEdge = (value) => (EDGES.includes(value) ? value : 'straight')
export const safeCards = (value) => (CARD_STYLES.includes(value) ? value : 'solid')
export const safeIcon = (value) => (SECTION_ICONS.includes(value) ? value : '')
