import { useEffect, useState } from 'react'
import { Badge, Button, CaptchaField, ErrorNote, Field, Loading, useToast } from '../../components/ui'
import { api } from '../../lib/api'
import { currencyName, STORE_CURRENCIES } from '../../lib/currencies'
import { useCaptcha, useAsync, useSeo } from '../../lib/hooks'
import { useI18n } from '../../lib/i18n'
import { normalizePhoneNumber, splitPhoneNumber } from '../../lib/phoneNumbers'
import { toLatinDigits } from '../../lib/util'
import CountryPhoneInput from '../../components/CountryPhoneInput'
import { useSeller } from './SellerContext'
import { PageHead } from './SellerLayout'

const emptyForm = {
  firstName: '', lastName: '', email: '', phone: '',
  nationalId: '', businessAddress: '', businessPhone: '',
  password: '', confirmPassword: '',
}

function fromProfile(profile) {
  const phone = splitPhoneNumber(profile.phone)
  const businessPhone = splitPhoneNumber(profile.business_phone)
  return {
    firstName: profile.first_name || '',
    lastName: profile.last_name || '',
    email: profile.email || '',
    phone: phone.nationalNumber,
    phoneCountry: phone.country,
    nationalId: profile.national_id || '',
    businessAddress: profile.business_address || '',
    businessPhone: businessPhone.nationalNumber,
    businessPhoneCountry: businessPhone.country,
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
    const phone = normalizePhoneNumber(form.phone, form.phoneCountry)
    const businessPhone = normalizePhoneNumber(form.businessPhone, form.businessPhoneCountry)

    const next = {}
    if (!form.firstName.trim()) next.firstName = t('form.required')
    if (!form.lastName.trim()) next.lastName = t('form.required')
    if (!form.phone.trim()) next.phone = t('form.required')
    else if (!phone) next.phone = t('auth.phoneInvalid')
    if (!/^\d{10}$/.test(nationalId)) next.nationalId = t('account.nationalIdInvalid')
    if (!form.businessAddress.trim()) next.businessAddress = t('form.required')
    if (!form.businessPhone.trim()) next.businessPhone = t('form.required')
    else if (!businessPhone) next.businessPhone = t('auth.phoneInvalid')
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
        <Field label={t('auth.phone')} error={errors.phone}><CountryPhoneInput required value={form.phone} country={form.phoneCountry} onCountryChange={(e) => setForm({ ...form, phoneCountry: e.target.value })} onValueChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
      </div>
      <Field label={t('account.nationalId')} hint={t('account.nationalIdHint')} error={errors.nationalId}>
        <input inputMode="numeric" required dir="ltr" maxLength={10} value={form.nationalId} onChange={set('nationalId')} />
      </Field>

      <h2 className="h3">{t('account.business')}</h2>
      <Field label={t('account.businessAddress')} error={errors.businessAddress} className="full">
        <textarea rows={3} required value={form.businessAddress} onChange={set('businessAddress')} />
      </Field>
      <Field label={t('account.businessPhone')} error={errors.businessPhone}>
        <CountryPhoneInput required value={form.businessPhone} country={form.businessPhoneCountry} onCountryChange={(e) => setForm({ ...form, businessPhoneCountry: e.target.value })} onValueChange={(e) => setForm({ ...form, businessPhone: e.target.value })} />
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

function StorePaymentSettings() {
  const { t, err, locale } = useI18n()
  const toast = useToast()
  const { store } = useSeller()
  const settings = useAsync(
    () => store ? api.seller.paymentSettings(store.id) : Promise.resolve(null),
    [store?.id],
  )
  const [form, setForm] = useState({ country_code: 'IR', currency: 'IRT', provider: 'disabled', external_account_id: '', merchant_id: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!settings.data) return
    setForm((current) => ({
      ...current,
      country_code: settings.data.country_code || 'IR',
      currency: settings.data.currency || 'IRT',
      provider: settings.data.provider || 'disabled',
      external_account_id: '',
      merchant_id: '',
    }))
  }, [settings.data])

  const set = (name) => (event) => setForm((current) => ({ ...current, [name]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const payload = {
        country_code: form.country_code.trim().toUpperCase(),
        currency: form.currency.trim().toUpperCase(),
        provider: form.provider,
      }
      if (form.provider === 'zarinpal' && form.merchant_id.trim()) payload.merchant_id = form.merchant_id.trim()
      if (!['disabled', 'zarinpal'].includes(form.provider) && form.external_account_id.trim()) payload.external_account_id = form.external_account_id.trim()
      await api.seller.updatePaymentSettings(store.id, payload)
      toast(t('saved'))
      setForm((current) => ({ ...current, external_account_id: '', merchant_id: '' }))
      settings.reload()
    } catch (cause) {
      setError(err(cause))
    } finally {
      setBusy(false)
    }
  }

  if (!store) return null

  return (
    <section className="card stack" aria-labelledby="store-payment-title">
      <h2 id="store-payment-title" className="h3">{t('pay.settings')}</h2>
      {settings.loading ? <Loading /> : settings.error ? <ErrorNote error={settings.error} onRetry={settings.reload} /> : (
        <>
          {error && <p className="notice notice-danger" role="alert">{error}</p>}
          {settings.data?.status === 'active' && <p className="notice notice-ok" role="status">{t('pay.status.active')}</p>}
          {settings.data?.status === 'pending' && <p className="notice" role="status">{settings.data.provider === 'zarinpal' && settings.data.account_configured ? t('pay.status.resave') : `${t('pay.status.pending')} · ${t('pay.adapterPending')}`}</p>}
          {settings.data?.status === 'not_configured' && <p className="muted">{t('pay.status.disabled')}</p>}
          <form className="stack" onSubmit={submit}>
            <div className="form-grid">
              <Field label={t('pay.country')}><input required minLength={2} maxLength={2} pattern="[A-Za-z]{2}" value={form.country_code} onChange={set('country_code')} dir="ltr" /></Field>
              <Field label={t('pay.currency')}><select required value={form.currency} onChange={set('currency')} dir="ltr">
                {!STORE_CURRENCIES.includes(form.currency) && <option value={form.currency}>{form.currency}</option>}
                {STORE_CURRENCIES.map((code) => <option key={code} value={code} disabled={form.provider === 'zarinpal' && !['IRT', 'IRR'].includes(code)}>{code} · {currencyName(code, locale)}</option>)}
              </select></Field>
            </div>
            <Field label={t('pay.provider')}>
              <select value={form.provider} onChange={(event) => setForm((current) => ({
                ...current,
                provider: event.target.value,
                currency: event.target.value === 'zarinpal' && !['IRT', 'IRR'].includes(current.currency) ? 'IRT' : current.currency,
              }))}>
                {['disabled', 'zarinpal', 'stripe_connect', 'paypal_multiparty', 'adyen_platforms', 'mollie_connect', ...(import.meta.env.DEV ? ['mock'] : [])].map((provider) => (
                  <option key={provider} value={provider}>{t(`pay.provider.${provider}`)}</option>
                ))}
              </select>
            </Field>
            {form.provider === 'zarinpal' ? (
              <Field label={t('pay.credentialReference')} hint={t('pay.credentialHint')}>
                <input type="password" maxLength={36} value={form.merchant_id} onChange={set('merchant_id')} dir="ltr" autoComplete="new-password" />
              </Field>
            ) : !['disabled', 'mock'].includes(form.provider) ? (
              <Field label={t('pay.accountId')}>
                <input maxLength={255} value={form.external_account_id} onChange={set('external_account_id')} dir="ltr" autoComplete="off" />
              </Field>
            ) : null}
            <div className="row"><Button type="submit" variant="primary" busy={busy}>{t('pay.save')}</Button></div>
          </form>
        </>
      )}
    </section>
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
        <div className="stack">
          <AccountForm profile={profile.data} onSaved={profile.reload} />
          <StorePaymentSettings />
        </div>
      )}
    </>
  )
}
