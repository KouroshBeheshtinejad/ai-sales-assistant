import { useEffect, useState } from 'react'
import { Badge, Button, CaptchaField, ErrorNote, Field, Loading, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { useCaptcha, useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { toLatinDigits } from '../../lib/util'
import { PageHead } from './SellerLayout'

const emptyForm = {
  firstName: '', lastName: '', email: '', phone: '',
  nationalId: '', businessAddress: '', businessPhone: '',
  password: '', confirmPassword: '',
}

function fromProfile(profile) {
  return {
    firstName: profile.first_name || '',
    lastName: profile.last_name || '',
    email: profile.email || '',
    phone: profile.phone || '',
    nationalId: profile.national_id || '',
    businessAddress: profile.business_address || '',
    businessPhone: profile.business_phone || '',
    password: '',
    confirmPassword: '',
  }
}

function AccountForm({ profile, onSaved }) {
  const { t, err } = useI18n()
  const toast = useToast()
  const captcha = useCaptcha()
  const [form, setForm] = useState(() => fromProfile(profile))
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value })

  useEffect(() => { setForm(fromProfile(profile)) }, [profile])

  const submit = async (event) => {
    event.preventDefault()
    const nationalId = toLatinDigits(form.nationalId).trim()
    const phone = toLatinDigits(form.phone).trim()
    const businessPhone = toLatinDigits(form.businessPhone).trim()

    const next = {}
    if (!form.firstName.trim()) next.firstName = t('form.required')
    if (!form.lastName.trim()) next.lastName = t('form.required')
    if (!phone) next.phone = t('form.required')
    if (!/^\d{10}$/.test(nationalId)) next.nationalId = t('account.nationalIdInvalid')
    if (!form.businessAddress.trim()) next.businessAddress = t('form.required')
    if (!businessPhone) next.businessPhone = t('form.required')
    if ((form.password || form.confirmPassword) && form.password !== form.confirmPassword) next.confirmPassword = t('account.passwordMismatch')
    if ((form.password || form.confirmPassword) && form.password && form.password.length < 8) next.password = t('auth.passwordHint')
    setErrors(next)
    if (Object.keys(next).length) return

    setBusy(true)
    setFormError('')
    try {
      const res = await api.updateProfile({
        first_name: form.firstName.trim(),
        last_name: form.lastName.trim(),
        email: form.email.trim(),
        phone,
        national_id: nationalId,
        business_address: form.businessAddress.trim(),
        business_phone: businessPhone,
        password: form.password || undefined,
        confirm_password: form.password ? form.confirmPassword : undefined,
        captcha_token: captcha.token,
        captcha_answer: captcha.answer,
      })
      toast(res.verification_required ? t('account.savedNeedsVerify') : t('account.saved'))
      setForm((f) => ({ ...f, password: '', confirmPassword: '' }))
      onSaved()
    } catch (e) {
      setFormError(err(e))
    } finally {
      setBusy(false)
      captcha.refresh()
    }
  }

  return (
    <form className="stack card account-form" onSubmit={submit}>
      {formError && <p className="notice notice-danger" role="alert">{formError}</p>}

      <h2 className="h3">{t('account.personal')}</h2>
      <div className="form-grid">
        <Field label={t('auth.firstName')} error={errors.firstName}><input required maxLength={120} autoComplete="given-name" value={form.firstName} onChange={set('firstName')} /></Field>
        <Field label={t('auth.lastName')} error={errors.lastName}><input required maxLength={120} autoComplete="family-name" value={form.lastName} onChange={set('lastName')} /></Field>
      </div>
      <div className="form-grid">
        <Field label={t('auth.email')}><input type="email" required autoComplete="email" dir="ltr" value={form.email} onChange={set('email')} /></Field>
        <Field label={t('auth.phone')} error={errors.phone}><input type="tel" inputMode="tel" required dir="ltr" autoComplete="tel" value={form.phone} onChange={set('phone')} /></Field>
      </div>
      <Field label={t('account.nationalId')} hint={t('account.nationalIdHint')} error={errors.nationalId}>
        <input inputMode="numeric" required dir="ltr" maxLength={10} value={form.nationalId} onChange={set('nationalId')} />
      </Field>

      <h2 className="h3">{t('account.business')}</h2>
      <Field label={t('account.businessAddress')} error={errors.businessAddress} className="full">
        <textarea rows={3} required value={form.businessAddress} onChange={set('businessAddress')} />
      </Field>
      <Field label={t('account.businessPhone')} error={errors.businessPhone}>
        <input type="tel" inputMode="tel" required dir="ltr" value={form.businessPhone} onChange={set('businessPhone')} />
      </Field>

      <h2 className="h3">{t('account.security')}</h2>
      <p className="muted">{t('account.passwordHint')}</p>
      <div className="form-grid">
        <Field label={t('auth.password')} error={errors.password}><input type="password" autoComplete="new-password" dir="ltr" minLength={8} value={form.password} onChange={set('password')} /></Field>
        <Field label={t('account.confirmPassword')} error={errors.confirmPassword}><input type="password" autoComplete="new-password" dir="ltr" minLength={8} value={form.confirmPassword} onChange={set('confirmPassword')} /></Field>
      </div>

      <CaptchaField captcha={captcha} label={t('captcha.label')} hint={t('account.captchaHint')} />

      <div className="row">
        <Button type="submit" variant="primary" busy={busy}>{t('save')}</Button>
      </div>
    </form>
  )
}

export default function Account() {
  const { t } = useI18n()
  const profile = useAsync(() => api.me(), [])
  useSeo({ title: `${t('account.title')} | NAVA` })

  return (
    <>
      <PageHead
        title={t('account.title')}
        actions={profile.data && (
          <Badge tone={profile.data.profile_complete ? 'ok' : 'warn'}>
            {profile.data.profile_complete ? t('account.complete') : t('account.incomplete')}
          </Badge>
        )}
      />
      {profile.loading ? <Loading /> : profile.error ? <ErrorNote error={profile.error} onRetry={profile.reload} /> : (
        <AccountForm profile={profile.data} onSaved={profile.reload} />
      )}
    </>
  )
}
