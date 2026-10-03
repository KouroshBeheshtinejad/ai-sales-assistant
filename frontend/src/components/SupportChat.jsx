import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../lib/i18n'
import { Button, Icon } from './ui'

export function SupportChatPanel({ conversation, title, subtitle, onReply, disabled = false, busy = false, children }) {
  const { t, date } = useI18n()
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const logRef = useRef(null)
  const sendingRef = useRef(false)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [conversation?.messages, busy])

  const submit = async (event) => {
    event.preventDefault()
    const content = message.trim()
    if (!content || busy || sendingRef.current) return
    sendingRef.current = true
    setSending(true)
    setError('')
    try {
      await onReply(content)
      setMessage('')
    } catch (cause) {
      setError(cause.message)
    } finally {
      sendingRef.current = false
      setSending(false)
    }
  }

  return (
    <section className="support-chat" aria-label={title || t('dash.messages')}>
      <header className="support-chat-head">
        <span className="chat-avatar" aria-hidden="true">{(title || '?').charAt(0)}</span>
        <div><strong>{title || t('dash.messages')}</strong>{subtitle && <span>{subtitle}</span>}</div>
        {children && <div className="support-chat-actions">{children}</div>}
      </header>
      <div className="support-chat-log" ref={logRef} role="log" aria-live="polite">
        {!conversation?.messages?.length && <p className="muted">{t('dash.noMessagesYet')}</p>}
        {conversation?.messages?.map((item) => (
          <article key={item.id} className={`support-message ${item.role === 'assistant' ? 'assistant' : 'user'}`}>
            <p>{item.content}</p>
            <time dateTime={item.created_at}>{date(new Date(item.created_at))}</time>
          </article>
        ))}
      </div>
      {onReply && <form className="support-chat-form" onSubmit={submit}>
        {error && <p className="notice notice-danger" role="alert">{error}</p>}
        <input value={message} onChange={(event) => setMessage(event.target.value)} maxLength={5000} autoComplete="off" disabled={disabled || sending || busy} placeholder={disabled ? t('dash.chatClosed') : t('dash.typeReply')} aria-label={t('dash.typeReply')} />
        <Button type="submit" variant="primary" busy={sending || busy} disabled={disabled || sending || busy || !message.trim()} aria-label={t('dash.reply')}><Icon name="send" size={18} /></Button>
      </form>}
    </section>
  )
}