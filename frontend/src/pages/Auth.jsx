import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Button, Field } from '../components/ui'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useSeo } from '../lib/hooks'
import { useI18n } from '../lib/i18n'
import { safeNext, toLatinDigits } from '../lib/util'

// Receives id / aria-* from <Field>, so they are forwarded to the real input.
function PasswordInput({ minLength = 8, ...rest }) {
  const { t } = useI18n()
  const [visible, setVisible] = useState(false)
  return (
    <span className="input-affix">
      <input {...rest} type={visible ? 'text' : 'password'} required minLength={minLength} dir="ltr" />
      <button type="button" className="affix-btn" onClick={() => setVisible(!visible)}>{visible ? t('hide') : t('show')}</button>
    </span>
  )
}

function useSubmit(action) {
  const { err } = useI18n()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try { await action() } catch (e) { setError(err(e)); return e } finally { setBusy(false) }
    return null
  }
  return { busy, error, submit, setError }
}

const Notice = ({ error, info }) => (
  <>
    {info && <p className="notice notice-ok" role="status">{info}</p>}
    {error && <p className="notice notice-danger" role="alert">{error}</p>}
  </>
)

export default function AuthPage({ initial }) {
  const { t } = useI18n()
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [step, setStep] = useState(initial === 'register' ? 'register' : params.get('mode') || 'login')
  const [info, setInfo] = useState('')
  const [account, setAccount] = useState({ email: params.get('email') || '', password: '', phone: '', channels: ['email'] })
  const next = safeNext(params.get('next'))

  useSeo({ title: `${t(step === 'register' ? 'auth.registerTitle' : 'auth.loginTitle')} | NAVA` })

  const go = (nextStep, message = '') => { setStep(nextStep); setInfo(message) }
  const finishLogin = async (email, password) => {
    const data = await api.login({ email, password })
    signIn(data.access_token)
    navigate(next, { replace: true })
  }

  return (
    <div className="wrap auth">
      <div className="card auth-card">
        {step === 'login' && <LoginForm account={account} setAccount={setAccount} info={info} go={go} finishLogin={finishLogin} />}
        {step === 'register' && <RegisterForm account={account} setAccount={setAccount} go={go} />}
        {step === 'verify' && <VerifyForm account={account} go={go} finishLogin={finishLogin} info={info} />}
        {step === 'forgot' && <ForgotForm account={account} setAccount={setAccount} go={go} />}
        {step === 'reset' && <ResetForm go={go} initialToken={params.get('token') || ''} />}
      </div>
    </div>
  )
}

function LoginForm({ account, setAccount, info, go, finishLogin }) {
  const { t } = useI18n()
  const { busy, error, submit } = useSubmit(() => finishLogin(account.email.trim(), account.password))
  const onSubmit = async (event) => {
    const failure = await submit(event)
    if (failure?.status === 403) go('verify', t('auth.unverified')) // registered but never verified
  }
  return (
    <form className="stack" onSubmit={onSubmit}>
      <h1>{t('auth.loginTitle')}</h1>
      <Notice info={info} error={error} />
      <Field label={t('auth.email')}><input type="email" required autoComplete="email" dir="ltr" value={account.email} onChange={(e) => setAccount({ ...account, email: e.target.value })} /></Field>
      <Field label={t('auth.password')}><PasswordInput autoComplete="current-password" value={account.password} onChange={(e) => setAccount({ ...account, password: e.target.value })} /></Field>
      <Button type="submit" variant="primary" busy={busy}>{t('auth.loginSubmit')}</Button>
      <button type="button" className="link-btn" onClick={() => go('forgot')}>{t('auth.forgot')}</button>
      <p className="muted">{t('auth.noAccount')} <Link to="/register">{t('nav.register')}</Link></p>
    </form>
  )
}

function RegisterForm({ account, setAccount, go }) {
  const { t } = useI18n()
  const { busy, error, submit } = useSubmit(async () => {
    const phone = toLatinDigits(account.phone).trim()
    const res = await api.register({ email: account.email.trim(), password: account.password, phone: phone || undefined })
    setAccount({ ...account, phone, channels: res.channels || ['email'] })
    go('verify')
  })
  return (
    <form className="stack" onSubmit={submit}>
      <h1>{t('auth.registerTitle')}</h1>
      <Notice error={error} />
      <Field label={t('auth.email')}><input type="email" required autoComplete="email" dir="ltr" value={account.email} onChange={(e) => setAccount({ ...account, email: e.target.value })} /></Field>
      <Field label={`${t('auth.phone')} (${t('optional')})`} hint={t('auth.phoneHint')}><input type="tel" inputMode="tel" minLength={5} maxLength={50} autoComplete="tel" dir="ltr" value={account.phone} onChange={(e) => setAccount({ ...account, phone: e.target.value })} /></Field>
      <Field label={t('auth.password')} hint={t('auth.passwordHint')}><PasswordInput autoComplete="new-password" value={account.password} onChange={(e) => setAccount({ ...account, password: e.target.value })} /></Field>
      <Button type="submit" variant="primary" busy={busy}>{t('auth.registerSubmit')}</Button>
      <p className="muted">{t('auth.haveAccount')} <Link to="/login">{t('nav.login')}</Link></p>
    </form>
  )
}

function VerifyForm({ account, go, finishLogin, info }) {
  const { t } = useI18n()
  const needsPhone = account.channels.includes('phone')
  const [codes, setCodes] = useState({ email: '', phone: '' })
  const [localError, setLocalError] = useState('')
  const { busy, error, submit } = useSubmit(async () => {
    const emailCode = toLatinDigits(codes.email).trim()
    const phoneCode = toLatinDigits(codes.phone).trim()
    if (!/^\d{8}$/.test(emailCode) || (needsPhone && !/^\d{8}$/.test(phoneCode))) { setLocalError(t('form.otp')); return }
    setLocalError('')
    await api.verify({ email: account.email.trim(), email_code: emailCode, phone_code: needsPhone ? phoneCode : undefined })
    if (account.password) await finishLogin(account.email.trim(), account.password) // still in memory after sign-up
    else go('login', t('auth.verified'))
  })
  const digits = (name) => (e) => setCodes({ ...codes, [name]: e.target.value })
  return (
    <form className="stack" onSubmit={submit}>
      <h1>{t('auth.verifyTitle')}</h1>
      <p className="muted">{t('auth.verifyLead', { email: account.email })}</p>
      <Notice info={info} error={localError || error} />
      <Field label={t('auth.emailCode')}><input required inputMode="numeric" autoComplete="one-time-code" maxLength={8} dir="ltr" className="otp" value={codes.email} onChange={digits('email')} data-autofocus /></Field>
      {needsPhone && <Field label={t('auth.phoneCode')}><input required inputMode="numeric" maxLength={8} dir="ltr" className="otp" value={codes.phone} onChange={digits('phone')} /></Field>}
      <Button type="submit" variant="primary" busy={busy}>{t('auth.verifySubmit')}</Button>
      {import.meta.env.DEV && <p className="field-hint">{t('auth.devHint')}</p>}
      <button type="button" className="link-btn" onClick={() => go('login')}>{t('auth.backToLogin')}</button>
    </form>
  )
}

function ForgotForm({ account, setAccount, go }) {
  const { t } = useI18n()
  const [sent, setSent] = useState(false)
  const { busy, error, submit } = useSubmit(async () => { await api.requestReset(account.email.trim()); setSent(true) })
  return (
    <form className="stack" onSubmit={submit}>
      <h1>{t('auth.forgotTitle')}</h1>
      <p className="muted">{t('auth.forgotLead')}</p>
      <Notice error={error} info={sent ? t('auth.forgotSent') : ''} />
      <Field label={t('auth.email')}><input type="email" required autoComplete="email" dir="ltr" value={account.email} onChange={(e) => setAccount({ ...account, email: e.target.value })} /></Field>
      <Button type="submit" variant="primary" busy={busy}>{t('auth.forgotSubmit')}</Button>
      {sent && <button type="button" className="link-btn" onClick={() => go('reset')}>{t('auth.haveToken')}</button>}
      <button type="button" className="link-btn" onClick={() => go('login')}>{t('auth.backToLogin')}</button>
    </form>
  )
}

function ResetForm({ go, initialToken }) {
  const { t } = useI18n()
  const [token, setToken] = useState(initialToken)
  const [password, setPassword] = useState('')
  const { busy, error, submit } = useSubmit(async () => {
    await api.confirmReset(token.trim(), password)
    go('login', t('auth.resetDone'))
  })
  return (
    <form className="stack" onSubmit={submit}>
      <h1>{t('auth.resetTitle')}</h1>
      <Notice error={error} />
      <Field label={t('auth.resetToken')}><input required minLength={32} maxLength={255} dir="ltr" value={token} onChange={(e) => setToken(e.target.value)} /></Field>
      <Field label={t('auth.newPassword')} hint={t('auth.passwordHint')}><PasswordInput autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
      <Button type="submit" variant="primary" busy={busy}>{t('auth.resetSubmit')}</Button>
      <button type="button" className="link-btn" onClick={() => go('login')}>{t('auth.backToLogin')}</button>
    </form>
  )
}
