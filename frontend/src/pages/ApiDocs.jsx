import { useEffect, useMemo, useState } from 'react'
import { useSeo } from '../lib/hooks'
import { useI18n } from '../lib/i18n'
import { Button, Field, Loading } from '../components/ui'

const METHODS = ['get', 'post', 'put', 'patch', 'delete']

function resolveSchema(schema, components) {
  if (!schema) return null
  const reference = schema.$ref?.split('/').at(-1)
  return reference ? components?.schemas?.[reference] || schema : schema
}

function Endpoint({ path, method, operation, components, securitySchemes, t }) {
  const parameters = operation.parameters || []
  const requestBodies = Object.entries(operation.requestBody?.content || {}).map(([contentType, value]) => ({
    contentType,
    schema: resolveSchema(value.schema, components),
  }))
  const responses = operation.responses || {}
  const tags = operation.tags || []
  const security = operation.security || []

  return (
    <details className="card api-endpoint">
      <summary className="api-endpoint-summary">
        <span className={`api-method api-method-${method}`}>{method.toUpperCase()}</span>
        <code dir="ltr">{path}</code>
        <span className="api-endpoint-title">{operation.summary || operation.operationId || path}</span>
      </summary>
      <div className="api-endpoint-body">
        {operation.description && <p className="muted">{operation.description}</p>}
        {tags.length > 0 && <p className="api-meta">{t('apiDocs.group')}: {tags.join(', ')}</p>}
        <p className="api-meta">{t('apiDocs.authentication')}: {security.length ? security.flatMap((requirement) => Object.keys(requirement)).map((name) => securitySchemes?.[name]?.bearerFormat ? `${name} (${securitySchemes[name].bearerFormat})` : name).join(', ') : t('apiDocs.none')}</p>
        {parameters.length > 0 && <section className="api-detail-section">
          <h3>{t('apiDocs.parameters')}</h3>
          <ul className="plain-list">{parameters.map((parameter) => <li key={`${parameter.in}-${parameter.name}`}>
            <span><code dir="ltr">{parameter.name}</code> · {parameter.in}{parameter.required ? ` · ${t('apiDocs.required')}` : ''}</span>
            <span className="muted">{parameter.description || parameter.schema?.type || ''}</span>
          </li>)}</ul>
        </section>}
        {requestBodies.map(({ contentType, schema }) => <section className="api-detail-section" key={contentType}>
          <h3>{t('apiDocs.requestBody')} · <code dir="ltr">{contentType}</code></h3>
          {schema && <pre dir="ltr">{JSON.stringify(schema, null, 2)}</pre>}
        </section>)}
        <section className="api-detail-section">
          <h3>{t('apiDocs.responses')}</h3>
          <ul className="plain-list">{Object.entries(responses).map(([code, response]) => <li key={code}>
            <code dir="ltr">{code}</code><span>{response.description || ''}</span>
          </li>)}</ul>
        </section>
      </div>
    </details>
  )
}

export default function ApiDocs() {
  const { t } = useI18n()
  const [spec, setSpec] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [tagFilter, setTagFilter] = useState('all')
  useSeo({ title: `${t('apiDocs.title')} | NAVA`, description: t('apiDocs.lead') })

  useEffect(() => {
    const controller = new AbortController()
    fetch('/openapi.json', { headers: { Accept: 'application/json' }, signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json()
      })
      .then(setSpec)
      .catch((cause) => { if (cause.name !== 'AbortError') setError(cause.message) })
    return () => controller.abort()
  }, [])

  const operations = useMemo(() => {
    const entries = []
    for (const [path, pathItem] of Object.entries(spec?.paths || {})) {
      if (!path.startsWith('/api/')) continue
      for (const method of METHODS) {
        const operation = pathItem[method]
        if (operation) entries.push({ path, method, operation })
      }
    }
    return entries
  }, [spec])

  const tags = [...new Set(operations.flatMap(({ operation }) => operation.tags || []))].sort()
  const filtered = operations.filter(({ path, method, operation }) => {
    const haystack = `${path} ${method} ${operation.summary || ''} ${operation.description || ''} ${(operation.tags || []).join(' ')}`.toLowerCase()
    return haystack.includes(query.trim().toLowerCase()) && (tagFilter === 'all' || (operation.tags || []).includes(tagFilter))
  })
  const groups = filtered.reduce((result, endpoint) => {
    const key = endpoint.operation.tags?.[0] || t('apiDocs.untagged')
    result[key] ||= []
    result[key].push(endpoint)
    return result
  }, {})

  return (
    <div className="wrap api-docs page-narrow">
      <header className="page-head"><div><h1>{t('apiDocs.title')}</h1><p className="muted">{t('apiDocs.lead')}</p></div></header>
      <div className="api-docs-tools">
        <Field label={t('apiDocs.search')}><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} /></Field>
        <Field label={t('apiDocs.category')}>
          <select value={tagFilter} onChange={(event) => setTagFilter(event.target.value)}>
            <option value="all">{t('apiDocs.all')}</option>
            {tags.map((tag) => <option key={tag} value={tag}>{tag}</option>)}
          </select>
        </Field>
        <a className="btn btn-ghost" href="/docs" target="_blank" rel="noreferrer">{t('apiDocs.interactive')}</a>
      </div>
      {error && <p className="notice notice-danger" role="alert">{t('apiDocs.loadError')}: {error}</p>}
      {!spec && !error && <Loading />}
      {spec && <p className="api-count">{t('apiDocs.endpointCount', { count: filtered.length, version: spec.info?.version || '' })}</p>}
      {spec && Object.entries(groups).map(([group, endpoints]) => (
        <section className="api-group" key={group}>
          <h2>{group}</h2>
          <div className="api-endpoint-list">{endpoints.map((endpoint) => <Endpoint key={`${endpoint.method}:${endpoint.path}`} {...endpoint} components={spec.components} securitySchemes={spec.components?.securitySchemes} t={t} />)}</div>
        </section>
      ))}
      {spec && !filtered.length && <p className="muted">{t('apiDocs.noResults')}</p>}
      <Button variant="ghost" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>{t('footer.top')}</Button>
    </div>
  )
}