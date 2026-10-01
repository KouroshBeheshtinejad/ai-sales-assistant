import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../lib/i18n'
import ApiDocs from './ApiDocs'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

const openApi = {
  info: { version: '1.2.3' },
  paths: {
    '/api/products/': {
      get: {
        tags: ['Products'],
        summary: 'List products',
        parameters: [{ name: 'store_id', in: 'query', required: true, schema: { type: 'integer' } }],
        responses: { 200: { description: 'Products returned' } },
      },
      post: {
        tags: ['Products'],
        summary: 'Create product',
        security: [{ HTTPBearer: [] }],
        requestBody: { content: {
          'application/json': { schema: { $ref: '#/components/schemas/ProductCreate' } },
          'multipart/form-data': { schema: { type: 'object', properties: { image: { type: 'string', format: 'binary' } } } },
        } },
        responses: { 201: { description: 'Product created' } },
      },
    },
    '/health/live': { get: { summary: 'Health probe', responses: { 200: { description: 'Alive' } } } },
  },
  components: {
    schemas: { ProductCreate: { type: 'object', properties: { name: { type: 'string' } } } },
    securitySchemes: { HTTPBearer: { type: 'http', scheme: 'bearer' } },
  },
}

describe('API documentation page', () => {
  it('renders API operations from OpenAPI, including parameters, schemas, and responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => openApi }))
    render(<I18nProvider><ApiDocs /></I18nProvider>)

    expect(await screen.findByText('List products')).toBeTruthy()
    expect(screen.getByText('POST')).toBeTruthy()
    fireEvent.click(screen.getByText('Create product'))
    expect(await screen.findByText(/"name"/)).toBeTruthy()
    expect(screen.getByText('multipart/form-data')).toBeTruthy()
    expect(screen.getByText(/HTTPBearer/)).toBeTruthy()
    expect(screen.getByText('Product created')).toBeTruthy()
    expect(screen.queryByText('Health probe')).toBeNull()
  })

  it('filters the generated endpoint list by search query', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => openApi }))
    render(<I18nProvider><ApiDocs /></I18nProvider>)

    await screen.findByText('List products')
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'Create product' } })
    await waitFor(() => expect(screen.queryByText('List products')).toBeNull())
    expect(screen.getByText('Create product')).toBeTruthy()
  })
})