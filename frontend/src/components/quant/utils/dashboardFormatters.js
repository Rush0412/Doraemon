export const defaultSymbolForMarket = (value) => {
  if (value === 'SH') return '600036'
  if (value === 'SZ') return '000001'
  if (value === '300') return '300750'
  if (value === 'US') return 'AAPL'
  if (value === 'HK') return '00700'
  return '600036'
}

export const formatTime = (value) => {
  if (!value) return '-'
  try {
    const parsed = typeof value === 'string' ? new Date(value) : new Date(String(value))
    if (Number.isNaN(parsed.getTime())) return String(value)
    return parsed.toLocaleString()
  } catch {
    return String(value)
  }
}

export const brief = (value) => {
  if (!value) return ''
  const text = typeof value === 'string' ? value : JSON.stringify(value)
  return text.length > 60 ? `${text.slice(0, 57)}...` : text
}

export const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(digits)
}
