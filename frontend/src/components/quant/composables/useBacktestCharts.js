import { nextTick, ref } from 'vue'
import { api } from '../../../services/api'
import { splitSymbolInput } from '../utils/symbols'
import {
  buildCandleSeriesData,
  buildEquitySeries,
  buildVolumeSeriesData,
  formatKlineDate,
  formatNumber,
  isClosedOrder,
  orderKey,
  resolveOrderProfit,
  toChartTime,
  toDateInt
} from '../utils/chartDomain'
import {
  buildAnalysisOverlaySpecs,
  buildChartMarkers,
  buildPriceLineSpecs
} from '../utils/chartOverlays'
import {
  createEquityChartRuntime,
  createKlineChartRuntime,
  destroyChartRuntime,
  resizeChartRuntime
} from '../utils/chartRuntime'

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
    const runtime = createKlineChartRuntime({
      container: klineContainer.value,
      onCrosshairMove: (param) => {
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
      }
    })
    if (!runtime) return
    chartRef.value = runtime.chart
    candleSeries.value = runtime.candleSeries
    volumeSeries.value = runtime.volumeSeries
  }

  const ensureEquityChart = () => {
    if (equityChartRef.value || !equityContainer.value) return
    const runtime = createEquityChartRuntime({
      container: equityContainer.value
    })
    if (!runtime) return
    equityChartRef.value = runtime.chart
    equitySeries.value = runtime.equitySeries
  }

  const buildMarkers = () => {
    return buildChartMarkers({
      overlayMode: resolveChartOverlayMode(),
      orders: getValidChartOrders(),
      klineData: klineData.value,
      predictionSignal: predictionSignal?.value,
      operationSuggestion: operationSuggestion?.value,
      chartSymbol: chartSymbol.value
    })
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
    const lineSpecs = buildPriceLineSpecs({
      overlayMode: resolveChartOverlayMode(),
      selectedOrder: selectedOrder.value,
      showStopLines: showStopLines.value,
      predictionSignal: predictionSignal?.value,
      operationSuggestion: operationSuggestion?.value,
      chartSymbol: chartSymbol.value,
      klineData: klineData.value
    })
    orderPriceLines.value = lineSpecs.map((spec) =>
      candleSeries.value.createPriceLine({
        ...spec,
        axisLabelVisible: true
      })
    )
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
    if (!chartRef.value) return
    const specs = buildAnalysisOverlaySpecs({
      analysisOverlayEnabled: analysisOverlayEnabled.value,
      analysisResult: analysisResult.value,
      chartSymbol: chartSymbol.value,
      klineData: klineData.value
    })
    specs.forEach((spec) => {
      const series = chartRef.value.addLineSeries({
        color: spec.color,
        lineWidth: spec.lineWidth,
        lineStyle: spec.lineStyle
      })
      series.setData(spec.data)
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
    candleSeries.value.setData(buildCandleSeriesData(data))
    volumeSeries.value.setData(buildVolumeSeriesData(data))
    candleSeries.value.setMarkers(buildMarkers())
    applyVisibleRange()
    applyOrderLines()
    applyAnalysisOverlay()
  }

  const updateEquityChart = () => {
    const points = buildEquitySeries({
      backtestJob: backtestJob.value,
      backtestOrders: backtestOrders.value,
      chartSymbol: chartSymbol.value
    })
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
    resizeChartRuntime({ chart: chartRef.value, container: klineContainer.value })
    resizeChartRuntime({ chart: equityChartRef.value, container: equityContainer.value })
    if (klineData.value.length) updateChartData()
    if (equityData.value.length) updateEquityChart()
  }

  const cleanupCharts = () => {
    destroyChartRuntime(chartRef.value)
    destroyChartRuntime(equityChartRef.value)
    chartRef.value = null
    equityChartRef.value = null
    candleSeries.value = null
    volumeSeries.value = null
    equitySeries.value = null
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
