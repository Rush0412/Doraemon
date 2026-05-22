import { reactive, ref, watch } from 'vue'

export function useTrendAnalysisDemo({
  market,
  store,
  inferMarketBySymbol,
  defaultSymbolForMarket,
  applySymbolToBacktest
}) {
  const trendForm = reactive({
    market: market.value,
    symbol: defaultSymbolForMarket(market.value),
    horizon_days: 5,
    note: ''
  })

  const trendFeatureInput = ref(
    JSON.stringify(
      [
        { trade_date: '2026-05-20', close: 12.31, ma5: 12.12, ma20: 11.84, rsi14: 61.2, macd: 0.18 },
        { trade_date: '2026-05-21', close: 12.45, ma5: 12.2, ma20: 11.9, rsi14: 63.5, macd: 0.21 }
      ],
      null,
      2
    )
  )

  const trendBusy = ref(false)
  const trendError = ref('')
  const trendDemoResult = ref(null)
  const trendImagePreview = ref('')
  const trendImageMeta = ref(null)

  const revokeTrendPreview = () => {
    if (trendImagePreview.value && trendImagePreview.value.startsWith('blob:')) {
      URL.revokeObjectURL(trendImagePreview.value)
    }
  }

  const clearTrendImage = () => {
    revokeTrendPreview()
    trendImagePreview.value = ''
    trendImageMeta.value = null
  }

  const handleTrendImageChange = (event) => {
    const file = event?.target?.files?.[0]
    if (!file) {
      clearTrendImage()
      return
    }
    revokeTrendPreview()
    trendImagePreview.value = URL.createObjectURL(file)
    trendImageMeta.value = {
      name: file.name,
      type: file.type,
      sizeKb: Number((file.size / 1024).toFixed(1))
    }
  }

  const parseTrendFeatureRows = () => {
    const raw = String(trendFeatureInput.value || '').trim()
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      throw new Error('特征 JSON 必须是数组格式')
    }
    return parsed
  }

  const runTrendDemo = async () => {
    trendBusy.value = true
    trendError.value = ''
    try {
      const effectiveMarket = inferMarketBySymbol(trendForm.symbol, trendForm.market)
      trendForm.market = effectiveMarket
      const result = await store.runTrendAnalysisDemo({
        market: effectiveMarket,
        symbol: trendForm.symbol,
        horizon_days: trendForm.horizon_days,
        chart_image_name: trendImageMeta.value?.name,
        chart_image_type: trendImageMeta.value?.type,
        chart_image_size_kb: trendImageMeta.value?.sizeKb,
        feature_rows: parseTrendFeatureRows(),
        note: trendForm.note || undefined
      })
      trendDemoResult.value = result
      if (trendForm.symbol) {
        applySymbolToBacktest(trendForm.symbol)
      }
    } catch (err) {
      trendError.value = err?.message || String(err)
    } finally {
      trendBusy.value = false
    }
  }

  watch(market, (val) => {
    trendForm.market = val
    if (!trendForm.symbol) {
      trendForm.symbol = defaultSymbolForMarket(val)
    }
  })

  return {
    trendForm,
    trendFeatureInput,
    trendBusy,
    trendError,
    trendDemoResult,
    trendImagePreview,
    trendImageMeta,
    clearTrendImage,
    handleTrendImageChange,
    runTrendDemo,
    revokeTrendPreview
  }
}
