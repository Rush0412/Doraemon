export const formatMetric = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(4)
}

export const formatNumberMetric = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(2)
}

export const formatPercentMetric = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return `${(num * 100).toFixed(2)}%`
}

export const formatCount = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num) || num <= 0) return '-'
  return String(num)
}

export const formatModelScope = (scope) => {
  if (scope === 'composite_market') return 'CN 子市场聚合'
  if (scope === 'market') return '市场模型'
  if (scope === 'custom') return '自定义模型'
  return scope || '-'
}

export const formatModelLabel = (summary) => {
  if (!summary) return '-'
  if (summary.model_scope === 'composite_market') {
    const names = Object.entries(summary.model_names || {})
      .map(([market, name]) => `${market}:${name}`)
      .join(' | ')
    return names || 'composite_market_bundle'
  }
  if (summary.model_id) return `#${summary.model_id} ${summary.model_name || ''}`.trim()
  return summary.model_name || '-'
}
