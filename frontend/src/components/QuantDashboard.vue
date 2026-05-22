<template>
  <div class="quant-shell">
    <section class="hero">
      <div class="hero-head">
        <div>
          <p class="eyebrow">量化任务中心</p>
          <h1>量化交易指挥台</h1>
          <p class="hero-sub">
            数据更新、策略回测、参数寻优、量化分析与当日建议的一体化闭环。
          </p>
          <p v-if="initError" class="error hero-error">{{ initError }}</p>
        </div>
        <div class="hero-actions">
          <button class="btn-ghost" @click="refreshJobs" :disabled="actionsBusy">刷新任务</button>
          <button class="btn-primary" @click="runVerify" :disabled="actionsBusy">环境验证</button>
        </div>
      </div>
      <div class="hero-metrics">
        <div class="metric-card">
          <p class="metric-label">任务总数</p>
          <p class="metric-value">{{ jobStats.total }}</p>
        </div>
        <div class="metric-card">
          <p class="metric-label">运行中</p>
          <p class="metric-value">{{ jobStats.running }}</p>
        </div>
        <div class="metric-card">
          <p class="metric-label">成功</p>
          <p class="metric-value">{{ jobStats.succeeded }}</p>
        </div>
        <div class="metric-card">
          <p class="metric-label">失败</p>
          <p class="metric-value">{{ jobStats.failed }}</p>
        </div>
      </div>
    </section>
    <section class="flow-nav">
      <div class="flow-track">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['flow-step', { active: activeTab === tab.id }]"
          @click="setTab(tab.id)"
        >
          <span class="flow-step-index">{{ tab.step }}</span>
          <span class="flow-step-title">{{ tab.title }}</span>
          <span class="flow-step-sub">{{ tab.subtitle }}</span>
        </button>
      </div>
      <div class="flow-context">
        <div>
          <p class="eyebrow">当前步骤</p>
          <h2>{{ activeTabMeta.title }}</h2>
          <p class="muted">{{ activeTabMeta.hint }}</p>
        </div>
        <div class="flow-actions">
          <button class="btn-secondary" @click="goPrev" :disabled="isFirstTab">上一步</button>
          <button class="btn-primary" @click="goNext" :disabled="isLastTab">下一步</button>
        </div>
      </div>
    </section>
    <PreparePanel
      :active="activeTab === 'prepare'"
      :store="store"
      v-model:market="market"
      v-model:query="query"
      v-model:kind="kind"
      v-model:pageSize="pageSize"
      v-model:selectedPortfolio="selectedPortfolio"
      v-model:portfolioDraftName="portfolioDraftName"
      :selected-symbols="selectedSymbols"
      :saved-portfolios="savedPortfolios"
      :portfolio-save-open="portfolioSaveOpen"
      :portfolio-save-error="portfolioSaveError"
      :update-form="updateForm"
      :last-update-summary="lastUpdateSummary"
      :total-pages="totalPages"
      :actions-busy="actionsBusy"
      :search="search"
      :import-symbols="importSymbols"
      :import-all-symbols="importAllSymbols"
      :select-page="selectPage"
      :invert-page="invertPage"
      :display-symbol="displaySymbol"
      :display-market="displayMarket"
      :display-exchange="displayExchange"
      :format-selected-symbol="formatSelectedSymbol"
      :display-kind="displayKind"
      :toggle-symbol="toggleSymbol"
      :is-selected="isSelected"
      :clear-symbols="clearSymbols"
      :save-selection="saveSelection"
      :confirm-save-selection="confirmSaveSelection"
      :cancel-save-selection="cancelSaveSelection"
      :load-portfolio="loadPortfolio"
      :delete-portfolio="deletePortfolio"
      :remove-symbol="removeSymbol"
      :change-page="changePage"
      :apply-page-size="applyPageSize"
      :run-kl-update="runKlUpdate"
      :run-market-coverage-update="runMarketCoverageUpdate"
      :run-full-ashare-update="runFullAshareUpdate"
    />
    <StrategyPanel
      :active="activeTab === 'strategy'"
      :backtest-form="backtestForm"
      :grid-form="gridForm"
      :strategy-error="strategyError"
      v-model:grid-use-backtest-base="gridUseBacktestBase"
      v-model:grid-explore-all-strategies="gridExploreAllStrategies"
      :buy-strategies="buyStrategies"
      :sell-strategies="sellStrategies"
      :active-buy-strategy="activeBuyStrategy"
      :active-sell-strategy="activeSellStrategy"
      :grid-buy-param-lists="gridBuyParamLists"
      :grid-sell-param-lists="gridSellParamLists"
      v-model:buy-strategy-id="buyStrategyId"
      v-model:sell-strategy-id="sellStrategyId"
      :buy-strategy-params="buyStrategyParams"
      :sell-strategy-params="sellStrategyParams"
      :run-backtest="runBacktest"
      :run-stock-select="runStockSelect"
      :run-closed-loop="runClosedLoop"
      :actions-busy="actionsBusy"
      :backtest-summary="backtestSummary"
      :backtest-top-symbols="backtestTopSymbols"
      :backtest-actionable-candidates="backtestActionableCandidates"
      :backtest-trade-stats="backtestTradeStats"
      :backtest-symbols="backtestSymbols"
      v-model:chart-symbol="chartSymbol"
      v-model:order-filter="orderFilter"
      v-model:selected-order-key="selectedOrderKey"
      v-model:show-stop-lines="showStopLines"
      :chart-window="chartWindow"
      :kline-loading="klineLoading"
      :kline-error="klineError"
      :hover-info="hoverInfo"
      :kline-data="klineData"
      :equity-data="equityData"
      :operation-suggestion="operationSuggestion"
      v-model:advice-profile="adviceProfile"
      :advice-templates="adviceTemplates"
      :filtered-orders="filteredOrders"
      :paged-orders="pagedOrders"
      v-model:order-page="orderPage"
      v-model:order-page-size="orderPageSize"
      :order-total-pages="orderTotalPages"
      :order-key="orderKey"
      :format-number="formatNumber"
      :format-kline-date="formatKlineDate"
      :resolve-order-profit="resolveOrderProfit"
      :select-order="selectOrder"
      :shift-window="shiftWindow"
      :load-kline-chart="loadKlineChart"
      :show-backtest-visual="showBacktestVisual"
      :run-grid-search="runGridSearch"
      :grid-summary="gridSummary"
      :grid-diagnostics="gridDiagnostics"
      :stock-select-summary="stockSelectSummary"
      :stock-select-diagnostics="stockSelectDiagnostics"
      :stock-select-top-symbols="stockSelectTopSymbols"
      :stock-select-actionable-candidates="stockSelectActionableCandidates"
      :stock-select-recommendation="stockSelectRecommendation"
      :grid-top-symbols="gridTopSymbols"
      :grid-actionable-candidates="gridActionableCandidates"
      :grid-recommendation="gridRecommendation"
      :grid-errors="gridErrors"
      :grid-next-param-suggestions="gridNextParamSuggestions"
      :grid-top-runs="gridTopRuns"
      :grid-summary-text="gridSummaryText"
      :apply-grid-to-backtest="applyGridToBacktest"
      :apply-grid-run-to-backtest="applyGridRunToBacktest"
      :apply-grid-next-suggestions="applyGridNextSuggestions"
      :apply-symbol-to-backtest="applySymbolToBacktest"
      :apply-symbol-to-analysis="applySymbolToAnalysis"
      :format-symbol-text="formatSymbolText"
      :format-selected-symbol="formatSelectedSymbol"
      :set-kline-container="setKlineContainer"
      :set-equity-container="setEquityContainer"
    />
    <AnalysisPanel
      :active="activeTab === 'tools'"
      :tool-form="toolForm"
      :tool-options="toolOptions"
      :tool-option-mode="toolOptionMode"
      :analysis-result="analysisResult"
      :analysis-text="analysisText"
      :analysis-error="analysisError"
      :analysis-status-text="analysisStatusText"
      :analysis-overlay-enabled="analysisOverlayEnabled"
      :set-analysis-overlay-enabled="setAnalysisOverlayEnabled"
      :run-tool="runTool"
      :sync-analysis-to-chart="syncAnalysisToChart"
      :actions-busy="actionsBusy"
    />
    <MlPanel
      :active="activeTab === 'ml'"
      :actions-busy="actionsBusy"
      :ml-running="mlRunning"
      :ml-loading="store.mlLoading"
      :ml-error="store.mlError"
      :ml-feature-form="mlFeatureForm"
      :ml-train-form="mlTrainForm"
      :ml-predict-form="mlPredictForm"
      :ml-select-form="mlSelectForm"
      :ml-feature-result="mlFeatureResult"
      :ml-train-result="mlTrainResult"
      :ml-predict-result="mlPredictResult"
      :ml-select-result="mlSelectResult"
      :ml-models="store.mlModels"
      :ml-predictions="store.mlPredictions"
      :run-ml-feature-build="runMlFeatureBuild"
      :run-ml-train="runMlTrain"
      :run-ml-predict="runMlPredict"
      :run-ml-stock-select="runMlStockSelect"
      :run-ml-pipeline="runMlPipeline"
      :run-market-model-pipeline="runMarketModelPipeline"
      :refresh-ml-data="refreshMlData"
      :use-ml-model="useMlModel"
      :promote-ml-model="promoteMlModel"
      :load-model-training-params="loadModelTrainingParams"
      :apply-prediction-to-backtest="applyPredictionToBacktest"
      :apply-prediction-to-pool="applyPredictionToPool"
    />
    <TrendAnalysisPanel
      :active="activeTab === 'trend'"
      :trend-form="trendForm"
      v-model:trendFeatureInput="trendFeatureInput"
      :trend-demo-result="trendDemoResult"
      :trend-busy="trendBusy"
      :trend-error="trendError"
      :trend-image-preview="trendImagePreview"
      :trend-image-meta="trendImageMeta"
      :handle-trend-image-change="handleTrendImageChange"
      :clear-trend-image="clearTrendImage"
      :run-trend-demo="runTrendDemo"
      :apply-symbol-to-backtest="applySymbolToBacktest"
    />
    <JobsPanel
      :active="activeTab === 'jobs'"
      :store="store"
      :format-time="formatTime"
      :brief="brief"
      :export-url="exportUrl"
      :job-export-sections="jobExportSections"
      :select-job="selectJob"
      :remove-job="removeJob"
      :batch-delete-finished="batchDeleteFinished"
      :batch-delete-failed="batchDeleteFailed"
      :active-params-text="activeParamsText"
      :active-result-text="activeResultText"
      :active-error-text="activeErrorText"
    />
  </div>
</template>
<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import PreparePanel from './quant/PreparePanel.vue'
import StrategyPanel from './quant/StrategyPanel.vue'
import AnalysisPanel from './quant/AnalysisPanel.vue'
import MlPanel from './quant/MlPanel.vue'
import TrendAnalysisPanel from './quant/TrendAnalysisPanel.vue'
import JobsPanel from './quant/JobsPanel.vue'
import { useBacktestCharts } from './quant/composables/useBacktestCharts'
import { useJobTracking } from './quant/composables/useJobTracking'
import { useMlWorkflow } from './quant/composables/useMlWorkflow'
import { useOperationSuggestion } from './quant/composables/useOperationSuggestion'
import { usePrepareWorkflow } from './quant/composables/usePrepareWorkflow'
import { useQuantExecution } from './quant/composables/useQuantExecution'
import { useQuantSettings } from './quant/composables/useQuantSettings'
import { useTrendAnalysisDemo } from './quant/composables/useTrendAnalysisDemo'
import { quantDashboardTabs } from './quant/config/dashboardTabs'
import {
  displayExchange,
  displayKind,
  displayMarket,
  displaySymbol,
  formatSelectedSymbol as formatSelectedSymbolUtil,
  formatSymbolText as formatSymbolTextUtil,
  inferMarketBySymbol,
  inferMarketBySymbols,
  normalizeSymbolsInputForUi,
  splitSymbolInput,
  symbolEquals
} from './quant/utils/symbols'
import {
  applyGridDefaults,
  applyStrategyDefaults,
  resetGridParamLists,
  resetStrategyParams
} from './quant/utils/strategyGrid'
import {
  brief,
  defaultSymbolForMarket,
  formatNumber,
  formatTime
} from './quant/utils/dashboardFormatters'
import { useQuantStore } from '../stores/quantStore'
const store = useQuantStore()
const tabs = quantDashboardTabs
const activeTab = ref('prepare')
const activeTabMeta = computed(() => tabs.find((tab) => tab.id === activeTab.value) || tabs[0])
const tabIndex = computed(() => tabs.findIndex((tab) => tab.id === activeTab.value))
const isFirstTab = computed(() => tabIndex.value <= 0)
const isLastTab = computed(() => tabIndex.value >= tabs.length - 1)
const setTab = (id) => {
  activeTab.value = id
}
const goPrev = () => {
  if (isFirstTab.value) return
  activeTab.value = tabs[tabIndex.value - 1].id
}
const goNext = () => {
  if (isLastTab.value) return
  activeTab.value = tabs[tabIndex.value + 1].id
}
const market = ref(store.market)
const query = ref(store.query)
const kind = ref(store.kind)
const pageSize = ref(store.pageSize)
const selectedSymbols = ref([])
const chartSymbol = ref('')
const orderFilter = ref('all')
const selectedOrderKey = ref('')
const selectedOrder = ref(null)
const predictionSignal = ref(null)
const showStopLines = ref(true)
const analysisOverlayEnabled = ref(true)
const gridUseBacktestBase = ref(true)
const gridExploreAllStrategies = ref(true)
const flowRunning = ref(false)
const trackedJobRunning = ref(false)
const orderPage = ref(1)
const orderPageSize = ref(20)
const initError = ref('')
const strategyError = ref('')
const {
  jobStats,
  lastUpdateSummary,
  latestJobByType,
  refreshJobs,
  selectJob,
  removeJob,
  batchDeleteFinished,
  batchDeleteFailed,
  exportUrl,
  jobExportSections,
  activeParamsText,
  activeResultText,
  activeErrorText,
  waitForJobDone,
  runTrackedJob
} = useJobTracking({
  store,
  trackedJobRunning
})
const setAnalysisOverlayEnabled = (value) => {
  analysisOverlayEnabled.value = value
}
const updateForm = reactive({
  market: market.value,
  n_folds: 1,
  start: '',
  end: '',
  n_jobs: 8,
  how: 'thread',
  symbols: '',
  coverage_mode: 'below_min_rows',
  min_kline_rows: 120
})
const backtestForm = reactive({
  market: market.value,
  symbols: '',
  cash: 1000000,
  commission_rate: 0.00025,
  min_commission: 5,
  stamp_tax_rate: 0.0005,
  slippage_bp: 2,
  buy_xd: 42,
  stop_loss_n: 0.5,
  stop_win_n: 3.0,
  n_folds: 1,
  start: '',
  end: ''
})
const buyStrategyId = ref('breakout')
const sellStrategyId = ref('atr_stop')
const buyStrategyParams = reactive({})
const sellStrategyParams = reactive({})
const gridBuyParamLists = reactive({})
const gridSellParamLists = reactive({})
const gridForm = reactive({
  market: market.value,
  symbols: '',
  cash: 1000000,
  buy_xd_list: '20, 42, 60',
  stop_loss_n_list: '0.5, 1.0',
  stop_win_n_list: '2.0, 3.0',
  buy_strategies: '',
  sell_strategies: '',
  validation_mode: 'none',
  train_ratio: 0.7,
  walk_forward_days: 365,
  walk_forward_step_days: 180,
  ranking_metric: 'profit',
  ranking_weights: {
    profit: 1.0,
    win_rate: 1.0,
    sharpe: 1.0,
    annual_return: 1.0,
    drawdown: 1.0
  },
  symbol_top_n: 10,
  symbol_eval_limit: 3000,
  n_folds: 1,
  start: '',
  end: '',
  max_runs: 50
})
if (!gridForm.ranking_weights || typeof gridForm.ranking_weights !== 'object') {
  gridForm.ranking_weights = {
    profit: 1.0,
    win_rate: 1.0,
    sharpe: 1.0,
    annual_return: 1.0,
    drawdown: 1.0
  }
}
const toolForm = reactive({
  market: market.value,
  tool: 'support_resistance',
  symbols: '',
  n_folds: 1,
  start: '',
  end: '',
  limit: 200
})
const toolOptions = reactive({
  only_last: true,
  mode: 'stats',
  jump_diff_factor: 1.0,
  power_threshold: 2.0,
  weight_a: 0.5,
  weight_b: 0.5,
  benchmark: '',
  resample: 5,
  speed_key: 'close',
  step_x: 1.0,
  shift_mode: 'close',
  regress_mode: 'best',
  corr_type: 'pears',
  distance_type: 'manhattan',
  field: 'p_change'
})
const formatSelectedSymbol = (symbol, fallbackMarket = backtestForm.market) =>
  formatSelectedSymbolUtil(symbol, fallbackMarket)
const formatSymbolText = (rawSymbols, fallbackMarket = backtestForm.market) =>
  formatSymbolTextUtil(rawSymbols, fallbackMarket)
const actionsBusy = computed(
  () => store.jobsLoading || store.activeJobLoading || store.symbolsLoading || flowRunning.value || trackedJobRunning.value
)
const buyStrategies = computed(() => store.strategies?.buy || [])
const sellStrategies = computed(() => store.strategies?.sell || [])
const activeBuyStrategy = computed(() =>
  buyStrategies.value.find((item) => item.id === buyStrategyId.value) || null
)
const activeSellStrategy = computed(() =>
  sellStrategies.value.find((item) => item.id === sellStrategyId.value) || null
)
if (!backtestForm.symbols) backtestForm.symbols = defaultSymbolForMarket(market.value)
if (!gridForm.symbols) gridForm.symbols = defaultSymbolForMarket(market.value)
if (!toolForm.symbols) toolForm.symbols = defaultSymbolForMarket(market.value)
watch(market, (val) => {
  updateForm.market = val
  backtestForm.market = val
  gridForm.market = val
  toolForm.market = val
  trendForm.market = val
  if (!backtestForm.symbols) backtestForm.symbols = defaultSymbolForMarket(val)
  if (!gridForm.symbols) gridForm.symbols = defaultSymbolForMarket(val)
  if (!toolForm.symbols) toolForm.symbols = defaultSymbolForMarket(val)
  if (!trendForm.symbol) trendForm.symbol = defaultSymbolForMarket(val)
})
watch(
  () => backtestForm.symbols,
  (val) => {
    const normalized = normalizeSymbolsInputForUi(val)
    if (normalized !== val) backtestForm.symbols = normalized
  }
)
watch(
  () => gridForm.symbols,
  (val) => {
    const normalized = normalizeSymbolsInputForUi(val)
    if (normalized !== val) gridForm.symbols = normalized
  }
)
watch(
  () => toolForm.symbols,
  (val) => {
    const normalized = normalizeSymbolsInputForUi(val)
    if (normalized !== val) toolForm.symbols = normalized
  }
)
watch(buyStrategies, (list) => {
  if (!list.length) return
  if (!list.find((item) => item.id === buyStrategyId.value)) {
    buyStrategyId.value = list[0].id
  }
  applyStrategyDefaults(activeBuyStrategy.value, buyStrategyParams)
  applyGridDefaults(activeBuyStrategy.value, gridBuyParamLists, gridForm)
})
watch(sellStrategies, (list) => {
  if (!list.length) return
  if (!list.find((item) => item.id === sellStrategyId.value)) {
    sellStrategyId.value = list[0].id
  }
  applyStrategyDefaults(activeSellStrategy.value, sellStrategyParams)
  applyGridDefaults(activeSellStrategy.value, gridSellParamLists, gridForm)
})
watch(buyStrategyId, () => {
  resetStrategyParams(activeBuyStrategy.value, buyStrategyParams)
  resetGridParamLists(activeBuyStrategy.value, gridBuyParamLists, gridForm)
})
watch(sellStrategyId, () => {
  resetStrategyParams(activeSellStrategy.value, sellStrategyParams)
  resetGridParamLists(activeSellStrategy.value, gridSellParamLists, gridForm)
})
watch(
  () => backtestForm.buy_xd,
  (val) => {
    if (['breakout', 'momentum_break', 'put_break', 'put_xdbk'].includes(buyStrategyId.value)) {
      buyStrategyParams.xd = val
    }
  }
)
watch(
  () => [backtestForm.stop_loss_n, backtestForm.stop_win_n],
  ([loss, win]) => {
    if (['atr_stop', 'atr_close', 'atr_pre'].includes(sellStrategyId.value)) {
      sellStrategyParams.stop_loss_n = loss
      sellStrategyParams.stop_win_n = win
    }
  }
)
const backtestJob = computed(() => {
  if (store.activeJob && store.activeJob.type === 'backtest') return store.activeJob
  return latestJobByType('backtest')
})
const backtestSummary = computed(() => backtestJob.value?.result?.summary || null)
const backtestTopSymbols = computed(() => {
  const rows = backtestJob.value?.result?.top_symbols
  return Array.isArray(rows) ? rows : []
})
const backtestActionableCandidates = computed(() => {
  const rows = backtestJob.value?.result?.actionable_candidates
  return Array.isArray(rows) ? rows : []
})
const backtestOrders = computed(() => backtestJob.value?.result?.orders || [])
const chartOrdersAll = computed(() => {
  const orders = backtestOrders.value || []
  if (!chartSymbol.value) return orders
  return orders.filter((item) => symbolEquals(item.symbol, chartSymbol.value))
})
const filteredOrders = computed(() => {
  const scoped = chartOrdersAll.value
  if (orderFilter.value === 'win') return scoped.filter((item) => resolveOrderProfit(item) > 0)
  if (orderFilter.value === 'loss') return scoped.filter((item) => resolveOrderProfit(item) < 0)
  if (orderFilter.value === 'hold') {
    return scoped.filter((item) => {
      const sellDate = Number(item.sell_date || 0)
      return !sellDate
    })
  }
  return scoped
})
const orderTotalPages = computed(() => {
  const total = filteredOrders.value.length
  return Math.max(1, Math.ceil(total / orderPageSize.value))
})
const pagedOrders = computed(() => {
  const total = filteredOrders.value.length
  if (!total) return []
  const page = Math.min(orderPage.value, orderTotalPages.value)
  const start = (page - 1) * orderPageSize.value
  const end = start + orderPageSize.value
  return filteredOrders.value.slice(start, end)
})
const backtestSymbols = computed(() => {
  const raw = backtestJob.value?.result?.summary?.symbols || backtestJob.value?.params?.symbols
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') return splitSymbolInput(raw)
  return []
})
const isClosedOrder = (order) => {
  if (!order) return false
  const sellDate = Number(order.sell_date || 0)
  const sellPrice = Number(order.sell_price)
  return sellDate > 0 && Number.isFinite(sellPrice) && sellPrice > 0
}
const backtestTradeStats = computed(() => {
  const orders = backtestOrders.value || []
  const closedOrders = orders.filter((item) => isClosedOrder(item))
  if (!closedOrders.length) return null
  const profits = closedOrders.map((item) => Number(resolveOrderProfit(item) || 0))
  const total = closedOrders.length
  const wins = profits.filter((p) => p > 0).length
  const totalProfit = profits.reduce((sum, val) => sum + val, 0)
  const avgProfit = total ? totalProfit / total : 0
  return {
    total,
    wins,
    winRate: total ? (wins / total) * 100 : 0,
    totalProfit,
    avgProfit
  }
})
const showBacktestVisual = computed(() => {
  return (
    !!backtestSummary.value ||
    !!chartSymbol.value ||
    klineLoading.value ||
    (klineData.value && klineData.value.length > 0)
  )
})
const chartWindow = reactive({
  size: 220,
  offset: 0
})
const gridJob = computed(() => {
  if (store.activeJob && store.activeJob.type === 'grid_search') return store.activeJob
  return latestJobByType('grid_search')
})
const stockSelectJob = computed(() => {
  if (store.activeJob && store.activeJob.type === 'stock_select') return store.activeJob
  return latestJobByType('stock_select')
})
const stockSelectSummary = computed(() => stockSelectJob.value?.result?.summary || null)
const stockSelectDiagnostics = computed(() => stockSelectJob.value?.result?.diagnostics || null)
const stockSelectTopSymbols = computed(() => {
  const rows = stockSelectJob.value?.result?.top_symbols
  return Array.isArray(rows) ? rows : []
})
const stockSelectActionableCandidates = computed(() => {
  const rows = stockSelectJob.value?.result?.actionable_candidates
  return Array.isArray(rows) ? rows : []
})
const stockSelectRecommendation = computed(() => stockSelectJob.value?.result?.recommendation || null)
const gridSummary = computed(() => gridJob.value?.result?.best || null)
const gridDiagnostics = computed(() => gridJob.value?.result?.diagnostics || null)
const gridTopSymbols = computed(() => {
  const rows = gridJob.value?.result?.top_symbols
  return Array.isArray(rows) ? rows : []
})
const gridActionableCandidates = computed(() => {
  const rows = gridJob.value?.result?.actionable_candidates
  return Array.isArray(rows) ? rows : []
})
const gridRecommendation = computed(() => gridJob.value?.result?.recommendation || null)
const gridErrors = computed(() => {
  const rows = gridJob.value?.result?.errors
  return Array.isArray(rows) ? rows : []
})
const gridNextParamSuggestions = computed(() => gridJob.value?.result?.next_param_suggestions || null)
const pickGridMetric = (run, key, fallback = 0) => {
  if (!run) return fallback
  const validationValue = run[`validation_${key}`]
  if (validationValue !== undefined && validationValue !== null && Number.isFinite(Number(validationValue))) {
    return Number(validationValue)
  }
  const raw = run[key]
  if (raw !== undefined && raw !== null && Number.isFinite(Number(raw))) {
    return Number(raw)
  }
  return fallback
}
const gridTopRuns = computed(() => {
  const runs = Array.isArray(gridJob.value?.result?.runs) ? gridJob.value.result.runs : []
  return runs.slice(0, 10).map((run, idx) => ({
    ...run,
    rank: idx + 1,
    score: Number(
      (
        Number.isFinite(Number(run?.custom_score))
          ? Number(run.custom_score)
          : pickGridMetric(run, 'profit_sum') * 0.55 +
            pickGridMetric(run, 'win_rate') * 0.25 +
            pickGridMetric(run, 'sharpe') * 10 -
            pickGridMetric(run, 'max_drawdown') * 100
      ).toFixed(2)
    )
  }))
})
const analysisJob = computed(() => {
  if (store.activeJob?.type === 'analysis') return store.activeJob
  return latestJobByType('analysis')
})
const analysisResult = computed(() => analysisJob.value?.result || null)
const analysisError = computed(() =>
  analysisJob.value?.status === 'failed' ? analysisJob.value?.error || '分析任务执行失败。' : ''
)
const analysisStatusText = computed(() => {
  if (!analysisJob.value) return ''
  if (analysisJob.value.status === 'running' || analysisJob.value.status === 'queued') {
    return `分析任务 #${analysisJob.value.id} 执行中`
  }
  if (analysisJob.value.status === 'failed') {
    return '最近一次分析任务执行失败'
  }
  return `最近一次分析任务 #${analysisJob.value.id} 已完成`
})
const gridSummaryText = computed(() =>
  gridSummary.value ? JSON.stringify(gridSummary.value, null, 2) : ''
)
const analysisText = computed(() =>
  analysisResult.value ? JSON.stringify(analysisResult.value, null, 2) : ''
)
const { adviceProfile, adviceTemplates, operationSuggestion } = useOperationSuggestion({
  analysisResult,
  backtestTradeStats,
  gridSummary,
  gridDiagnostics,
  gridTopRuns
})
const { settingsReady, restoreQuantSettings, scheduleSaveQuantSettings, clearSettingsSaveTimer } = useQuantSettings({
  market,
  query,
  kind,
  pageSize,
  backtestForm,
  gridForm,
  toolForm,
  updateForm,
  buyStrategyId,
  sellStrategyId,
  buyStrategyParams,
  sellStrategyParams,
  gridBuyParamLists,
  gridSellParamLists,
  gridUseBacktestBase,
  gridExploreAllStrategies,
  adviceProfile,
  adviceTemplates
})
const {
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
} = useBacktestCharts({
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
})
watch(backtestSummary, (val) => {
  if (!val) return
  const symbols = backtestSymbols.value
  if (symbols.length && !chartSymbol.value) {
    chartSymbol.value = symbols[0]
  }
  if (chartSymbol.value) {
    loadKlineChart()
  }
  nextTick(() => {
    updateEquityChart()
  })
})
watch(chartSymbol, (val, oldVal) => {
  if (!val || val === oldVal) return
  loadKlineChart()
})
watch(
  () => [chartWindow.size, chartWindow.offset, klineData.value.length],
  () => {
    if (klineData.value.length) updateChartData()
  }
)
watch(filteredOrders, () => {
  orderPage.value = 1
  syncSelectedOrder()
  if (klineData.value.length) updateChartData()
  updateEquityChart()
})
watch(selectedOrderKey, () => {
  syncSelectedOrder()
})
watch(orderPageSize, () => {
  orderPage.value = 1
})
watch(selectedOrder, () => {
  applyOrderLines()
})
watch(predictionSignal, () => {
  if (klineData.value.length) updateChartData()
  applyOrderLines()
})
watch(showStopLines, () => {
  applyOrderLines()
})
watch([analysisResult, analysisOverlayEnabled], () => {
  if (klineData.value.length) applyAnalysisOverlay()
})
watch(activeTab, async (val) => {
  if (val !== 'strategy') return
  await nextTick()
  handleResize()
})
watch(
  () => [
    market.value,
    query.value,
    kind.value,
    pageSize.value,
    buyStrategyId.value,
    sellStrategyId.value,
    gridUseBacktestBase.value,
    gridExploreAllStrategies.value,
    adviceProfile.value,
  ],
  () => {
    scheduleSaveQuantSettings()
  }
)
watch(backtestForm, scheduleSaveQuantSettings, { deep: true })
watch(gridForm, scheduleSaveQuantSettings, { deep: true })
watch(toolForm, scheduleSaveQuantSettings, { deep: true })
watch(updateForm, scheduleSaveQuantSettings, { deep: true })
watch(buyStrategyParams, scheduleSaveQuantSettings, { deep: true })
watch(sellStrategyParams, scheduleSaveQuantSettings, { deep: true })
watch(gridBuyParamLists, scheduleSaveQuantSettings, { deep: true })
watch(gridSellParamLists, scheduleSaveQuantSettings, { deep: true })
watch(adviceTemplates, scheduleSaveQuantSettings, { deep: true })
watch(
  () => selectedSymbols.value.join(','),
  () => {
    syncSelectedSymbols()
  }
)
const {
  totalPages,
  search,
  importSymbols,
  importAllSymbols,
  addSymbol,
  isSelected,
  toggleSymbol,
  removeSymbol,
  clearSymbols,
  selectPage,
  invertPage,
  syncSelectedSymbols,
  changePage,
  applyPageSize,
  runKlUpdate,
  runMarketCoverageUpdate,
  runFullAshareUpdate,
  savedPortfolios,
  selectedPortfolio,
  portfolioDraftName,
  portfolioSaveOpen,
  portfolioSaveError,
  refreshPortfolioIndex,
  openSaveSelection: saveSelection,
  cancelSaveSelection,
  confirmSaveSelection,
  loadPortfolio,
  deletePortfolio
} = usePrepareWorkflow({
  store,
  market,
  query,
  kind,
  pageSize,
  selectedSymbols,
  updateForm,
  backtestForm,
  gridForm,
  toolForm,
  syncMlSymbols: (text) => syncMlSymbols?.(text),
  splitSymbolInput,
  normalizeSymbolsInputForUi
})
const {
  toolOptionMode,
  applyGridToBacktest,
  applyGridRunToBacktest,
  applyGridNextSuggestions,
  applySymbolToBacktest,
  applySymbolToAnalysis,
  buildMlStockSelectPayload,
  runVerify,
  runBacktest,
  runStockSelect,
  runClosedLoop,
  runGridSearch,
  runTool
} = useQuantExecution({
  store,
  market,
  activeTab,
  flowRunning,
  strategyError,
  chartSymbol,
  predictionSignal,
  klineError,
  backtestForm,
  gridForm,
  toolForm,
  toolOptions,
  buyStrategyId,
  sellStrategyId,
  buyStrategyParams,
  sellStrategyParams,
  activeBuyStrategy,
  activeSellStrategy,
  buyStrategies,
  sellStrategies,
  gridBuyParamLists,
  gridSellParamLists,
  gridUseBacktestBase,
  gridExploreAllStrategies,
  gridJob,
  waitForJobDone,
  runTrackedJob,
  loadKlineChart,
  inferMarketBySymbol,
  inferMarketBySymbols,
  normalizeSymbolsInputForUi
})
const {
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
} = useTrendAnalysisDemo({
  market,
  store,
  inferMarketBySymbol,
  defaultSymbolForMarket,
  applySymbolToBacktest
})
const {
  mlRunning,
  mlFeatureForm,
  mlTrainForm,
  mlPredictForm,
  mlSelectForm,
  mlFeatureResult,
  mlTrainResult,
  mlPredictResult,
  mlSelectResult,
  refreshMlData,
  runMlFeatureBuild,
  runMlTrain,
  runMlPredict,
  runMlStockSelect,
  runMlPipeline,
  runMarketModelPipeline,
  useMlModel,
  promoteMlModel,
  loadModelTrainingParams,
  applyPredictionToBacktest,
  applyPredictionToPool,
  syncSymbols: syncMlSymbols
} = useMlWorkflow({
  store,
  market,
  waitForJobDone,
  inferMarketBySymbols,
  normalizeSymbolsInputForUi,
  onUsePrediction: applySymbolToBacktest,
  onAddPrediction: addSymbol,
  buildMlStockSelectPayload
})
const runInitStep = async (label, task) => {
  try {
    await task()
    return null
  } catch (err) {
    return `${label}: ${err?.message || String(err)}`
  }
}
onMounted(async () => {
  initError.value = ''
  refreshPortfolioIndex()
  window.addEventListener('resize', handleResize)
  await restoreQuantSettings()
  const initFailures = (
    await Promise.all([
      runInitStep('任务列表加载失败', () => store.fetchJobs()),
      runInitStep('策略列表加载失败', () => store.fetchStrategies()),
      runInitStep('ML 数据加载失败', () => refreshMlData()),
      runInitStep('标的列表加载失败', () =>
        store.searchSymbols({
          market: market.value,
          q: query.value,
          kind: kind.value,
          page: store.page,
          pageSize: store.pageSize
        })
      )
    ])
  ).filter(Boolean)
  if (initFailures.length) {
    initError.value = `部分初始化未完成：${initFailures.join('；')}`
  }
  syncMlSymbols(normalizeSymbolsInputForUi(backtestForm.symbols || ''))
  settingsReady.value = true
  scheduleSaveQuantSettings()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  clearSettingsSaveTimer()
  revokeTrendPreview()
  cleanupCharts()
})
</script>
