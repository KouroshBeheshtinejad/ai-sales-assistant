// Locale catalogues are written as `key = value` lines (one message per line, `#` for comments).
// It keeps the files readable for translators and cheap to diff.
export function parseCatalog(source) {
  const out = {}
  for (const raw of source.split('\n')) {
    const line = raw.trim()
    if (!line || line.startsWith('#')) continue
    const cut = line.indexOf('=')
    if (cut < 1) continue
    out[line.slice(0, cut).trim()] = line.slice(cut + 1).trim()
  }
  return out
}
