import { Link } from 'react-router-dom'
import { DEMO_STORE_ID } from '../components/Layout'
import { ProductVisual, StockBadge } from '../components/ProductCard'
import { Button, Icon, Swatch } from '../components/ui'
import { useBusinessTypes, useSeo, useShowcase } from '../lib/hooks'
import { LOCALES, useI18n } from '../lib/i18n'
import { cx } from '../lib/util'

const FEATURES = [
  ['search', 'f1'], ['shield', 'f2'], ['chat', 'f3'], ['doc', 'f4'],
  ['layers', 'f5'], ['tag', 'f6'], ['globe', 'f7'], ['lock', 'f8'],
]
const STEPS = [1, 2, 3, 4]
const FAQ = [1, 2, 3, 4, 5, 6]
const TYPE_CHIPS = 14

function Tick({ children }) {
  return <li><span className="tick"><Icon name="check" size={14} /></span>{children}</li>
}

function SectionHead({ id, title, lead, action }) {
  return (
    <div className="section-head">
      <div>
        <h2 id={id}>{title}</h2>
        {lead && <p className="lead">{lead}</p>}
      </div>
      {action}
    </div>
  )
}

function Hero() {
  const { t } = useI18n()
  return (
    <section className="hero-wrap">
      <div className="wrap hero">
        <div className="hero-copy">
          <span className="eyebrow"><Icon name="sparkle" size={16} />{t('landing.badge')}</span>
          <h1>{t('landing.title')}</h1>
          <p className="lead">{t('landing.lead')}</p>
          <div className="row">
            <Link className="btn btn-primary btn-lg" to={`/store/${DEMO_STORE_ID}`}>{t('landing.cta')}<Icon name="arrow" size={18} className="flip-rtl" /></Link>
            <Link className="btn btn-lg" to="/register">{t('landing.ctaSeller')}</Link>
          </div>
          <ul className="ticks">
            <Tick>{t('landing.b1')}</Tick>
            <Tick>{t('landing.b2')}</Tick>
            <Tick>{t('landing.b3')}</Tick>
          </ul>
        </div>

        <div className="hero-art">
          <div className="demo-chat">
            <div className="bubble user">{t('landing.q1')}</div>
            <div className="bubble assistant">{t('landing.a1')}</div>
            <div className="bubble user">{t('landing.q2')}</div>
            <div className="bubble assistant">{t('landing.a2')}</div>
          </div>
          <span className="float-chip chip-a"><Icon name="check" size={16} />{t('landing.chipStock')}</span>
          <span className="float-chip chip-b"><Icon name="box" size={16} />{t('landing.chipOrder')}</span>
          <span className="float-chip chip-c"><Icon name="truck" size={16} />{t('landing.chipTracking')}</span>
        </div>
      </div>
    </section>
  )
}

function Stats({ showcase, typeCount }) {
  const { t, num } = useI18n()
  const live = showcase.data?.stats
  const items = [
    live && [t('landing.stat.stores'), live.stores],
    live && [t('landing.stat.products'), live.products],
    typeCount > 0 && [t('landing.stat.types'), typeCount],
    [t('landing.stat.languages'), LOCALES.length],
  ].filter(Boolean)
  return (
    <section className="wrap" aria-label="NAVA">
      <dl className="statbar">
        {items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{num(value)}</dd></div>)}
      </dl>
    </section>
  )
}

function How() {
  const { t } = useI18n()
  return (
    <section className="wrap section" id="how" aria-labelledby="how-title">
      <SectionHead id="how-title" title={t('landing.how')} lead={t('landing.howLead')} />
      <ol className="steps">
        {STEPS.map((n) => (
          <li key={n}>
            <h3>{t(`landing.h${n}`)}</h3>
            <p>{t(`landing.d${n}`)}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}

function Features({ typeCount }) {
  const { t } = useI18n()
  return (
    <section className="band" id="features" aria-labelledby="features-title">
      <div className="wrap section">
        <SectionHead id="features-title" title={t('landing.features')} lead={t('landing.featuresLead')} />
        <ul className="feature-grid">
          {FEATURES.map(([icon, key]) => (
            <li key={key} className="feature">
              <span className="feature-icon"><Icon name={icon} size={22} /></span>
              <h3>{t(`landing.${key}.t`, { n: typeCount || 49 })}</h3>
              <p>{t(`landing.${key}.d`)}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

function Assistant() {
  const { t } = useI18n()
  return (
    <section className="wrap section split-feature" aria-labelledby="assistant-title">
      <div className="stack">
        <h2 id="assistant-title">{t('landing.assistant')}</h2>
        <p className="lead">{t('landing.assistantBody')}</p>
        <ul className="ticks">
          {[1, 2, 3, 4].map((n) => <Tick key={n}>{t(`landing.can${n}`)}</Tick>)}
        </ul>
      </div>
      <div className="demo-chat">
        <div className="bubble user">{t('landing.q3')}</div>
        <div className="bubble assistant">{t('landing.a3')}</div>
        <div className="bubble user">{t('landing.q4')}</div>
        <div className="bubble assistant">{t('landing.a4')}</div>
      </div>
    </section>
  )
}

function StoreCard({ store, types }) {
  const { t, num, bizLabel } = useI18n()
  const label = bizLabel(store.business_type, types.find((x) => x.slug === store.business_type)?.label)
  return (
    <li className="store-card">
      {store.logo_url
        ? <img className="store-mark" src={store.logo_url} alt="" loading="lazy" />
        : <Swatch className="store-mark" seed={store.name} label={store.name} />}
      <div className="store-card-body">
        <h3><Link className="cover-link" to={`/store/${store.id}`}>{store.name}</Link></h3>
        <p className="muted">{label} · {t('landing.productsCount', { n: num(store.product_count) })}</p>
        {store.description && <p className="clamp">{store.description}</p>}
        <span className="store-card-cta">{t('landing.visit')}<Icon name="arrow" size={16} className="flip-rtl" /></span>
      </div>
    </li>
  )
}

function Skeletons({ count, className }) {
  return Array.from({ length: count }, (_, i) => <li key={i} className={cx('skeleton', className)} aria-hidden="true" />)
}

function Showcase({ showcase, types }) {
  const { t, money } = useI18n()
  const { data, loading, error, shuffle } = showcase
  const stores = data?.stores || []
  const products = data?.products || []
  const firstLoad = loading && !data
  if (error && !data) return null // marketing page stays clean when the API is unreachable

  return (
    <>
      <section className="wrap section" id="stores" aria-labelledby="stores-title" aria-busy={loading}>
        <SectionHead
          id="stores-title"
          title={t('landing.stores')}
          lead={t('landing.storesLead')}
          action={<Button onClick={shuffle} busy={loading && Boolean(data)}><Icon name="shuffle" size={18} />{t('landing.shuffle')}</Button>}
        />
        {!firstLoad && !stores.length ? (
          <div className="card empty-card">
            <p>{t('landing.storesEmpty')}</p>
            <Link className="btn btn-primary" to="/register">{t('landing.ctaSeller')}</Link>
          </div>
        ) : (
          <ul className="store-grid">
            {firstLoad ? <Skeletons count={3} className="skeleton-store" /> : stores.map((store) => <StoreCard key={store.id} store={store} types={types} />)}
          </ul>
        )}
      </section>

      {(firstLoad || products.length > 0) && (
        <section className="wrap section tight" id="products" aria-labelledby="products-title">
          <SectionHead id="products-title" title={t('landing.products')} lead={t('landing.productsLead')} />
          <ul className="mini-grid">
            {firstLoad ? <Skeletons count={4} className="skeleton-product" /> : products.map((product) => (
              <li key={product.id} className="mini-product">
                <div className="mini-media"><ProductVisual product={product} /></div>
                <div className="mini-body">
                  <h3><Link className="cover-link" to={`/store/${product.store_id}/product/${product.id}`}>{product.name}</Link></h3>
                  <p className="muted">{t('landing.by', { store: product.store_name })}</p>
                  <div className="product-meta">
                    <strong className="price">{money(product.price)}</strong>
                    <StockBadge stock={product.stock} />
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}

function Types({ types }) {
  const { t, num, bizLabel } = useI18n()
  if (!types.length) return null
  const shown = types.slice(0, TYPE_CHIPS)
  return (
    <section className="band band-soft" id="types" aria-labelledby="types-title">
      <div className="wrap section center-head">
        <h2 id="types-title">{t('landing.types')}</h2>
        <p className="lead">{t('landing.typesLead', { n: types.length })}</p>
        <ul className="type-chips">
          {shown.map((type) => <li key={type.slug}>{bizLabel(type.slug, type.label)}</li>)}
          {types.length > shown.length && <li className="more">{t('landing.typesMore', { n: num(types.length - shown.length) })}</li>}
        </ul>
      </div>
    </section>
  )
}

function Audience() {
  const { t } = useI18n()
  const cards = [
    ['store', 'landing.sellers', 'landing.sellersBody', ['landing.s1', 'landing.s2', 'landing.s3']],
    ['users', 'landing.buyers', 'landing.buyersBody', ['landing.y1', 'landing.y2', 'landing.y3']],
  ]
  return (
    <section className="wrap section split">
      {cards.map(([icon, title, body, list]) => (
        <div key={title} className="card audience">
          <span className="feature-icon"><Icon name={icon} size={22} /></span>
          <h2 className="h3">{t(title)}</h2>
          <p className="muted">{t(body)}</p>
          <ul className="ticks">{list.map((key) => <Tick key={key}>{t(key)}</Tick>)}</ul>
        </div>
      ))}
    </section>
  )
}

function Faq() {
  const { t } = useI18n()
  return (
    <section className="wrap section narrow-section" id="faq" aria-labelledby="faq-title">
      <h2 id="faq-title" className="center">{t('landing.faq')}</h2>
      <div className="faq">
        {FAQ.map((n) => (
          <details key={n}>
            <summary>{t(`faq.q${n}`)}<Icon name="chevron" size={18} className="faq-caret" /></summary>
            <p>{t(`faq.a${n}`)}</p>
          </details>
        ))}
      </div>
    </section>
  )
}

function FinalCta() {
  const { t } = useI18n()
  return (
    <section className="wrap section">
      <div className="cta-band">
        <h2>{t('landing.ctaTitle')}</h2>
        <p>{t('landing.ctaBody')}</p>
        <div className="row center-row">
          <Link className="btn btn-accent btn-lg" to="/register">{t('landing.ctaSeller')}</Link>
          <Link className="btn btn-outline-light btn-lg" to={`/store/${DEMO_STORE_ID}`}>{t('landing.cta')}</Link>
        </div>
      </div>
    </section>
  )
}

export default function Landing() {
  const { t } = useI18n()
  const types = useBusinessTypes()
  const showcase = useShowcase(6, 8)
  useSeo({ title: 'NAVA | AI commerce', description: t('landing.lead') })

  return (
    <>
      <Hero />
      <Stats showcase={showcase} typeCount={types.length} />
      <How />
      <Features typeCount={types.length} />
      <Assistant />
      <Showcase showcase={showcase} types={types} />
      <Types types={types} />
      <Audience />
      <Faq />
      <FinalCta />
    </>
  )
}
