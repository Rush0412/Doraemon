import { symbolEquals } from './symbols'
import { formatNumber, toChartTime, toDateInt } from './chartDomain'

export const buildSignalForChart = ({ predictionSignal, chartSymbol }) => {
  const signal = predictionSignal
  if (!signal || typeof signal !== 'object') return null
  const signalSymbol = String(signal.symbol || '').trim()
  if (signalSymbol && chartSymbol && !symbolEquals(signalSymbol, chartSymbol)) return null
  return signal
}

export const buildAdviceForChart = ({
  operationSuggestion,
  predictionSignal,
  chartSymbol,
  klineData
}) => {
  const advice = operationSuggestion
  if (!advice || typeof advice !== 'object' || !klineData?.length) return null
  const signal = buildSignalForChart({ predictionSignal, chartSymbol })
  if (signal?.symbol && chartSymbol && !symbolEquals(signal.symbol, chartSymbol)) return null
  const latestRow = klineData[klineData.length - 1] || null
  const adviceDateInt = toDateInt(signal?.trade_date) || toDateInt(latestRow?.date)
  const adviceTime = toChartTime(adviceDateInt)
  if (!adviceTime) return null
  const lastClose = Number(advice.lastClose)
  const support = Number(advice.support)
  const resistance = Number(advice.resistance)
  const stopLoss = Number(advice.stopLoss ?? signal?.stop_loss)
  const takeProfit = Number(advice.takeProfit ?? signal?.take_profit)
  const entryPrice = Number(signal?.entry_price ?? lastClose)
  const takeProfitPlan = Array.isArray(advice.takeProfitPlan) ? advice.takeProfitPlan : []
  const direction = String(advice.direction || signal?.action || '').trim().toLowerCase()
  const isBuySide = ['buy', 'buy_watch', 'light_buy'].includes(direction)
  const isSellSide = ['sell', 'reduce', 'avoid'].includes(direction)
  return {
    adviceTime,
    adviceDateInt,
    direction,
    isBuySide,
    isSellSide,
    entryPrice: Number.isFinite(entryPrice) && entryPrice > 0 ? entryPrice : null,
    support: Number.isFinite(support) && support > 0 ? support : null,
    resistance: Number.isFinite(resistance) && resistance > 0 ? resistance : null,
    stopLoss: Number.isFinite(stopLoss) && stopLoss > 0 ? stopLoss : null,
    takeProfit: Number.isFinite(takeProfit) && takeProfit > 0 ? takeProfit : null,
    takeProfitPlan: takeProfitPlan
      .map((item) => ({
        label: String(item?.label || '').trim(),
        target: Number(item?.target)
      }))
      .filter((item) => item.label && Number.isFinite(item.target) && item.target > 0)
  }
}

export const resolveSignalEvent = ({ predictionSignal, chartSymbol, klineData }) => {
  const signal = buildSignalForChart({ predictionSignal, chartSymbol })
  if (!signal || !klineData?.length) return null
  const entryDateInt = toDateInt(signal.trade_date) || toDateInt(klineData[klineData.length - 1]?.date)
  if (!entryDateInt) return null
  const entryTime = toChartTime(entryDateInt)
  if (!entryTime) return null
  const entryRow =
    klineData.find((item) => toDateInt(item.date) === entryDateInt) ||
    klineData.find((item) => {
      const dateInt = toDateInt(item.date)
      return dateInt && dateInt >= entryDateInt
    }) ||
    klineData[klineData.length - 1] ||
    null
  const rawEntryPrice = Number(signal.entry_price)
  const entryPrice = Number.isFinite(rawEntryPrice)
    ? rawEntryPrice
    : Number(entryRow?.close ?? entryRow?.open ?? NaN)
  const stopLoss = Number(signal.stop_loss)
  const takeProfit = Number(signal.take_profit)
  const hasStopLoss = Number.isFinite(stopLoss) && stopLoss > 0
  const hasTakeProfit = Number.isFinite(takeProfit) && takeProfit > 0
  let sellTrigger = null
  if (hasStopLoss || hasTakeProfit) {
    for (const item of klineData) {
      const dateInt = toDateInt(item?.date)
      if (!dateInt || dateInt < entryDateInt) continue
      const low = Number(item?.low ?? item?.close ?? NaN)
      const high = Number(item?.high ?? item?.close ?? NaN)
      const stopHit = hasStopLoss && Number.isFinite(low) && low <= stopLoss
      const takeHit = hasTakeProfit && Number.isFinite(high) && high >= takeProfit
      if (!stopHit && !takeHit) continue
      if (stopHit) {
        sellTrigger = { type: 'stop_loss', dateInt, time: toChartTime(dateInt), price: stopLoss }
      } else {
        sellTrigger = { type: 'take_profit', dateInt, time: toChartTime(dateInt), price: takeProfit }
      }
      break
    }
  }
  return {
    action: String(signal.action || '').trim().toLowerCase() || null,
    entryDateInt,
    entryTime,
    entryPrice: Number.isFinite(entryPrice) ? entryPrice : null,
    stopLoss: hasStopLoss ? stopLoss : null,
    takeProfit: hasTakeProfit ? takeProfit : null,
    sellTrigger
  }
}

const buildPredictionMarkers = ({ overlayMode, predictionSignal, chartSymbol, klineData, minDate, maxDate }) => {
  if (overlayMode !== 'signal-only') return []
  const event = resolveSignalEvent({ predictionSignal, chartSymbol, klineData })
  if (!event) return []
  const markers = []
  if (event.entryTime && (!minDate || (event.entryDateInt >= minDate && event.entryDateInt <= maxDate))) {
    markers.push({
      time: event.entryTime,
      position: 'belowBar',
      color: '#2f6fdd',
      shape: 'circle',
      text: `信号买入 ${formatNumber(event.entryPrice)}`
    })
  }
  const trigger = event.sellTrigger
  if (trigger?.time && (!minDate || (trigger.dateInt >= minDate && trigger.dateInt <= maxDate))) {
    const isStop = trigger.type === 'stop_loss'
    markers.push({
      time: trigger.time,
      position: 'aboveBar',
      color: isStop ? '#b33a3a' : '#1f7a4b',
      shape: 'arrowDown',
      text: `${isStop ? '信号止损' : '信号止盈'} ${formatNumber(trigger.price)}`
    })
  }
  return markers
}

const buildAdviceMarkers = ({ operationSuggestion, predictionSignal, chartSymbol, klineData, minDate, maxDate }) => {
  const advice = buildAdviceForChart({ operationSuggestion, predictionSignal, chartSymbol, klineData })
  if (!advice?.adviceTime) return []
  if (minDate && (advice.adviceDateInt < minDate || advice.adviceDateInt > maxDate)) return []
  const markers = []
  if (advice.isBuySide && advice.entryPrice) {
    markers.push({
      time: advice.adviceTime,
      position: 'belowBar',
      color: '#0f766e',
      shape: 'circle',
      text: `建议买入 ${formatNumber(advice.entryPrice)}`
    })
  }
  if (advice.isSellSide && advice.entryPrice) {
    markers.push({
      time: advice.adviceTime,
      position: 'aboveBar',
      color: '#b45309',
      shape: 'circle',
      text: `建议卖出 ${formatNumber(advice.entryPrice)}`
    })
  }
  if (advice.takeProfitPlan.length) {
    const primaryTp = advice.takeProfitPlan[0]
    markers.push({
      time: advice.adviceTime,
      position: 'aboveBar',
      color: '#1d4ed8',
      shape: 'square',
      text: `${primaryTp.label} ${formatNumber(primaryTp.target)}`
    })
  } else if (advice.takeProfit) {
    markers.push({
      time: advice.adviceTime,
      position: 'aboveBar',
      color: '#1d4ed8',
      shape: 'square',
      text: `预计止盈 ${formatNumber(advice.takeProfit)}`
    })
  }
  return markers
}

export const buildChartMarkers = ({
  overlayMode,
  orders,
  klineData,
  predictionSignal,
  operationSuggestion,
  chartSymbol
}) => {
  const maxMarkers = 5000
  const markerOrders = orders.length > maxMarkers ? orders.slice(-maxMarkers) : orders
  const minDate = klineData.length ? toDateInt(klineData[0]?.date) || 0 : 0
  const maxDate = klineData.length ? toDateInt(klineData[klineData.length - 1]?.date) || 0 : 0
  const markers = []
  markerOrders.forEach((order) => {
    const buyDate = toDateInt(order.buy_date) || 0
    const buyTime = toChartTime(order.buy_date)
    const sellTime = toChartTime(order.sell_date)
    if (buyTime && (!minDate || (buyDate >= minDate && buyDate <= maxDate))) {
      markers.push({
        time: buyTime,
        position: 'belowBar',
        color: '#1f7a4b',
        shape: 'arrowUp',
        text: `买 ${formatNumber(order.buy_price)}`
      })
    }
    const sellDate = toDateInt(order.sell_date) || 0
    if (sellTime && Number(order.sell_date) > 0 && (!minDate || (sellDate >= minDate && sellDate <= maxDate))) {
      markers.push({
        time: sellTime,
        position: 'aboveBar',
        color: '#c17f2f',
        shape: 'arrowDown',
        text: `卖 ${formatNumber(order.sell_price)}`
      })
    }
  })
  return [
    ...markers,
    ...buildPredictionMarkers({ overlayMode, predictionSignal, chartSymbol, klineData, minDate, maxDate }),
    ...buildAdviceMarkers({ operationSuggestion, predictionSignal, chartSymbol, klineData, minDate, maxDate })
  ].sort((a, b) => String(a.time).localeCompare(String(b.time)))
}

export const buildPriceLineSpecs = ({
  overlayMode,
  selectedOrder,
  showStopLines,
  predictionSignal,
  operationSuggestion,
  chartSymbol,
  klineData
}) => {
  const specs = []
  if (overlayMode === 'signal-only') {
    const event = resolveSignalEvent({ predictionSignal, chartSymbol, klineData })
    if (event?.entryPrice && Number.isFinite(event.entryPrice)) {
      specs.push({ price: event.entryPrice, color: '#2f6fdd', lineWidth: 2, lineStyle: 0, title: '信号买入' })
    }
    if (showStopLines && event?.stopLoss) {
      specs.push({ price: event.stopLoss, color: '#b33a3a', lineWidth: 1, lineStyle: 2, title: '信号止损' })
    }
    if (showStopLines && event?.takeProfit) {
      specs.push({ price: event.takeProfit, color: '#1f7a4b', lineWidth: 1, lineStyle: 2, title: '信号止盈' })
    }
  }

  const advice = buildAdviceForChart({ operationSuggestion, predictionSignal, chartSymbol, klineData })
  if (advice?.entryPrice) {
    specs.push({
      price: advice.entryPrice,
      color: advice.isSellSide ? '#b45309' : '#0f766e',
      lineWidth: 2,
      lineStyle: 1,
      title: advice.isSellSide ? '建议卖出' : '建议买入'
    })
  }
  if (showStopLines && advice?.stopLoss) {
    specs.push({ price: advice.stopLoss, color: '#b33a3a', lineWidth: 1, lineStyle: 2, title: '建议止损' })
  }
  if (showStopLines) {
    const tpTargets = advice?.takeProfitPlan?.length
      ? advice.takeProfitPlan.slice(0, 3)
      : advice?.takeProfit
        ? [{ label: '止盈', target: advice.takeProfit }]
        : []
    tpTargets.forEach((item) => {
      specs.push({
        price: item.target,
        color: '#1d4ed8',
        lineWidth: 1,
        lineStyle: 2,
        title: `预计${item.label || '止盈'}`
      })
    })
  }

  if (overlayMode !== 'selected-order' || !selectedOrder || typeof selectedOrder !== 'object') {
    return specs
  }

  const buyPrice = Number(selectedOrder.buy_price)
  if (Number.isFinite(buyPrice) && buyPrice > 0) {
    specs.push({ price: buyPrice, color: '#1f7a4b', lineWidth: 2, lineStyle: 0, title: '买入' })
  }
  const sellPrice = Number(selectedOrder.sell_price)
  const sellDate = Number(selectedOrder.sell_date || 0)
  if (Number.isFinite(sellPrice) && sellPrice > 0 && sellDate > 0) {
    specs.push({ price: sellPrice, color: '#c17f2f', lineWidth: 2, lineStyle: 0, title: '卖出' })
  }
  if (showStopLines) {
    const stopLoss = Number(selectedOrder.stop_loss_price)
    if (Number.isFinite(stopLoss) && stopLoss > 0) {
      specs.push({ price: stopLoss, color: '#b33a3a', lineWidth: 1, lineStyle: 2, title: '止损' })
    }
    const stopWin = Number(selectedOrder.stop_win_price)
    if (Number.isFinite(stopWin) && stopWin > 0) {
      specs.push({ price: stopWin, color: '#1f7a4b', lineWidth: 1, lineStyle: 2, title: '止盈' })
    }
  }
  return specs
}

export const buildAnalysisOverlaySpecs = ({
  analysisOverlayEnabled,
  analysisResult,
  chartSymbol,
  klineData
}) => {
  if (!analysisOverlayEnabled || !analysisResult || !klineData.length) return []
  const lines = analysisResult.trend_lines
  if (!Array.isArray(lines) || !lines.length) return []
  const symbol = (analysisResult.symbol || '').toLowerCase()
  if (symbol && chartSymbol && symbol !== chartSymbol.toLowerCase()) return []
  return lines
    .map((line) => {
      let startTime = toChartTime(line.x_start)
      let endTime = toChartTime(line.x_end)
      if (!startTime || !endTime) {
        const startIndexValue =
          Number.isFinite(Number(line.x_start_idx)) ? Number(line.x_start_idx) : Number(line.x_start)
        const endIndexValue =
          Number.isFinite(Number(line.x_end_idx)) ? Number(line.x_end_idx) : Number(line.x_end)
        const startIdx = Math.max(0, Math.min(klineData.length - 1, Math.round(startIndexValue || 0)))
        const endIdx = Math.max(0, Math.min(klineData.length - 1, Math.round(endIndexValue || 0)))
        startTime = toChartTime(klineData[startIdx]?.date)
        endTime = toChartTime(klineData[endIdx]?.date)
      }
      if (!startTime || !endTime) return null
      return {
        color: line.type === 'support' ? '#2f6fdd' : '#c17f2f',
        lineWidth: 1,
        lineStyle: 2,
        data: [
          { time: startTime, value: Number(line.y_start) || 0 },
          { time: endTime, value: Number(line.y_end) || 0 }
        ]
      }
    })
    .filter(Boolean)
}
