export const SYMBOL_SPLIT_REGEX = /[\s,;\uFF0C\u3001]+/

export const splitSymbolInput = (rawSymbols) =>
  String(rawSymbols || '')
    .split(SYMBOL_SPLIT_REGEX)
    .map((item) => item.trim())
    .filter(Boolean)

export const normalizeSymbol = (value) => {
  const raw = String(value || '').trim().toLowerCase()
  if (!raw) return ''
  return raw.replace(/[^a-z0-9]/g, '')
}

export const symbolEquals = (left, right) => {
  const a = normalizeSymbol(left)
  const b = normalizeSymbol(right)
  if (!a || !b) return false
  if (a === b) return true
  const stripCnPrefix = (text) => (/^[a-z]{2}\d{5,}$/.test(text) ? text.slice(2) : text)
  const aCode = stripCnPrefix(a)
  const bCode = stripCnPrefix(b)
  return !!aCode && !!bCode && aCode === bCode
}

export const inferMarketBySymbol = (symbol, defaultMarket = 'SH') => {
  const raw = String(symbol || '').trim().toLowerCase()
  if (raw.startsWith('us')) return 'US'
  if (raw.startsWith('hk')) return 'HK'
  if (raw.startsWith('sh')) return 'SH'
  if (raw.startsWith('sz3')) return '300'
  if (raw.startsWith('sz')) return 'SZ'
  return defaultMarket || 'SH'
}

export const inferMarketBySymbols = (rawSymbols, fallbackMarket = 'SH') => {
  const list = splitSymbolInput(rawSymbols)
  if (!list.length) return fallbackMarket || 'SH'
  const inferred = list.map((symbol) => inferMarketBySymbol(symbol, fallbackMarket)).filter(Boolean)
  if (!inferred.length) return fallbackMarket || 'SH'
  const first = inferred[0]
  if (inferred.every((item) => item === first)) return first
  return fallbackMarket || 'SH'
}

export const displaySymbol = (item) => {
  if (!item || !item.symbol) return ''
  const lower = String(item.symbol).toLowerCase()
  if (lower.startsWith('sh') || lower.startsWith('sz')) {
    return item.symbol.slice(2)
  }
  return item.symbol
}

export const displayKind = (kind) => {
  if (kind === 'index') return '指数'
  if (kind === 'stock') return '个股'
  return '-'
}

export const displayMarket = (item) => {
  if (!item) return '-'
  const symbol = String(item.symbol || '').toLowerCase()
  if (symbol.startsWith('sz3')) return '300'
  return item.market || '-'
}

export const displayExchange = (item) => {
  if (!item) return '-'
  const symbol = String(item.symbol || '').toLowerCase()
  const exchange = String(item.exchange || '').trim().toUpperCase()
  if (symbol.startsWith('sz3')) return 'SZ (ChiNext)'
  return exchange || '-'
}

const normalizeSingleSymbolForInput = (symbol) => {
  const text = String(symbol || '').trim()
  if (!text) return ''
  const raw = text.toLowerCase()
  if ((raw.startsWith('sh') || raw.startsWith('sz')) && /^\d{6}$/.test(raw.slice(2))) {
    return raw.slice(2)
  }
  return text
}

export const normalizeSymbolsInputForUi = (rawSymbols) =>
  splitSymbolInput(rawSymbols).map((item) => normalizeSingleSymbolForInput(item)).filter(Boolean).join(', ')

export const formatSelectedSymbol = (symbol, fallbackMarket = 'SH') => {
  if (!symbol) return ''
  const text = String(symbol).trim()
  if (!text) return ''
  const raw = text.toLowerCase()
  let code = text
  if (raw.startsWith('sh') || raw.startsWith('sz') || raw.startsWith('hk') || raw.startsWith('us')) {
    code = text.slice(2)
  }
  const market = inferMarketBySymbols(text, fallbackMarket)
  if (market === '300') return `${code} (300)`
  if (market === 'SH' || market === 'SZ') return `${code} (${market})`
  return `${code} (${market})`
}

export const formatSymbolText = (rawSymbols, fallbackMarket = 'SH') => {
  const list = splitSymbolInput(rawSymbols)
  if (!list.length) return '-'
  return list.map((symbol) => formatSelectedSymbol(symbol, fallbackMarket)).join(', ')
}
