import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { cx, safeStorage } from '../lib/util'
import { Button, Icon } from './ui'

const MAX_SAVED = 60
const storageKey = (storeId) => `nava_chat_${storeId}`
const loadHistory = (storeId) => {
  try { return JSON.parse(safeStorage.get(storageKey(storeId)) || '[]') } catch { return [] }
}
const SUGGESTIONS = ['chat.s1', 'chat.s2', 'chat.s3', 'chat.s4']

// The server keeps the conversation but has no endpoint to read it back for guests,
// so the transcript is mirrored in localStorage to survive a page reload.
export default function ChatDock({ shop, storeName, open, onClose, draft, onDraftUsed }) {
  const { t, err } = useI18n()
  const { storeId } = shop
  const [messages, setMessages] = useState(() => loadHistory(storeId))
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)
  const logRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    safeStorage.set(storageKey(storeId), JSON.stringify(messages.filter((m) => !m.error).slice(-MAX_SAVED)))
  }, [messages, storeId])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [messages, busy])

  useEffect(() => {
    if (!draft) return
    setValue(draft)
    inputRef.current?.focus()
    onDraftUsed()
  }, [draft, onDraftUsed])

  const send = async (text) => {
    const question = text.trim()
    if (!question || busy) return
    setValue('')
    setBusy(true)
    setMessages((list) => [...list, { role: 'user', content: question }])
    const hadItems = shop.cartCount > 0
    try {
      const res = await api.chat(storeId, question, shop.getGuestToken())
      shop.remember(res.guest_token)
      setMessages((list) => [...list, { role: 'assistant', content: res.answer }])
      const cart = await shop.refreshCart()
      if (hadItems && cart && cart.items.length === 0) shop.reloadCatalog() // an order was placed in chat: stock changed
    } catch (error) {
      setMessages((list) => [...list, { role: 'assistant', content: err(error), error: true }])
    } finally {
      setBusy(false)
      inputRef.current?.focus()
    }
  }

  return (
    <aside className={cx('chat', open && 'is-open')} aria-label={t('chat.title')}>
      <header className="chat-head">
        <span className="chat-avatar" aria-hidden="true">{(storeName || '؟').charAt(0)}</span>
        <div>
          <strong>{t('chat.title')}</strong>
          <span>{storeName}</span>
        </div>
        <button type="button" className="icon-btn chat-close" onClick={onClose} aria-label={t('close')}><Icon name="close" /></button>
      </header>

      <div className="chat-log" ref={logRef} role="log" aria-live="polite">
        <div className="bubble assistant">{t('chat.welcome', { store: storeName || '' })}</div>
        {messages.map((m, i) => <div key={i} className={cx('bubble', m.role, m.error && 'error')}>{m.content}</div>)}
        {busy && <div className="bubble assistant typing" role="status" aria-label={t('chat.typing')}><i /><i /><i /></div>}
      </div>

      {messages.length === 0 && (
        <div className="chips">
          {SUGGESTIONS.map((key) => <button key={key} type="button" className="chip" onClick={() => send(t(key))}>{t(key)}</button>)}
        </div>
      )}

      <form className="chat-form" onSubmit={(event) => { event.preventDefault(); send(value) }}>
        <input ref={inputRef} value={value} onChange={(e) => setValue(e.target.value)} maxLength={1000} autoComplete="off" placeholder={t('chat.placeholder')} aria-label={t('chat.placeholder')} />
        <Button type="submit" variant="primary" disabled={busy || !value.trim()} aria-label={t('chat.send')}><Icon name="send" /></Button>
      </form>
    </aside>
  )
}
