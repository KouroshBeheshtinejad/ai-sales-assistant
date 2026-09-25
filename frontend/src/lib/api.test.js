import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from './api'

describe('versioned API client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('uses the /api prefix for public catalog requests', async () => {
    const response = { ok: true, json: async () => ({ products: [] }) }
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response)

    await api.catalog(42)

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/public/stores/42/catalog',
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('requests the landing showcase with explicit limits', async () => {
    const response = { ok: true, json: async () => ({ stores: [], products: [] }) }
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response)

    await api.showcase(3, 5)

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/public/showcase?stores=3&products=5',
      expect.objectContaining({ method: 'GET' }),
    )
  })
})