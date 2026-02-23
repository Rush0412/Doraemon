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
      :selected-symbols="selectedSymbols"
      :saved-portfolios="savedPortfolios"
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
      :load-portfolio="loadPortfolio"
      :delete-portfolio="deletePortfolio"
      :remove-symbol="removeSymbol"
      :change-page="changePage"
      :apply-page-size="applyPageSize"
      :run-kl-update="runKlUpdate"
    />


    
    <StrategyPanel
      :active="activeTab === 'strategy'"
      :backtest-form="backtestForm"
      :grid-form="gridForm"
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
      :analysis-overlay-enabled="analysisOverlayEnabled"
      :set-analysis-overlay-enabled="setAnalysisOverlayEnabled"
      :run-tool="runTool"
      :sync-analysis-to-chart="syncAnalysisToChart"
      :actions-busy="actionsBusy"
    />


    <JobsPanel
      :active="activeTab === 'jobs'"
      :store="store"
      :format-time="formatTime"
      :brief="brief"
      :export-url="exportUrl"
      :select-job="selectJob"
      :remove-job="removeJob"
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
import JobsPanel from './quant/JobsPanel.vue'
import { useBacktestCharts } from './quant/composables/useBacktestCharts'
import { useOperationSuggestion } from './quant/composables/useOperationSuggestion'
import { useQuantSettings } from './quant/composables/useQuantSettings'
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
  buildGridParamPayload,
  parseStringList,
  resetGridParamLists,
  resetStrategyParams
} from './quant/utils/strategyGrid'
import { useQuantStore } from '../stores/quantStore'

const store = useQuantStore()
const tabs = [
  {
    id: 'prepare',
    step: '01',
    title: '数据准备',
    subtitle: '标的与更新',
    hint: '搜索标的、维护组合，并先完成 K 线更新。'
  },
  {
    id: 'strategy',
    step: '02',
    title: '回测与寻优',
    subtitle: '验证策略',
    hint: '执行历史回测、参数交叉验证，并将最优组合应用到回测。'
  },
  {
    id: 'tools',
    step: '03',
    title: '量化分析',
    subtitle: '信号工具',
    hint: '运行支撑阻力、跳空、趋势速度等工具，生成交易信号。'
  },
  {
    id: 'jobs',
    step: '04',
    title: '任务中心',
    subtitle: '状态与导出',
    hint: '查看任务状态、结果明细并导出。'
  }
]
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
const savedPortfolios = ref([])
const selectedPortfolio = ref('')
const chartSymbol = ref('')
const orderFilter = ref('all')
const selectedOrderKey = ref('')
const selectedOrder = ref(null)
const showStopLines = ref(true)
const analysisOverlayEnabled = ref(true)
const gridUseBacktestBase = ref(true)
const gridExploreAllStrategies = ref(true)
const flowRunning = ref(false)
const orderPage = ref(1)
const orderPageSize = ref(20)

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
  symbols: ''
})

const backtestForm = reactive({
  market: market.value,
  symbols: '',
  cash: 1000000,
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
  symbol_eval_limit: 120,
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
  () => store.jobsLoading || store.activeJobLoading || store.symbolsLoading || flowRunning.value
)

const buyStrategies = computed(() => store.strategies?.buy || [])
const sellStrategies = computed(() => store.strategies?.sell || [])
const activeBuyStrategy = computed(() =>
  buyStrategies.value.find((item) => item.id === buyStrategyId.value) || null
)
const activeSellStrategy = computed(() =>
  sellStrategies.value.find((item) => item.id === sellStrategyId.value) || null
)

const defaultSymbolForMarket = (value) => {
  if (value === 'SH') return '600036'
  if (value === 'SZ') return '000001'
  if (value === '300') return '300750'
  if (value === 'US') return 'AAPL'
  if (value === 'HK') return '00700'
  return '600036'
}

if (!backtestForm.symbols) backtestForm.symbols = defaultSymbolForMarket(market.value)
if (!gridForm.symbols) gridForm.symbols = defaultSymbolForMarket(market.value)
if (!toolForm.symbols) toolForm.symbols = defaultSymbolForMarket(market.value)

watch(market, (val) => {
  updateForm.market = val
  backtestForm.market = val
  gridForm.market = val
  toolForm.market = val
  if (!backtestForm.symbols) backtestForm.symbols = defaultSymbolForMarket(val)
  if (!gridForm.symbols) gridForm.symbols = defaultSymbolForMarket(val)
  if (!toolForm.symbols) toolForm.symbols = defaultSymbolForMarket(val)
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

const jobStats = computed(() => {
  const stats = { total: 0, running: 0, succeeded: 0, failed: 0 }
  stats.total = store.jobs.length
  for (const job of store.jobs) {
    if (job.status === 'running') stats.running += 1
    if (job.status === 'succeeded') stats.succeeded += 1
    if (job.status === 'failed') stats.failed += 1
  }
  return stats
})

const lastUpdateSummary = computed(() => {
  const job = store.jobs.find((item) => item.type === 'kl_update' && item.status === 'succeeded')
  return job?.result || null
})

const latestJobByType = (type) => {
  if (!type) return null
  const jobs = store.jobs.filter((job) => job.type === type)
  if (!jobs.length) return null
  return jobs.reduce((latest, job) => (job.id > latest.id ? job : latest), jobs[0])
}

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
  if (store.activeJob && store.activeJob.type === 'analysis') return store.activeJob
  return latestJobByType('analysis')
})

const analysisResult = computed(() => analysisJob.value?.result || null)

const gridSummaryText = computed(() =>
  gridSummary.value ? JSON.stringify(gridSummary.value, null, 2) : ''
)

const analysisText = computed(() =>
  analysisResult.value ? JSON.stringify(analysisResult.value, null, 2) : ''
)

const { operationSuggestion } = useOperationSuggestion({
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
  gridExploreAllStrategies
})

const applyGridCandidateToBacktest = async (candidate) => {
  if (!candidate) return
  if (candidate.buy_strategy) {
    buyStrategyId.value = candidate.buy_strategy
  }
  if (candidate.sell_strategy) {
    sellStrategyId.value = candidate.sell_strategy
  }
  await nextTick()
  if (candidate.buy_params) {
    resetStrategyParams(activeBuyStrategy.value, buyStrategyParams)
    Object.assign(buyStrategyParams, candidate.buy_params)
    if (candidate.buy_params.xd !== undefined) {
      backtestForm.buy_xd = Number(candidate.buy_params.xd) || backtestForm.buy_xd
    }
  }
  if (candidate.sell_params) {
    resetStrategyParams(activeSellStrategy.value, sellStrategyParams)
    Object.assign(sellStrategyParams, candidate.sell_params)
    if (candidate.sell_params.stop_loss_n !== undefined) {
      const val = Number(candidate.sell_params.stop_loss_n)
      if (Number.isFinite(val)) backtestForm.stop_loss_n = val
    }
    if (candidate.sell_params.stop_win_n !== undefined) {
      const val = Number(candidate.sell_params.stop_win_n)
      if (Number.isFinite(val)) backtestForm.stop_win_n = val
    }
  }
  if (candidate.buy_xd !== undefined) {
    const val = Number(candidate.buy_xd)
    if (Number.isFinite(val) && val > 0) backtestForm.buy_xd = val
  }
  if (candidate.stop_loss_n !== undefined) {
    const val = Number(candidate.stop_loss_n)
    if (Number.isFinite(val)) backtestForm.stop_loss_n = val
  }
  if (candidate.stop_win_n !== undefined) {
    const val = Number(candidate.stop_win_n)
    if (Number.isFinite(val)) backtestForm.stop_win_n = val
  }
  if (Array.isArray(candidate.symbols) && candidate.symbols.length) {
    backtestForm.symbols = normalizeSymbolsInputForUi(candidate.symbols.join(', '))
  }
  if (typeof candidate.symbol === 'string' && candidate.symbol.trim()) {
    backtestForm.symbols = normalizeSymbolsInputForUi(candidate.symbol.trim())
    chartSymbol.value = candidate.symbol.trim()
  }
  if (candidate.market) backtestForm.market = candidate.market
  activeTab.value = 'strategy'
}

const applyGridToBacktest = async () => {
  await applyGridCandidateToBacktest(gridSummary.value)
}

const applyGridRunToBacktest = async (run) => {
  await applyGridCandidateToBacktest(run)
}

const applyGridNextSuggestions = () => {
  const next = gridNextParamSuggestions.value
  if (!next || typeof next !== 'object') return
  if (next.buy_params_grid && typeof next.buy_params_grid === 'object') {
    Object.entries(next.buy_params_grid).forEach(([key, values]) => {
      if (!Array.isArray(values)) return
      gridBuyParamLists[key] = values.join(', ')
    })
  }
  if (next.sell_params_grid && typeof next.sell_params_grid === 'object') {
    Object.entries(next.sell_params_grid).forEach(([key, values]) => {
      if (!Array.isArray(values)) return
      gridSellParamLists[key] = values.join(', ')
    })
  }
}

const applySymbolToBacktest = (symbol) => {
  if (!symbol) return
  const text = String(symbol).trim()
  if (!text) return
  backtestForm.symbols = normalizeSymbolsInputForUi(text)
  backtestForm.market = inferMarketBySymbol(text, market.value || 'SH')
  chartSymbol.value = text
  activeTab.value = 'strategy'
}

const applySymbolToAnalysis = async (symbol) => {
  if (!symbol) return
  const text = String(symbol).trim()
  if (!text) return
  toolForm.symbols = normalizeSymbolsInputForUi(text)
  toolForm.market = inferMarketBySymbol(text, market.value || 'SH')
  activeTab.value = 'tools'
  await runTool()
}

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
  chartSymbol,
  selectedOrderKey,
  selectedOrder,
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
    gridExploreAllStrategies.value
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

const activeParamsText = computed(() =>
  store.activeJob?.params ? JSON.stringify(store.activeJob.params, null, 2) : ''
)
const activeResultText = computed(() =>
  store.activeJob?.result ? JSON.stringify(store.activeJob.result, null, 2) : ''
)
const activeErrorText = computed(() =>
  store.activeJob?.error ? String(store.activeJob.error) : ''
)

const toolOptionMode = computed(() => {
  if (toolForm.tool === 'support_resistance') return 'support'
  if (toolForm.tool === 'jump_gap') return 'jump'
  if (toolForm.tool === 'trend_speed') return 'trend'
  if (toolForm.tool === 'shift_distance') return 'shift'
  if (toolForm.tool === 'regress' || toolForm.tool === 'price_channel') return 'regress'
  if (toolForm.tool === 'correlation') return 'corr'
  if (toolForm.tool === 'distance') return 'distance'
  return 'base'
})

const totalPages = computed(() => Math.max(1, Math.ceil(store.total / store.pageSize)))

const formatTime = (v) => {
  if (!v) return '-'
  try {
    const d = typeof v === 'string' ? new Date(v) : new Date(String(v))
    if (Number.isNaN(d.getTime())) return String(v)
    return d.toLocaleString()
  } catch {
    return String(v)
  }
}

const brief = (v) => {
  if (!v) return ''
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 60 ? `${s.slice(0, 57)}...` : s
}

const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(digits)
}

const search = async () => {
  await store.searchSymbols({
    market: market.value,
    q: query.value,
    kind: kind.value,
    page: 1,
    pageSize: pageSize.value
  })
}

const importSymbols = async () => {
  const data = await store.importSymbols(market.value)
  if (data) {
    await store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page: 1,
      pageSize: pageSize.value
    })
  }
}

const importAllSymbols = async () => {
  const data = await store.importSymbols('CN')
  if (data) {
    await store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page: 1,
      pageSize: pageSize.value
    })
  }
}

const refreshJobs = async () => {
  await store.fetchJobs()
}

const selectJob = async (id) => {
  await store.fetchJob(id)
}

const removeJob = async (job) => {
  if (job.status === 'running') return
  await store.deleteJob(job.id)
}

const exportUrl = (id, format, section) => {
  const params = new URLSearchParams()
  if (format) params.set('format', format)
  if (section) params.set('section', section)
  const qs = params.toString()
  return `/api/v1/jobs/${encodeURIComponent(String(id))}/export${qs ? `?${qs}` : ''}`
}

const addSymbol = (symbol) => {
  if (!symbol || selectedSymbols.value.includes(symbol)) return
  selectedSymbols.value = [...selectedSymbols.value, symbol]
  syncSelectedSymbols()
}

const isSelected = (symbol) => selectedSymbols.value.includes(symbol)

const toggleSymbol = (symbol) => {
  if (isSelected(symbol)) {
    removeSymbol(symbol)
    return
  }
  addSymbol(symbol)
}

const removeSymbol = (symbol) => {
  selectedSymbols.value = selectedSymbols.value.filter((item) => item !== symbol)
  syncSelectedSymbols()
}

const clearSymbols = () => {
  selectedSymbols.value = []
  syncSelectedSymbols()
}

const selectPage = () => {
  const pageSymbols = store.symbols.map((item) => item.symbol)
  const merged = new Set([...selectedSymbols.value, ...pageSymbols])
  selectedSymbols.value = Array.from(merged)
  syncSelectedSymbols()
}

const invertPage = () => {
  const pageSymbols = new Set(store.symbols.map((item) => item.symbol))
  const next = selectedSymbols.value.filter((symbol) => !pageSymbols.has(symbol))
  for (const symbol of pageSymbols) {
    if (!selectedSymbols.value.includes(symbol)) {
      next.push(symbol)
    }
  }
  selectedSymbols.value = next
  syncSelectedSymbols()
}

const saveSelection = () => {
  const name = window.prompt('淇濆瓨缁勫悎鍚嶇О')
  if (!name) return
  const trimmed = name.trim()
  if (!trimmed) return
  const payload = { name: trimmed, symbols: selectedSymbols.value }
  localStorage.setItem(`doraemon_portfolio_${trimmed}`, JSON.stringify(payload))
  const indexKey = 'doraemon_portfolios'
  const list = JSON.parse(localStorage.getItem(indexKey) || '[]')
  if (!list.includes(trimmed)) list.push(trimmed)
  localStorage.setItem(indexKey, JSON.stringify(list))
  savedPortfolios.value = list
  selectedPortfolio.value = trimmed
}

const loadPortfolio = () => {
  if (!selectedPortfolio.value) return
  const raw = localStorage.getItem(`doraemon_portfolio_${selectedPortfolio.value}`)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    selectedSymbols.value = Array.isArray(parsed.symbols) ? parsed.symbols : []
    syncSelectedSymbols()
  } catch {
    // ignore malformed payload
  }
}

const deletePortfolio = () => {
  if (!selectedPortfolio.value) return
  localStorage.removeItem(`doraemon_portfolio_${selectedPortfolio.value}`)
  const indexKey = 'doraemon_portfolios'
  const list = JSON.parse(localStorage.getItem(indexKey) || '[]').filter(
    (name) => name !== selectedPortfolio.value
  )
  localStorage.setItem(indexKey, JSON.stringify(list))
  savedPortfolios.value = list
  selectedPortfolio.value = ''
}

const syncSelectedSymbols = () => {
  const text = normalizeSymbolsInputForUi(selectedSymbols.value.join(', '))
  backtestForm.symbols = text
  gridForm.symbols = text
  toolForm.symbols = text
  updateForm.symbols = text
}

const changePage = async (nextPage) => {
  if (nextPage < 1 || nextPage > totalPages.value) return
  await store.searchSymbols({
    market: market.value,
    q: query.value,
    kind: kind.value,
    page: nextPage,
    pageSize: pageSize.value
  })
}

const applyPageSize = async () => {
  await store.searchSymbols({
    market: market.value,
    q: query.value,
    kind: kind.value,
    page: 1,
    pageSize: pageSize.value
  })
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const waitForJobDone = async (jobId, timeoutMs = 20 * 60 * 1000, pollMs = 1200) => {
  const startedAt = Date.now()
  while (Date.now() - startedAt <= timeoutMs) {
    await store.fetchJob(jobId)
    const current = store.activeJob
    if (current?.id === jobId && (current.status === 'succeeded' || current.status === 'failed')) {
      await store.fetchJobs()
      if (current.status === 'failed') {
        throw new Error(current.error || `任务 ${jobId} 执行失败`)
      }
      return current
    }
    await sleep(pollMs)
  }
  throw new Error(`任务 ${jobId} 超时未完成`)
}

const buildBacktestPayload = () => {
  const effectiveMarket = inferMarketBySymbols(backtestForm.symbols, backtestForm.market)
  backtestForm.market = effectiveMarket
  return {
    market: effectiveMarket,
    symbols: backtestForm.symbols,
    n_folds: backtestForm.n_folds,
    start: backtestForm.start || undefined,
    end: backtestForm.end || undefined,
    cash: backtestForm.cash,
    buy_xd: backtestForm.buy_xd,
    stop_loss_n: backtestForm.stop_loss_n,
    stop_win_n: backtestForm.stop_win_n,
    buy_strategy: buyStrategyId.value,
    buy_params: { ...buyStrategyParams },
    sell_strategy: sellStrategyId.value,
    sell_params: { ...sellStrategyParams },
    orders_preview_limit: 8000,
    actions_preview_limit: 8000
  }
}

const buildStockSelectPayload = () => {
  const rawSymbols = String(backtestForm.symbols || '').trim()
  const fallbackCandidateLimit = Math.max(Number(gridForm.symbol_eval_limit || 120), Number(gridForm.symbol_top_n || 10) * 3)
  const effectiveMarket = inferMarketBySymbols(rawSymbols, backtestForm.market)
  backtestForm.market = effectiveMarket
  return {
    market: effectiveMarket,
    symbols: rawSymbols || undefined,
    all_symbols: !rawSymbols,
    candidate_limit: fallbackCandidateLimit,
    symbol_eval_limit: Number(gridForm.symbol_eval_limit || 120),
    symbol_top_n: Number(gridForm.symbol_top_n || 10),
    min_kline_rows: 120,
    n_folds: backtestForm.n_folds,
    start: backtestForm.start || undefined,
    end: backtestForm.end || undefined,
    cash: backtestForm.cash,
    buy_xd: backtestForm.buy_xd,
    stop_loss_n: backtestForm.stop_loss_n,
    stop_win_n: backtestForm.stop_win_n,
    buy_strategy: buyStrategyId.value,
    buy_params: { ...buyStrategyParams },
    sell_strategy: sellStrategyId.value,
    sell_params: { ...sellStrategyParams }
  }
}

const runVerify = async () => {
  try {
    const job = await store.startVerify()
    await waitForJobDone(job.id, 2 * 60 * 1000)
  } catch (err) {
    klineError.value = err?.message || String(err)
    return null
  }
}

const runKlUpdate = async () => {
  try {
    const symbols = selectedSymbols.value.length ? selectedSymbols.value.join(',') : ''
    const job = await store.startKlUpdate({
      market: updateForm.market,
      n_folds: updateForm.n_folds,
      start: updateForm.start || undefined,
      end: updateForm.end || undefined,
      how: updateForm.how,
      n_jobs: updateForm.n_jobs,
      symbols: symbols || undefined,
      all: !symbols
    })
    await waitForJobDone(job.id, 30 * 60 * 1000)
  } catch (err) {
    klineError.value = err?.message || String(err)
    return null
  }
}

const runBacktest = async () => {
  try {
    klineError.value = ''
    const job = await store.startBacktest(buildBacktestPayload())
    return await waitForJobDone(job.id, 40 * 60 * 1000)
  } catch (err) {
    klineError.value = err?.message || String(err)
    return null
  }
}

const runStockSelect = async () => {
  try {
    klineError.value = ''
    const job = await store.startStockSelect(buildStockSelectPayload())
    return await waitForJobDone(job.id, 30 * 60 * 1000)
  } catch (err) {
    klineError.value = err?.message || String(err)
    return null
  }
}

const _normalizePayload = (value) => {
  if (Array.isArray(value)) return value.map((item) => _normalizePayload(item))
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((acc, key) => {
        const v = value[key]
        if (v !== undefined) acc[key] = _normalizePayload(v)
        return acc
      }, {})
  }
  return value
}

const _samePayload = (a, b) => JSON.stringify(_normalizePayload(a || {})) === JSON.stringify(_normalizePayload(b || {}))

const _parseJobTime = (job) => {
  const v = job?.updated_at || job?.finished_at || job?.created_at
  if (!v) return 0
  const ts = new Date(v).getTime()
  return Number.isFinite(ts) ? ts : 0
}

const _findReusableSucceededJob = (type, payload, maxAgeMs = 15 * 60 * 1000) => {
  const now = Date.now()
  const rows = Array.isArray(store.jobs) ? [...store.jobs] : []
  rows.sort((a, b) => _parseJobTime(b) - _parseJobTime(a))
  return (
    rows.find((job) => {
      if (!job || job.type !== type || job.status !== 'succeeded') return false
      const ageMs = now - _parseJobTime(job)
      if (!Number.isFinite(ageMs) || ageMs < 0 || ageMs > maxAgeMs) return false
      return _samePayload(job.params, payload)
    }) || null
  )
}

const runClosedLoop = async () => {
  flowRunning.value = true
  klineError.value = ''
  try {
    await store.fetchJobs(120)
    const selectPayload = buildStockSelectPayload()
    const reusableSelect = _findReusableSucceededJob('stock_select', selectPayload)
    let selectDone = null
    if (reusableSelect) {
      await store.fetchJob(reusableSelect.id)
      selectDone = store.activeJob
    } else {
      const selectQueued = await store.startStockSelect(selectPayload)
      selectDone = await waitForJobDone(selectQueued.id)
    }
    const selectResult = selectDone?.result || {}
    const topSymbols = Array.isArray(selectResult.top_symbols)
      ? selectResult.top_symbols.map((item) => String(item.symbol || '').trim()).filter(Boolean)
      : []
    if (!topSymbols.length) {
      throw new Error('独立选股未返回可回测标的，请调整范围后重试。')
    }

    const picked = topSymbols.slice(0, Math.max(1, Number(gridForm.symbol_top_n || 10)))
    backtestForm.symbols = normalizeSymbolsInputForUi(picked.join(', '))
    chartSymbol.value = picked[0]

    const backtestPayload = buildBacktestPayload()
    const reusableBacktest = _findReusableSucceededJob('backtest', backtestPayload)
    if (reusableBacktest) {
      await store.fetchJob(reusableBacktest.id)
    } else {
      const backtestQueued = await store.startBacktest(backtestPayload)
      await waitForJobDone(backtestQueued.id)
    }

    toolForm.market = backtestForm.market
    toolForm.tool = 'support_resistance'
    toolForm.symbols = normalizeSymbolsInputForUi(picked[0])
    toolForm.start = backtestForm.start || ''
    toolForm.end = backtestForm.end || ''
    const analysisPayload = {
      market: toolForm.market,
      tool: toolForm.tool,
      symbols: toolForm.symbols,
      n_folds: toolForm.n_folds,
      start: toolForm.start || undefined,
      end: toolForm.end || undefined,
      limit: toolForm.limit,
      options: buildToolOptions()
    }
    const reusableAnalysis = _findReusableSucceededJob('analysis', analysisPayload)
    if (reusableAnalysis) {
      await store.fetchJob(reusableAnalysis.id)
    } else {
      const analysisQueued = await store.startQuantTool(analysisPayload)
      await waitForJobDone(analysisQueued.id)
    }

    activeTab.value = 'strategy'
    await nextTick()
    await loadKlineChart()
  } catch (err) {
    klineError.value = err?.message || String(err)
  } finally {
    flowRunning.value = false
  }
}

const runGridSearch = async () => {
  try {
    klineError.value = ''
    const buyGrid = buildGridParamPayload(activeBuyStrategy.value, gridBuyParamLists)
    const sellGrid = buildGridParamPayload(activeSellStrategy.value, gridSellParamLists)
    const rankingWeights = {
      profit: Number(gridForm.ranking_weights?.profit ?? 1),
      win_rate: Number(gridForm.ranking_weights?.win_rate ?? 1),
      sharpe: Number(gridForm.ranking_weights?.sharpe ?? 1),
      annual_return: Number(gridForm.ranking_weights?.annual_return ?? 1),
      drawdown: Number(gridForm.ranking_weights?.drawdown ?? 1)
    }
    const customBuyList = parseStringList(gridForm.buy_strategies)
    const customSellList = parseStringList(gridForm.sell_strategies)
    const buyStrategyList = gridExploreAllStrategies.value
      ? buyStrategies.value.map((item) => item.id).filter(Boolean)
      : customBuyList
    const sellStrategyList = gridExploreAllStrategies.value
      ? sellStrategies.value.map((item) => item.id).filter(Boolean)
      : customSellList
    const baseSymbols = gridUseBacktestBase.value ? backtestForm.symbols : gridForm.symbols
    const baseMarketRaw = gridUseBacktestBase.value ? backtestForm.market : gridForm.market
    const baseMarket = inferMarketBySymbols(baseSymbols, baseMarketRaw)
    if (gridUseBacktestBase.value) backtestForm.market = baseMarket
    else gridForm.market = baseMarket
    const baseCash = gridUseBacktestBase.value ? backtestForm.cash : gridForm.cash
    const baseStart = gridUseBacktestBase.value ? backtestForm.start : gridForm.start
    const baseEnd = gridUseBacktestBase.value ? backtestForm.end : gridForm.end
    const baseNFolds = gridUseBacktestBase.value ? backtestForm.n_folds : gridForm.n_folds
    const normalizedMaxRuns = Math.max(1, Number(gridForm.max_runs || 150))
    gridForm.max_runs = normalizedMaxRuns
    const job = await store.startGridSearch({
      market: baseMarket,
      symbols: baseSymbols,
      n_folds: baseNFolds,
      start: baseStart || undefined,
      end: baseEnd || undefined,
      cash: baseCash,
      buy_strategy: buyStrategyId.value,
      sell_strategy: sellStrategyId.value,
      buy_strategies: buyStrategyList.length ? buyStrategyList : undefined,
      sell_strategies: sellStrategyList.length ? sellStrategyList : undefined,
      buy_params_grid: buyGrid,
      sell_params_grid: sellGrid,
      validation_mode: gridForm.validation_mode,
      train_ratio: gridForm.train_ratio,
      walk_forward_days: gridForm.walk_forward_days,
      walk_forward_step_days: gridForm.walk_forward_step_days,
      ranking_metric: gridForm.ranking_metric,
      ranking_weights: rankingWeights,
      symbol_top_n: gridForm.symbol_top_n,
      symbol_eval_limit: gridForm.symbol_eval_limit,
      max_runs: normalizedMaxRuns
    })
    await waitForJobDone(job.id, 60 * 60 * 1000)
  } catch (err) {
    klineError.value = err?.message || String(err)
    return null
  }
}

const buildToolOptions = () => {
  const opts = {}
  if (toolForm.tool === 'support_resistance') opts.only_last = toolOptions.only_last
  if (toolForm.tool === 'jump_gap') {
    opts.mode = toolOptions.mode
    opts.jump_diff_factor = toolOptions.jump_diff_factor
    opts.power_threshold = toolOptions.power_threshold
    opts.weight = [toolOptions.weight_a, toolOptions.weight_b]
  }
  if (toolForm.tool === 'trend_speed') {
    opts.benchmark = toolOptions.benchmark
    opts.resample = toolOptions.resample
    opts.speed_key = toolOptions.speed_key
  }
  if (toolForm.tool === 'shift_distance') {
    opts.step_x = toolOptions.step_x
    opts.mode = toolOptions.shift_mode
  }
  if (toolForm.tool === 'regress' || toolForm.tool === 'price_channel') {
    opts.mode = toolOptions.regress_mode
  }
  if (toolForm.tool === 'correlation') {
    opts.corr_type = toolOptions.corr_type
    opts.field = toolOptions.field
  }
  if (toolForm.tool === 'distance') {
    opts.distance_type = toolOptions.distance_type
    opts.field = toolOptions.field
  }
  return opts
}

const runTool = async () => {
  try {
    const effectiveMarket = inferMarketBySymbols(toolForm.symbols, toolForm.market)
    toolForm.market = effectiveMarket
    const job = await store.startQuantTool({
      market: effectiveMarket,
      tool: toolForm.tool,
      symbols: toolForm.symbols,
      n_folds: toolForm.n_folds,
      start: toolForm.start || undefined,
      end: toolForm.end || undefined,
      limit: toolForm.limit,
      options: buildToolOptions()
    })
    await waitForJobDone(job.id, 20 * 60 * 1000)
  } catch (err) {
    klineError.value = err?.message || String(err)
    return null
  }
}

onMounted(async () => {
  savedPortfolios.value = JSON.parse(localStorage.getItem('doraemon_portfolios') || '[]')
  window.addEventListener('resize', handleResize)
  await Promise.all([
    store.fetchJobs(),
    store.fetchStrategies(),
    store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page: store.page,
      pageSize: store.pageSize
    })
  ])
  await restoreQuantSettings()
  settingsReady.value = true
  scheduleSaveQuantSettings()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  clearSettingsSaveTimer()
  cleanupCharts()
})
</script>


