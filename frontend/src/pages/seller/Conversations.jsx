import { Link, useParams } from 'react-router-dom'
import { Async, Badge, Empty } from '../../components/ui'
import { api } from '../../lib/api'
import { useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { cx, parseDate } from '../../lib/util'
import { useSeller } from './SellerContext'
import { NeedStore, PageHead } from './SellerLayout'

const STATE_TONE = { idle: 'neutral', awaiting_customer: 'warn', awaiting_confirmation: 'warn', completed: 'ok' }
const StateBadge = ({ value }) => {
  const { t } = useI18n()
  return <Badge tone={STATE_TONE[value] || 'neutral'}>{t(`cs.${value}`)}</Badge>
}

export function Conversations() {
  const { t, id, num, date } = useI18n()
  const { store } = useSeller()
  useSeo({ title: `${t('s.conversations')} | NAVA` })
  const state = useAsync(() => (store ? api.seller.conversations(store.id) : null), [store?.id])
  if (!store) return <NeedStore />

  return (
    <>
      <PageHead title={t('s.conversations')} />
      <Async state={state}>
        {(list) => !list.length ? <Empty title={t('c.empty')} /> : (
          <ul className="list-cards">
            {list.map((c) => {
              const last = c.messages[c.messages.length - 1]
              return (
                <li key={c.id} className="card">
                  <div className="row between">
                    <Link to={`/seller/conversation/${c.id}`}><strong>{t('c.guest', { id: id(c.id) })}</strong></Link>
                    <StateBadge value={c.checkout_state} />
                  </div>
                  <p className="clamp">{last ? last.content : t('c.noMessages')}</p>
                  <div className="row muted">
                    <span>{t('c.messages', { n: num(c.messages.length) })}</span>
                    <span>{date(parseDate(c.updated_at))}</span>
                    {c.last_order_id && <Link to={`/seller/order/${c.last_order_id}`}>{t('c.order', { id: id(c.last_order_id) })}</Link>}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </Async>
    </>
  )
}

export function ConversationDetail() {
  const { conversationId } = useParams()
  const { t, id, date } = useI18n()
  const state = useAsync(() => api.seller.conversation(conversationId), [conversationId])
  useSeo({ title: `${t('c.guest', { id: id(conversationId) })} | NAVA` })

  return (
    <>
      <Link className="back-link" to="/seller/conversations">{t('s.conversations')}</Link>
      <Async state={state}>
        {(c) => (
          <>
            <PageHead title={t('c.guest', { id: id(c.id) })} actions={<><StateBadge value={c.checkout_state} />{c.last_order_id && <Link className="btn btn-sm" to={`/seller/order/${c.last_order_id}`}>{t('c.order', { id: id(c.last_order_id) })}</Link>}</>} />
            <div className="card transcript" role="log">
              {c.messages.map((m) => (
                <div key={m.id} className={cx('bubble', m.role === 'user' ? 'user' : 'assistant')}>
                  <small>{t(`c.${m.role}`)} · {date(parseDate(m.created_at))}</small>
                  {m.content}
                </div>
              ))}
            </div>
          </>
        )}
      </Async>
    </>
  )
}

export default Conversations
