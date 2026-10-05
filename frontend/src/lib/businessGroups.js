export const BUSINESS_GROUPS = [
  { id: 'food', types: ['restaurant', 'fast_food', 'cafe', 'bakery', 'grocery'] },
  { id: 'fashion', types: ['clothing', 'jewelry', 'cosmetics', 'beauty_salon'] },
  { id: 'home', types: ['furniture', 'home_decor', 'hardware'] },
  { id: 'health', types: ['pharmacy', 'fitness'] },
  { id: 'nature', types: ['pet_store', 'sports'] },
  { id: 'arts', types: ['stationery', 'books_music', 'toys'] },
  { id: 'travel', types: ['automotive'] },
  { id: 'events', types: ['flowers'] },
]

export function groupBusinessTypes(slugs) {
  const available = new Set(slugs)
  const used = new Set()
  const groups = BUSINESS_GROUPS.map((group) => {
    const list = group.types.filter((slug) => available.has(slug))
    list.forEach((slug) => used.add(slug))
    return { id: group.id, slugs: list }
  }).filter((group) => group.slugs.length)
  const rest = slugs.filter((slug) => !used.has(slug))
  if (rest.length) groups.push({ id: 'other', slugs: rest })
  return groups
}
