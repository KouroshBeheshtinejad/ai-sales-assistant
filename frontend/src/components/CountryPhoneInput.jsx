import { flagEmoji, phoneCountries } from '../lib/phoneNumbers'
import { useI18n } from '../lib/i18n'

export default function CountryPhoneInput({ id, value, country, onCountryChange, onValueChange, ...inputProps }) {
  const { t, locale } = useI18n()
  return (
    <div className="country-phone-input" dir="ltr">
      <select aria-label={t('auth.phoneCountry')} value={country} onChange={onCountryChange}>
        {phoneCountries(locale).map((option) => (
          <option key={option.country} value={option.country}>{flagEmoji(option.country)} {option.name} (+{option.callingCode})</option>
        ))}
      </select>
      <input
        {...inputProps}
        id={id}
        type="tel"
        inputMode="tel"
        autoComplete="tel-national"
        value={value}
        onChange={onValueChange}
      />
    </div>
  )
}