import { symbolEquals } from './symbols'

export const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(digits)
}

export const toDateInt = (value) => {
  if (value === null || value === undefined) return null
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return null
    if (value > 100000000000) {
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return null
      const yyyy = d.getFullYear()
      const mm = String(d.getMonth() + 1).padStart(2, '0')
      const dd = String(d.getDate()).padStart(2, '0')
      return Number(`${yyyy}${mm}${dd}`)
    }
    if (value > 1000000000 && value < 100000000000) {
      const d = new Date(value * 1000)
      if (Number.isNaN(d.getTime())) return null
      const yyyy = d.getFullYear()
      const mm = String(d.getMonth() + 1).padStart(2, '0')
      const dd = String(d.getDate()).padStart(2, '0')
      return Number(`${yyyy}${mm}${dd}`)
    }
    return value
  }
  const raw = String(value).trim()
  if (!raw) return null
  if (/^\d{8}$/.test(raw)) return Number(raw)
  if (/^\d{13}$/.test(raw) || /^\d{10}$/.test(raw)) {
    const n = Number(raw)
    return toDateInt(n)
  }
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return null
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return Number(`${yyyy}${mm}${dd}`)
}

export const formatKlineDate = (value) => {
  const dateInt = toDateInt(value)
  if (!dateInt) return '-'
  const raw = String(dateInt)
  return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
}

export const toChartTime = (value) => {
  const dateInt = toDateInt(value)
  if (!dateInt) return null
  const raw = String(dateInt)
  return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
}

export const orderKey = (order) => {
  if (!order) return ''
  const dateInt = toDateInt(order.buy_date) || 0
  const price = Number(order.buy_price) || 0
  return `${order.symbol || 'unknown'}-${dateInt}-${price}`
}

export const isClosedOrder = (order) => {
  if (!order) return false
  const sellDate = Number(order.sell_date || 0)
  const sellPrice = Number(order.sell_price)
  return sellDate > 0 && Number.isFinite(sellPrice) && sellPrice > 0
}

export const resolveOrderProfit = (order) => {
  if (!order) return 0
  if (!isClosedOrder(order)) return null
  if (order.profit !== undefined && order.profit !== null) {
    const val = Number(order.profit)
    if (Number.isFinite(val)) return val
  }
  const buy = Number(order.buy_price)
  const sell = Number(order.sell_price)
  const cnt = Number(order.buy_cnt)
  const direction = Number(order.expect_direction || 1)
  const size = Number.isFinite(cnt) && cnt > 0 ? cnt : 1
  const dir = Number.isFinite(direction) ? direction : 1
  if (Number.isFinite(buy) && Number.isFinite(sell)) return (sell - buy) * size * dir
  return 0
}

export const buildCandleSeriesData = (data) =>
  (data || [])
    .map((item) => ({
      time: toChartTime(item.date),
      open: Number(item.open ?? item.close ?? 0),
      high: Number(item.high ?? item.close ?? 0),
      low: Number(item.low ?? item.close ?? 0),
      close: Number(item.close ?? item.open ?? 0)
    }))
    .filter((item) => item.time)

export const buildVolumeSeriesData = (data) =>
  (data || [])
    .map((item) => ({
      time: toChartTime(item.date),
      value: Number(item.volume ?? 0),
      color:
        Number(item.close ?? 0) >= Number(item.open ?? 0)
          ? 'rgba(194, 53, 49, 0.42)'
          : 'rgba(47, 125, 50, 0.42)'
    }))
    .filter((item) => item.time)

export const buildEquitySeries = ({
  backtestJob,
  backtestOrders,
  chartSymbol
}) => {
  const curve = backtestJob?.result?.equity_curve
  if (Array.isArray(curve) && curve.length) {
    return curve
      .map((item) => ({
        time: toChartTime(item.time || item.date || item.x),
        value: Number(item.value ?? item.y)
      }))
      .filter((item) => item.time && Number.isFinite(item.value))
      .sort((a, b) => String(a.time).localeCompare(String(b.time)))
  }

  const allOrders = Array.isArray(backtestOrders) ? backtestOrders : []
  const symbolScoped = chartSymbol
    ? allOrders.filter((item) => symbolEquals(item.symbol, chartSymbol))
    : allOrders
  const scopedClosedCount = symbolScoped.filter((item) => isClosedOrder(item)).length
  const sourceOrders = scopedClosedCount ? symbolScoped : allOrders

  const rows = sourceOrders
    .filter((order) => isClosedOrder(order))
    .map((order) => ({
      time: toChartTime(order.sell_date || order.buy_date),
      profit: Number(resolveOrderProfit(order) || 0)
    }))
    .filter((row) => row.time && Number.isFinite(row.profit))
    .sort((a, b) => String(a.time).localeCompare(String(b.time)))

  if (!rows.length) {
    const fallbackRows = sourceOrders
      .map((order) => ({
        time: toChartTime(order.sell_date || order.buy_date),
        profit: Number(order?.profit)
      }))
      .filter((row) => row.time && Number.isFinite(row.profit))
      .sort((a, b) => String(a.time).localeCompare(String(b.time)))
    if (!fallbackRows.length) return []
    rows.push(...fallbackRows)
  }

  const dailyProfit = new Map()
  rows.forEach((row) => {
    dailyProfit.set(row.time, Number((dailyProfit.get(row.time) || 0) + row.profit))
  })

  const points = []
  let cumulative = 0
  Array.from(dailyProfit.entries())
    .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
    .forEach(([time, profit]) => {
      cumulative += Number(profit || 0)
      points.push({ time, value: Number(cumulative.toFixed(2)) })
    })
  return points
}
