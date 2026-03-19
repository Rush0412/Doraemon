import { nextTick, ref } from 'vue'
import { createChart } from 'lightweight-charts'
import { api } from '../../../services/api'
import { splitSymbolInput, symbolEquals } from '../utils/symbols'

const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(digits)
}

export const useBacktestCharts = ({
  backtestForm,
  backtestJob,
  backtestOrders,
  backtestSymbols,
  chartOrdersAll,
  filteredOrders,
  analysisResult,
  analysisOverlayEnabled,
  operationSuggestion,
  chartSymbol,
  selectedOrderKey,
  selectedOrder,
  predictionSignal,
  showStopLines,
  chartWindow,
  activeTab,
  toolForm
}) => {
  const klineContainer = ref(null)
  const equityContainer = ref(null)
  const chartRef = ref(null)
  const candleSeries = ref(null)
  const volumeSeries = ref(null)
  const equityChartRef = ref(null)
  const equitySeries = ref(null)
  const analysisLineSeries = ref([])
  const orderPriceLines = ref([])
  const klineData = ref([])
  const equityData = ref([])
  const klineLoading = ref(false)
  const klineError = ref('')
  const hoverInfo = ref(null)
  const latestKlineRequestId = ref(0)

  const setKlineContainer = (el) => {
    klineContainer.value = el
  }

  const setEquityContainer = (el) => {
    equityContainer.value = el
  }

  const toDateInt = (value) => {
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

  const formatKlineDate = (value) => {
    const dateInt = toDateInt(value)
    if (!dateInt) return '-'
    const raw = String(dateInt)
    return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
  }

  const toChartTime = (value) => {
    const dateInt = toDateInt(value)
    if (!dateInt) return null
    const raw = String(dateInt)
    return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
  }

  const orderKey = (order) => {
    if (!order) return ''
    const dateInt = toDateInt(order.buy_date) || 0
    const price = Number(order.buy_price) || 0
    return `${order.symbol || 'unknown'}-${dateInt}-${price}`
  }

  const isClosedOrder = (order) => {
    if (!order) return false
    const sellDate = Number(order.sell_date || 0)
    const sellPrice = Number(order.sell_price)
    return sellDate > 0 && Number.isFinite(sellPrice) && sellPrice > 0
  }

  const resolveOrderProfit = (order) => {
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

  const getValidChartOrders = () => {
    const rows = Array.isArray(chartOrdersAll.value) ? chartOrdersAll.value : []
    return rows.filter((item) => item && typeof item === 'object')
  }

  const resolveChartOverlayMode = () => {
    if (selectedOrder.value && typeof selectedOrder.value === 'object') return 'selected-order'
    if (getValidChartOrders().length) return 'orders-overview'
    return 'signal-only'
  }

  const applyVisibleRange = () => {
    if (!chartRef.value || !klineData.value.length) return
    const total = klineData.value.length
    const size = Math.max(60, Math.min(chartWindow.size || 220, total))
    const maxOffset = Math.max(0, total - size)
    if (chartWindow.offset > maxOffset) chartWindow.offset = maxOffset
    if (chartWindow.offset < 0) chartWindow.offset = 0
    const to = total - 1 - chartWindow.offset
    const from = Math.max(0, to - size + 1)
    chartRef.value.timeScale().setVisibleLogicalRange({ from, to })
  }

  const focusOrder = (order) => {
    if (!order || !klineData.value.length) return
    const dateInt = toDateInt(order.buy_date)
    if (!dateInt) return
    const index = klineData.value.findIndex((item) => toDateInt(item.date) === dateInt)
    if (index < 0) return
    const total = klineData.value.length
    const size = Math.max(60, Math.min(chartWindow.size || 220, total))
    const to = Math.min(total - 1, index + Math.floor(size / 2))
    chartWindow.offset = Math.max(0, total - 1 - to)
    applyVisibleRange()
  }

  const syncSelectedOrder = () => {
    if (!selectedOrderKey.value) {
      selectedOrder.value = null
      return
    }
    const next = filteredOrders.value.find((order) => orderKey(order) === selectedOrderKey.value)
    if (!next) {
      selectedOrderKey.value = ''
    }
    selectedOrder.value = next || null
    if (next) {
      focusOrder(next)
    }
  }

  const selectOrder = (order) => {
    if (!order) return
    selectedOrderKey.value = orderKey(order)
    selectedOrder.value = order
    focusOrder(order)
  }

  const ensureChart = () => {
    if (chartRef.value || !klineContainer.value) return
    const width = klineContainer.value.clientWidth
    if (!width) return
    chartRef.value = createChart(klineContainer.value, {
      height: 560,
      width,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#1b1a18',
        fontFamily: "Sora, 'Noto Sans SC', sans-serif",
        attributionLogo: false
      },
      grid: {
        vertLines: { color: 'rgba(27, 26, 24, 0.08)' },
        horzLines: { color: 'rgba(27, 26, 24, 0.08)' }
      },
      rightPriceScale: {
        borderColor: 'rgba(27, 26, 24, 0.2)'
      },
      timeScale: {
        borderColor: 'rgba(27, 26, 24, 0.2)',
        timeVisible: true,
        secondsVisible: false
      },
      crosshair: {
        mode: 0
      }
    })
    candleSeries.value = chartRef.value.addCandlestickSeries({
      upColor: '#c23531',
      downColor: '#2f7d32',
      wickUpColor: '#c23531',
      wickDownColor: '#2f7d32',
      borderVisible: false
    })
    volumeSeries.value = chartRef.value.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      scaleMargins: { top: 0.8, bottom: 0 }
    })
    chartRef.value.subscribeCrosshairMove((param) => {
      if (!param || !param.time || !candleSeries.value) {
        hoverInfo.value = null
        return
      }
      const candle = param.seriesData.get(candleSeries.value)
      if (!candle) {
        hoverInfo.value = null
        return
      }
      const volume = volumeSeries.value ? param.seriesData.get(volumeSeries.value) : null
      const time =
        typeof param.time === 'string'
          ? param.time
          : `${param.time.year}-${String(param.time.month).padStart(2, '0')}-${String(param.time.day).padStart(2, '0')}`
      hoverInfo.value = {
        date: time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
        volume: volume?.value ?? null
      }
    })
  }

  const ensureEquityChart = () => {
    if (equityChartRef.value || !equityContainer.value) return
    const width = equityContainer.value.clientWidth
    if (!width) return
    equityChartRef.value = createChart(equityContainer.value, {
      height: 280,
      width,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#1b1a18',
        fontFamily: "Sora, 'Noto Sans SC', sans-serif",
        attributionLogo: false
      },
      grid: {
        vertLines: { color: 'rgba(27, 26, 24, 0.08)' },
        horzLines: { color: 'rgba(27, 26, 24, 0.08)' }
      },
      rightPriceScale: {
        borderColor: 'rgba(27, 26, 24, 0.2)'
      },
      timeScale: {
        borderColor: 'rgba(27, 26, 24, 0.2)',
        timeVisible: true,
        secondsVisible: false
      }
    })
    equitySeries.value = equityChartRef.value.addLineSeries({
      color: '#1f7a4b',
      lineWidth: 2
    })
  }

  const buildSignalForChart = () => {
    const signal = predictionSignal?.value
    if (!signal || typeof signal !== 'object') return null
    const signalSymbol = String(signal.symbol || '').trim()
    if (signalSymbol && chartSymbol.value && !symbolEquals(signalSymbol, chartSymbol.value)) return null
    return signal
  }

  const buildAdviceForChart = () => {
    const advice = operationSuggestion?.value
    if (!advice || typeof advice !== 'object' || !klineData.value.length) return null
    const signal = buildSignalForChart()
    if (signal?.symbol && chartSymbol.value && !symbolEquals(signal.symbol, chartSymbol.value)) return null
    const latestRow = klineData.value[klineData.value.length - 1] || null
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

  const resolveSignalEvent = () => {
    const signal = buildSignalForChart()
    if (!signal || !klineData.value.length) return null
    const entryDateInt = toDateInt(signal.trade_date) || toDateInt(klineData.value[klineData.value.length - 1]?.date)
    if (!entryDateInt) return null
    const entryTime = toChartTime(entryDateInt)
    if (!entryTime) return null
    const entryRow =
      klineData.value.find((item) => toDateInt(item.date) === entryDateInt) ||
      klineData.value.find((item) => {
        const dateInt = toDateInt(item.date)
        return dateInt && dateInt >= entryDateInt
      }) ||
      klineData.value[klineData.value.length - 1] ||
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
      for (const item of klineData.value) {
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

  const buildPredictionMarkers = (minDate, maxDate) => {
    if (resolveChartOverlayMode() !== 'signal-only') return []
    const event = resolveSignalEvent()
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

  const buildAdviceMarkers = (minDate, maxDate) => {
    const advice = buildAdviceForChart()
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

  const buildMarkers = () => {
    const orders = getValidChartOrders()
    const maxMarkers = 5000
    const markerOrders = orders.length > maxMarkers ? orders.slice(-maxMarkers) : orders
    const minDate = klineData.value.length ? toDateInt(klineData.value[0]?.date) || 0 : 0
    const maxDate = klineData.value.length ? toDateInt(klineData.value[klineData.value.length - 1]?.date) || 0 : 0
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
    return [...markers, ...buildPredictionMarkers(minDate, maxDate), ...buildAdviceMarkers(minDate, maxDate)].sort((a, b) =>
      String(a.time).localeCompare(String(b.time))
    )
  }

  const clearOrderLines = () => {
    if (!candleSeries.value || !orderPriceLines.value.length) {
      orderPriceLines.value = []
      return
    }
    orderPriceLines.value.forEach((line) => {
      try {
        candleSeries.value.removePriceLine(line)
      } catch {
        // ignore stale lines
      }
    })
    orderPriceLines.value = []
  }

  const applyOrderLines = () => {
    clearOrderLines()
    if (!candleSeries.value) return
    const order = selectedOrder.value
    const overlayMode = resolveChartOverlayMode()
    const lines = []
    if (overlayMode === 'signal-only') {
      const event = resolveSignalEvent()
      if (event?.entryPrice && Number.isFinite(event.entryPrice)) {
        lines.push(
          candleSeries.value.createPriceLine({
            price: event.entryPrice,
            color: '#2f6fdd',
            lineWidth: 2,
            lineStyle: 0,
            axisLabelVisible: true,
            title: '信号买入'
          })
        )
      }
      if (showStopLines.value && event?.stopLoss) {
        lines.push(
          candleSeries.value.createPriceLine({
            price: event.stopLoss,
            color: '#b33a3a',
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: '信号止损'
          })
        )
      }
      if (showStopLines.value && event?.takeProfit) {
        lines.push(
          candleSeries.value.createPriceLine({
            price: event.takeProfit,
            color: '#1f7a4b',
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: '信号止盈'
          })
        )
      }
      orderPriceLines.value = lines
    }
    const advice = buildAdviceForChart()
    if (advice?.entryPrice) {
      lines.push(
        candleSeries.value.createPriceLine({
          price: advice.entryPrice,
          color: advice.isSellSide ? '#b45309' : '#0f766e',
          lineWidth: 2,
          lineStyle: 1,
          axisLabelVisible: true,
          title: advice.isSellSide ? '建议卖出' : '建议买入'
        })
      )
    }
    if (showStopLines.value && advice?.stopLoss) {
      lines.push(
        candleSeries.value.createPriceLine({
          price: advice.stopLoss,
          color: '#b33a3a',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: '建议止损'
        })
      )
    }
    if (showStopLines.value) {
      const tpTargets = advice?.takeProfitPlan?.length
        ? advice.takeProfitPlan.slice(0, 3)
        : advice?.takeProfit
          ? [{ label: '止盈', target: advice.takeProfit }]
          : []
      tpTargets.forEach((item) => {
        lines.push(
          candleSeries.value.createPriceLine({
            price: item.target,
            color: '#1d4ed8',
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: `预计${item.label || '止盈'}`
          })
        )
      })
    }
    if (overlayMode !== 'selected-order' || !order || typeof order !== 'object') {
      orderPriceLines.value = lines
      return
    }
    const buyPrice = Number(order.buy_price)
    if (Number.isFinite(buyPrice) && buyPrice > 0) {
      lines.push(
        candleSeries.value.createPriceLine({
          price: buyPrice,
          color: '#1f7a4b',
          lineWidth: 2,
          lineStyle: 0,
          axisLabelVisible: true,
          title: '买入'
        })
      )
    }
    const sellPrice = Number(order.sell_price)
    const sellDate = Number(order.sell_date || 0)
    if (Number.isFinite(sellPrice) && sellPrice > 0 && sellDate > 0) {
      lines.push(
        candleSeries.value.createPriceLine({
          price: sellPrice,
          color: '#c17f2f',
          lineWidth: 2,
          lineStyle: 0,
          axisLabelVisible: true,
          title: '卖出'
        })
      )
    }
    if (showStopLines.value) {
      const stopLoss = Number(order.stop_loss_price)
      if (Number.isFinite(stopLoss) && stopLoss > 0) {
        lines.push(
          candleSeries.value.createPriceLine({
            price: stopLoss,
            color: '#b33a3a',
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: '止损'
          })
        )
      }
      const stopWin = Number(order.stop_win_price)
      if (Number.isFinite(stopWin) && stopWin > 0) {
        lines.push(
          candleSeries.value.createPriceLine({
            price: stopWin,
            color: '#1f7a4b',
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: '止盈'
          })
        )
      }
    }
    orderPriceLines.value = lines
  }

  const clearAnalysisOverlay = () => {
    if (!chartRef.value || !analysisLineSeries.value.length) {
      analysisLineSeries.value = []
      return
    }
    analysisLineSeries.value.forEach((series) => {
      try {
        chartRef.value.removeSeries(series)
      } catch {
        // ignore stale series
      }
    })
    analysisLineSeries.value = []
  }

  const applyAnalysisOverlay = () => {
    clearAnalysisOverlay()
    if (!analysisOverlayEnabled.value || !analysisResult.value || !chartRef.value) return
    const lines = analysisResult.value.trend_lines
    if (!Array.isArray(lines) || !lines.length || !klineData.value.length) return
    const symbol = (analysisResult.value.symbol || '').toLowerCase()
    if (symbol && chartSymbol.value && symbol !== chartSymbol.value.toLowerCase()) return
    lines.forEach((line) => {
      let startTime = toChartTime(line.x_start)
      let endTime = toChartTime(line.x_end)
      if (!startTime || !endTime) {
        const startIndexValue =
          Number.isFinite(Number(line.x_start_idx)) ? Number(line.x_start_idx) : Number(line.x_start)
        const endIndexValue =
          Number.isFinite(Number(line.x_end_idx)) ? Number(line.x_end_idx) : Number(line.x_end)
        const startIdx = Math.max(0, Math.min(klineData.value.length - 1, Math.round(startIndexValue || 0)))
        const endIdx = Math.max(0, Math.min(klineData.value.length - 1, Math.round(endIndexValue || 0)))
        startTime = toChartTime(klineData.value[startIdx]?.date)
        endTime = toChartTime(klineData.value[endIdx]?.date)
      }
      if (!startTime || !endTime) return
      const color = line.type === 'support' ? '#2f6fdd' : '#c17f2f'
      const series = chartRef.value.addLineSeries({
        color,
        lineWidth: 1,
        lineStyle: 2
      })
      series.setData([
        { time: startTime, value: Number(line.y_start) || 0 },
        { time: endTime, value: Number(line.y_end) || 0 }
      ])
      analysisLineSeries.value.push(series)
    })
  }

  const updateChartData = () => {
    ensureChart()
    if (!chartRef.value || !candleSeries.value || !volumeSeries.value) return
    const data = klineData.value || []
    if (!data.length) {
      candleSeries.value.setData([])
      volumeSeries.value.setData([])
      hoverInfo.value = null
      clearOrderLines()
      clearAnalysisOverlay()
      return
    }
    const candleData = data
      .map((item) => ({
        time: toChartTime(item.date),
        open: Number(item.open ?? item.close ?? 0),
        high: Number(item.high ?? item.close ?? 0),
        low: Number(item.low ?? item.close ?? 0),
        close: Number(item.close ?? item.open ?? 0)
      }))
      .filter((item) => item.time)
    candleSeries.value.setData(candleData)
    volumeSeries.value.setData(
      data
        .map((item) => ({
          time: toChartTime(item.date),
          value: Number(item.volume ?? 0),
          color:
            Number(item.close ?? 0) >= Number(item.open ?? 0)
              ? 'rgba(194, 53, 49, 0.42)'
              : 'rgba(47, 125, 50, 0.42)'
        }))
        .filter((item) => item.time)
    )
    candleSeries.value.setMarkers(buildMarkers())
    applyVisibleRange()
    applyOrderLines()
    applyAnalysisOverlay()
  }

  const buildEquitySeries = () => {
    const curve = backtestJob.value?.result?.equity_curve
    if (Array.isArray(curve) && curve.length) {
      return curve
        .map((item) => ({
          time: toChartTime(item.time || item.date || item.x),
          value: Number(item.value ?? item.y),
        }))
        .filter((item) => item.time && Number.isFinite(item.value))
        .sort((a, b) => String(a.time).localeCompare(String(b.time)))
    }

    const allOrders = backtestOrders.value || []
    const symbolScoped = chartSymbol.value
      ? allOrders.filter((item) => symbolEquals(item.symbol, chartSymbol.value))
      : allOrders
    const scopedClosedCount = symbolScoped.filter((item) => isClosedOrder(item)).length
    const sourceOrders = scopedClosedCount ? symbolScoped : allOrders

    const rows = sourceOrders
      .filter((order) => isClosedOrder(order))
      .map((order) => {
        const time = toChartTime(order.sell_date || order.buy_date)
        return {
          time,
          profit: Number(resolveOrderProfit(order) || 0)
        }
      })
      .filter((row) => row.time && Number.isFinite(row.profit))
      .sort((a, b) => String(a.time).localeCompare(String(b.time)))

    if (!rows.length) {
      const fallbackRows = sourceOrders
        .map((order) => {
          const time = toChartTime(order.sell_date || order.buy_date)
          const profit = Number(order?.profit)
          return { time, profit }
        })
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

  const updateEquityChart = () => {
    const points = buildEquitySeries()
    equityData.value = points
    ensureEquityChart()
    if (!equityChartRef.value || !equitySeries.value) return
    equitySeries.value.setData(points)
    if (points.length) {
      equityChartRef.value.timeScale().fitContent()
    }
  }

  const shiftWindow = (direction) => {
    const data = klineData.value || []
    if (!data.length) return
    const step = Math.max(10, Math.floor((chartWindow.size || 220) / 5))
    const size = Math.max(60, Math.min(chartWindow.size || 220, data.length))
    const maxOffset = Math.max(0, data.length - size)
    chartWindow.offset = Math.min(maxOffset, Math.max(0, chartWindow.offset + direction * step))
    applyVisibleRange()
  }

  const loadKlineChart = async () => {
    const symbols = backtestSymbols.value.length
      ? backtestSymbols.value
      : splitSymbolInput(backtestForm.symbols)
    if (!symbols.length) return
    if (!chartSymbol.value) chartSymbol.value = symbols[0]
    const requestId = ++latestKlineRequestId.value
    const requestSymbol = chartSymbol.value
    const requestMarket = backtestForm.market
    klineLoading.value = true
    klineError.value = ''
    try {
      const { data } = await api.get('/quant/klines', {
        params: {
          symbol: requestSymbol,
          market: requestMarket,
          start: backtestForm.start || undefined,
          end: backtestForm.end || undefined,
          limit: 2000
        }
      })
      if (requestId !== latestKlineRequestId.value) return
      const items = data.data?.items || []
      if (!items.length) {
        klineData.value = []
        hoverInfo.value = null
        updateChartData()
        throw new Error(`No data for ${requestSymbol}`)
      }
      klineData.value = items.slice().sort((a, b) => {
        const left = toDateInt(a.date) || 0
        const right = toDateInt(b.date) || 0
        return left - right
      })
      chartWindow.offset = 0
      await nextTick()
      updateChartData()
    } catch (err) {
      if (requestId !== latestKlineRequestId.value) return
      klineData.value = []
      hoverInfo.value = null
      updateChartData()
      klineError.value = err?.message || String(err)
    } finally {
      if (requestId !== latestKlineRequestId.value) return
      klineLoading.value = false
    }
  }

  const syncAnalysisToChart = async () => {
    if (!analysisResult.value) return
    if (analysisResult.value.symbol) {
      chartSymbol.value = analysisResult.value.symbol
      if (!backtestForm.symbols) {
        backtestForm.symbols = analysisResult.value.symbol
      }
    }
    backtestForm.market = toolForm.market
    if (toolForm.start) backtestForm.start = toolForm.start
    if (toolForm.end) backtestForm.end = toolForm.end
    analysisOverlayEnabled.value = true
    activeTab.value = 'strategy'
    await nextTick()
    await loadKlineChart()
  }

  const handleResize = () => {
    ensureChart()
    ensureEquityChart()
    if (chartRef.value && klineContainer.value) {
      chartRef.value.applyOptions({ width: klineContainer.value.clientWidth })
    }
    if (equityChartRef.value && equityContainer.value) {
      equityChartRef.value.applyOptions({ width: equityContainer.value.clientWidth })
    }
    if (klineData.value.length) updateChartData()
    if (equityData.value.length) updateEquityChart()
  }

  const cleanupCharts = () => {
    if (chartRef.value) {
      chartRef.value.remove()
      chartRef.value = null
    }
    if (equityChartRef.value) {
      equityChartRef.value.remove()
      equityChartRef.value = null
    }
  }

  return {
    klineData,
    equityData,
    klineLoading,
    klineError,
    hoverInfo,
    setKlineContainer,
    setEquityContainer,
    formatKlineDate,
    orderKey,
    resolveOrderProfit,
    selectOrder,
    shiftWindow,
    loadKlineChart,
    syncAnalysisToChart,
    updateChartData,
    updateEquityChart,
    applyOrderLines,
    applyAnalysisOverlay,
    syncSelectedOrder,
    handleResize,
    cleanupCharts
  }
}
