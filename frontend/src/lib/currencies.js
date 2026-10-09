export const STORE_CURRENCIES = [
  'IRT', 'IRR', 'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'NZD', 'CHF', 'JPY',
  'CNY', 'INR', 'KRW', 'SGD', 'HKD', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK',
  'TRY', 'AED', 'SAR', 'QAR', 'KWD', 'EGP', 'PKR', 'BRL', 'MXN', 'ZAR',
  'IDR', 'THB',
]

export function currencyName(code, locale) {
  if (code === 'IRT') return locale === 'fa' ? 'تومان' : 'Iranian toman'
  try {
    return new Intl.DisplayNames([locale], { type: 'currency' }).of(code) || code
  } catch {
    return code
  }
}