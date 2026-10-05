export const BUSINESS_GROUPS = [
  { id: 'food', types: ['restaurant', 'fast_food', 'cafe', 'bakery', 'grocery', 'grocery_delivery'] },
  { id: 'fashion', types: ['clothing', 'jewelry', 'cosmetics', 'beauty_salon'] },
  { id: 'home', types: ['furniture', 'home_decor', 'hardware', 'construction', 'landscaping', 'cleaning', 'laundry', 'real_estate'] },
  { id: 'tech', types: ['electronics', 'software', 'digital_products', 'productivity', 'agency'] },
  { id: 'health', types: ['pharmacy', 'medical_clinic', 'dental', 'fitness', 'yoga', 'sports'] },
  { id: 'nature', types: ['pet_store', 'veterinary', 'aquarium', 'agricultural', 'garden', 'camping'] },
  { id: 'arts', types: ['stationery', 'books_music', 'educational', 'artist_shop', 'handmade', 'toys', 'printing'] },
  { id: 'travel', types: ['automotive', 'car_rental', 'boat', 'travel'] },
  { id: 'events', types: ['event_planning', 'wedding', 'flowers'] },
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
