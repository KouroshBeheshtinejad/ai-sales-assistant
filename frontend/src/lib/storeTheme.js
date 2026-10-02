function readableColor(hex) {
  const channels = hex.match(/[\da-f]{2}/gi)?.map((channel) => parseInt(channel, 16) / 255) || [0, 0, 0]
  const linear = channels.map((channel) => (channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4))
  const luminance = linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722
  return luminance > 0.2 ? '#0f2530' : '#ffffff'
}

export function storefrontStyle(store) {
  const primary = store?.primary_color || '#0d8a85'
  const secondary = store?.secondary_color || '#f2f7f6'
  return {
    '--store-primary': primary,
    '--store-secondary': secondary,
    '--store-on-primary': readableColor(primary),
    '--store-on-secondary': readableColor(secondary),
  }
}