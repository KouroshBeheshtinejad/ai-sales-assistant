import { Link } from 'react-router-dom'
import { DEMO_STORE_ID } from '../components/Layout'
import { useSeo } from '../lib/hooks'
import { useI18n } from '../lib/i18n'

export default function Landing() {
  const { t } = useI18n()
  useSeo({ title: 'NAVA | AI commerce', description: t('landing.lead') })

  const steps = [1, 2, 3, 4]
  return (
    <>
      <section className="wrap hero">
        <div>
          <h1>{t('landing.title')}</h1>
          <p className="lead">{t('landing.lead')}</p>
          <div className="row">
            <Link className="btn btn-primary" to={`/store/${DEMO_STORE_ID}`}>{t('landing.cta')}</Link>
            <Link className="btn" to="/register">{t('landing.ctaSeller')}</Link>
          </div>
        </div>

        <div className="demo-chat" aria-hidden="true">
          <div className="bubble user">{t('landing.q1')}</div>
          <div className="bubble assistant">{t('landing.a1')}</div>
          <div className="bubble user">{t('landing.q2')}</div>
          <div className="bubble assistant">{t('landing.a2')}</div>
        </div>
      </section>

      <section className="wrap section">
        <h2>{t('landing.how')}</h2>
        <ol className="steps">
          {steps.map((n) => (
            <li key={n}>
              <h3>{t(`landing.h${n}`)}</h3>
              <p>{t(`landing.d${n}`)}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="wrap section split">
        <div>
          <h2>{t('landing.sellers')}</h2>
          <p>{t('landing.sellersBody')}</p>
        </div>
        <div>
          <h2>{t('landing.buyers')}</h2>
          <p>{t('landing.buyersBody')}</p>
        </div>
      </section>
    </>
  )
}
