<template>
  <div class="quant-shell">
    <section class="hero">
      <div class="hero-head">
        <div>
          <p class="eyebrow">Doraemon Quant Suite</p>
          <h1>量化交易指挥台</h1>
          <p class="hero-sub">
            数据更新、策略回测、参数寻优、量化分析与操作建议的一体化闭环。
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
import { createChart } from 'lightweight-charts'
import PreparePanel from './quant/PreparePanel.vue'
import StrategyPanel from './quant/StrategyPanel.vue'
import AnalysisPanel from './quant/AnalysisPanel.vue'
import JobsPanel from './quant/JobsPanel.vue'
import { api } from '../services/api'
import { useQuantStore } from '../stores/quantStore'

const store = useQuantStore()
const tabs = [
  {
    id: 'prepare',
    step: '01',
    title: '数据准备',
    subtitle: '标的与更新',
    hint: '搜索标的、维护组合，并先完成K线更新。'
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
    hint: '运行支撑阻力、跳空、趋势速度等工具生成交易信号。'
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
const setKlineContainer = (el) => {
  klineContainer.value = el
}
const setEquityContainer = (el) => {
  equityContainer.value = el
}

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
  max_runs: 30
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

const SETTINGS_KEY = 'doraemon_quant_settings_v1'
const settingsReady = ref(false)
let settingsSaveTimer = null

const plainObject = (value) => {
  try {
    return JSON.parse(JSON.stringify(value ?? {}))
  } catch {
    return {}
  }
}

const saveQuantSettings = () => {
  if (!settingsReady.value) return
  const snapshot = {
    market: market.value,
    query: query.value,
    kind: kind.value,
    pageSize: pageSize.value,
    backtestForm: plainObject(backtestForm),
    gridForm: plainObject(gridForm),
    toolForm: plainObject(toolForm),
    updateForm: plainObject(updateForm),
    buyStrategyId: buyStrategyId.value,
    sellStrategyId: sellStrategyId.value,
    buyStrategyParams: plainObject(buyStrategyParams),
    sellStrategyParams: plainObject(sellStrategyParams),
    gridBuyParamLists: plainObject(gridBuyParamLists),
    gridSellParamLists: plainObject(gridSellParamLists),
    gridUseBacktestBase: !!gridUseBacktestBase.value,
    gridExploreAllStrategies: !!gridExploreAllStrategies.value,
    adviceProfile: adviceProfile.value,
    adviceTemplates: plainObject(adviceTemplates),
  }
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(snapshot))
  } catch {
    // ignore storage write error
  }
}

const scheduleSaveQuantSettings = () => {
  if (!settingsReady.value) return
  if (settingsSaveTimer) clearTimeout(settingsSaveTimer)
  settingsSaveTimer = setTimeout(() => {
    saveQuantSettings()
    settingsSaveTimer = null
  }, 180)
}

const restoreAdviceTemplates = (payload) => {
  if (!payload || typeof payload !== 'object') return
  ;['conservative', 'balanced', 'aggressive'].forEach((key) => {
    const source = payload[key]
    const target = adviceTemplates[key]
    if (!source || !target) return
    if (typeof source.label === 'string' && source.label.trim()) target.label = source.label
    if (source.position && typeof source.position === 'object') {
      Object.assign(target.position, source.position)
    }
    if (source.entry && typeof source.entry === 'object') {
      Object.assign(target.entry, source.entry)
    }
    if (source.takeProfit && typeof source.takeProfit === 'object') {
      Object.assign(target.takeProfit, source.takeProfit)
    }
    if (source.trailStopPct !== undefined) {
      target.trailStopPct = Number(source.trailStopPct)
    }
  })
}

const restoreQuantSettings = async () => {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (!raw) return
    const snapshot = JSON.parse(raw)
    if (!snapshot || typeof snapshot !== 'object') return
    if (typeof snapshot.market === 'string' && snapshot.market.trim()) market.value = snapshot.market
    if (typeof snapshot.query === 'string') query.value = snapshot.query
    if (typeof snapshot.kind === 'string') kind.value = snapshot.kind
    if (Number.isFinite(Number(snapshot.pageSize)) && Number(snapshot.pageSize) > 0) {
      pageSize.value = Number(snapshot.pageSize)
    }
    if (snapshot.updateForm && typeof snapshot.updateForm === 'object') Object.assign(updateForm, snapshot.updateForm)
    if (snapshot.backtestForm && typeof snapshot.backtestForm === 'object') Object.assign(backtestForm, snapshot.backtestForm)
    if (snapshot.gridForm && typeof snapshot.gridForm === 'object') Object.assign(gridForm, snapshot.gridForm)
    if (!gridForm.ranking_weights || typeof gridForm.ranking_weights !== 'object') {
      gridForm.ranking_weights = {}
    }
    gridForm.ranking_weights = {
      profit: Number(gridForm.ranking_weights.profit ?? 1),
      win_rate: Number(gridForm.ranking_weights.win_rate ?? 1),
      sharpe: Number(gridForm.ranking_weights.sharpe ?? 1),
      annual_return: Number(gridForm.ranking_weights.annual_return ?? 1),
      drawdown: Number(gridForm.ranking_weights.drawdown ?? 1)
    }
    if (snapshot.toolForm && typeof snapshot.toolForm === 'object') Object.assign(toolForm, snapshot.toolForm)
    if (typeof snapshot.buyStrategyId === 'string' && snapshot.buyStrategyId.trim()) {
      buyStrategyId.value = snapshot.buyStrategyId
    }
    if (typeof snapshot.sellStrategyId === 'string' && snapshot.sellStrategyId.trim()) {
      sellStrategyId.value = snapshot.sellStrategyId
    }
    if (snapshot.gridUseBacktestBase !== undefined) {
      gridUseBacktestBase.value = !!snapshot.gridUseBacktestBase
    }
    if (snapshot.gridExploreAllStrategies !== undefined) {
      gridExploreAllStrategies.value = !!snapshot.gridExploreAllStrategies
    }
    if (typeof snapshot.adviceProfile === 'string' && snapshot.adviceProfile.trim()) {
      adviceProfile.value = snapshot.adviceProfile
    }
    restoreAdviceTemplates(snapshot.adviceTemplates)
    await nextTick()
    if (snapshot.buyStrategyParams && typeof snapshot.buyStrategyParams === 'object') {
      Object.assign(buyStrategyParams, snapshot.buyStrategyParams)
    }
    if (snapshot.sellStrategyParams && typeof snapshot.sellStrategyParams === 'object') {
      Object.assign(sellStrategyParams, snapshot.sellStrategyParams)
    }
    if (snapshot.gridBuyParamLists && typeof snapshot.gridBuyParamLists === 'object') {
      Object.assign(gridBuyParamLists, snapshot.gridBuyParamLists)
    }
    if (snapshot.gridSellParamLists && typeof snapshot.gridSellParamLists === 'object') {
      Object.assign(gridSellParamLists, snapshot.gridSellParamLists)
    }
  } catch {
    // ignore malformed storage
  }
}

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
  if (value === 'SH') return 'sh600036'
  if (value === 'SZ') return 'sz000001'
  if (value === '300') return 'sz300750'
  if (value === 'US') return 'usAAPL'
  if (value === 'HK') return 'hk00700'
  return 'sh600036'
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

watch(buyStrategies, (list) => {
  if (!list.length) return
  if (!list.find((item) => item.id === buyStrategyId.value)) {
    buyStrategyId.value = list[0].id
  }
  applyStrategyDefaults(activeBuyStrategy.value, buyStrategyParams)
  applyGridDefaults(activeBuyStrategy.value, gridBuyParamLists)
})

watch(sellStrategies, (list) => {
  if (!list.length) return
  if (!list.find((item) => item.id === sellStrategyId.value)) {
    sellStrategyId.value = list[0].id
  }
  applyStrategyDefaults(activeSellStrategy.value, sellStrategyParams)
  applyGridDefaults(activeSellStrategy.value, gridSellParamLists)
})

watch(buyStrategyId, () => {
  resetStrategyParams(activeBuyStrategy.value, buyStrategyParams)
  resetGridParamLists(activeBuyStrategy.value, gridBuyParamLists)
})

watch(sellStrategyId, () => {
  resetStrategyParams(activeSellStrategy.value, sellStrategyParams)
  resetGridParamLists(activeSellStrategy.value, gridSellParamLists)
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

const normalizeSymbol = (value) => {
  const raw = String(value || '').trim().toLowerCase()
  if (!raw) return ''
  return raw.replace(/[^a-z0-9]/g, '')
}

const symbolEquals = (left, right) => {
  const a = normalizeSymbol(left)
  const b = normalizeSymbol(right)
  if (!a || !b) return false
  if (a === b) return true
  const stripCnPrefix = (text) => (/^[a-z]{2}\d{5,}$/.test(text) ? text.slice(2) : text)
  const aCode = stripCnPrefix(a)
  const bCode = stripCnPrefix(b)
  return !!aCode && !!bCode && aCode === bCode
}

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
  if (typeof raw === 'string') {
    return raw
      .split(/[\s,;]+/)
      .map((item) => item.trim())
      .filter(Boolean)
  }
  return []
})

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
const hoverInfo = ref(null)

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

const analysisResult = computed(() => {
  if (!store.activeJob || store.activeJob.type !== 'analysis') return null
  return store.activeJob.result || null
})

const gridSummaryText = computed(() =>
  gridSummary.value ? JSON.stringify(gridSummary.value, null, 2) : ''
)

const analysisText = computed(() =>
  analysisResult.value ? JSON.stringify(analysisResult.value, null, 2) : ''
)

const adviceProfile = ref('balanced')
const adviceTemplates = reactive({
  conservative: {
    label: '稳健',
    position: {
      buyHigh: 0.45,
      buyMid: 0.3,
      buyWatchHigh: 0.28,
      buyWatchMid: 0.18,
      reduce: 0.15,
      watch: 0.1
    },
    entry: { first: 0.45, pullback: 0.35, breakout: 0.2 },
    takeProfit: { tp1: 0.3, tp2: 0.4, tp3: 0.3 },
    trailStopPct: 0.04
  },
  balanced: {
    label: '平衡',
    position: {
      buyHigh: 0.6,
      buyMid: 0.45,
      buyWatchHigh: 0.4,
      buyWatchMid: 0.25,
      reduce: 0.2,
      watch: 0.12
    },
    entry: { first: 0.5, pullback: 0.3, breakout: 0.2 },
    takeProfit: { tp1: 0.4, tp2: 0.4, tp3: 0.2 },
    trailStopPct: 0.05
  },
  aggressive: {
    label: '激进',
    position: {
      buyHigh: 0.75,
      buyMid: 0.6,
      buyWatchHigh: 0.5,
      buyWatchMid: 0.35,
      reduce: 0.25,
      watch: 0.15
    },
    entry: { first: 0.55, pullback: 0.25, breakout: 0.2 },
    takeProfit: { tp1: 0.35, tp2: 0.35, tp3: 0.3 },
    trailStopPct: 0.06
  }
})

const clamp01 = (value, fallback = 0) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return fallback
  return Math.max(0, Math.min(1, num))
}

const normalizeTriplet = (a, b, c, defaults = [0.4, 0.4, 0.2]) => {
  const values = [Number(a), Number(b), Number(c)].map((item) => (Number.isFinite(item) ? Math.max(item, 0) : 0))
  const sum = values.reduce((acc, item) => acc + item, 0)
  if (sum <= 0) return defaults
  return values.map((item) => item / sum)
}

const currentAdviceTemplate = computed(() => adviceTemplates[adviceProfile.value] || adviceTemplates.balanced)

const operationSuggestion = computed(() => {
  const signal = analysisResult.value?.signal || null
  const stats = backtestTradeStats.value
  const hasGridBest = !!gridSummary.value || gridTopRuns.value.length > 0
  const tpl = currentAdviceTemplate.value

  let direction = 'watch'
  let reason = '暂无明确趋势信号，建议等待突破或支撑确认。'
  let score = 0

  if (signal?.action === 'breakout') {
    direction = 'buy'
    reason = signal.reason || '价格向上突破阻力位。'
    score += 2
  } else if (signal?.action === 'near_support') {
    direction = 'buy_watch'
    reason = signal.reason || '价格接近支撑位，等待确认后分批加仓。'
    score += 1
  } else if (signal?.action === 'breakdown') {
    direction = 'sell'
    reason = signal.reason || '价格跌破支撑位。'
    score -= 2
  } else if (signal?.action === 'near_resistance') {
    direction = 'reduce'
    reason = signal.reason || '价格接近阻力位，建议减仓保护收益。'
    score -= 1
  } else if (signal?.reason) {
    reason = signal.reason
  }

  if (stats) {
    if (stats.winRate >= 60) score += 1
    else if (stats.winRate < 45) score -= 1
  }
  if (hasGridBest) score += 0.5

  if (direction === 'buy' && score <= 0) direction = 'buy_watch'
  if (direction === 'sell' && score >= 0) direction = 'reduce'

  const confidence = score >= 2 ? '高' : score <= -1 ? '低' : '中'

  let positionPct = clamp01(tpl.position.watch, 0.1)
  if (direction === 'buy') {
    positionPct = confidence === 'High' ? clamp01(tpl.position.buyHigh, 0.6) : clamp01(tpl.position.buyMid, 0.45)
  } else if (direction === 'buy_watch') {
    positionPct =
      confidence === 'High' ? clamp01(tpl.position.buyWatchHigh, 0.4) : clamp01(tpl.position.buyWatchMid, 0.25)
  } else if (direction === 'reduce') {
    positionPct = clamp01(tpl.position.reduce, 0.2)
  } else if (direction === 'sell') {
    positionPct = 0
  }

  if (stats?.winRate && stats.winRate < 45) positionPct = Math.max(0, positionPct - 0.1)
  if (stats?.winRate && stats.winRate > 65) positionPct = Math.min(0.85, positionPct + 0.1)

  const stopLoss = signal?.stop_loss ?? null
  const takeProfit = signal?.take_profit ?? null
  const lastClose = signal?.last_close ?? null
  if (lastClose && stopLoss && Number(stopLoss) >= Number(lastClose)) {
    positionPct = Math.min(positionPct, 0.15)
  }

  const delta =
    Number.isFinite(Number(takeProfit)) && Number.isFinite(Number(lastClose))
      ? Number(takeProfit) - Number(lastClose)
      : null
  const tp1Price =
    Number.isFinite(delta) && delta > 0 && Number.isFinite(Number(lastClose))
      ? Number((Number(lastClose) + delta * 0.5).toFixed(2))
      : takeProfit
  const tp2Price = Number.isFinite(Number(takeProfit)) ? Number(Number(takeProfit).toFixed(2)) : null
  const tp3Price =
    Number.isFinite(delta) && delta > 0 && Number.isFinite(Number(takeProfit))
      ? Number((Number(takeProfit) + delta * 0.5).toFixed(2))
      : null

  const [entry1, entry2, entry3] = normalizeTriplet(tpl.entry.first, tpl.entry.pullback, tpl.entry.breakout, [0.5, 0.3, 0.2])
  const [tp1Ratio, tp2Ratio, tp3Ratio] = normalizeTriplet(tpl.takeProfit.tp1, tpl.takeProfit.tp2, tpl.takeProfit.tp3, [0.4, 0.4, 0.2])

  const hintParts = []
  if (stats) {
    hintParts.push(`回测胜率 ${formatNumber(stats.winRate, 1)}%，累计盈亏 ${formatNumber(stats.totalProfit, 2)}`)
  }
  if (hasGridBest) {
    hintParts.push('已获得寻优组合，建议先对重点标的做二次回测后再实盘。')
  }
  if (signal?.support || signal?.resistance) {
    hintParts.push(`支撑位 ${formatNumber(signal?.support)}，阻力位 ${formatNumber(signal?.resistance)}`)
  }

  const actionTextMap = {
    buy: '买入 / 加仓',
    buy_watch: '观察待买',
    sell: '止损 / 清仓',
    reduce: '减仓',
    watch: '观望'
  }

  return {
    direction,
    actionText: actionTextMap[direction] || actionTextMap.watch,
    confidence,
    reason,
    hint: hintParts.join('；'),
    lastClose,
    stopLoss,
    takeProfit,
    positionPct,
    positionText: `${Math.round(positionPct * 100)}%`,
    profileKey: adviceProfile.value,
    profileLabel: tpl.label,
    tranchePlan:
      direction === 'buy' || direction === 'buy_watch'
        ? [
            { label: '首批', ratio: entry1, trigger: '当前价附近先建第一笔仓位' },
            { label: '回踩加仓', ratio: entry2, trigger: '回踩支撑不破时加仓' },
            { label: '突破加仓', ratio: entry3, trigger: '突破确认后追加仓位' }
          ]
        : [{ label: '防守', ratio: 1, trigger: '优先降低风险敞口' }],
    takeProfitPlan:
      direction === 'buy' || direction === 'buy_watch'
        ? [
            { label: 'TP1', ratio: tp1Ratio, target: tp1Price },
            { label: 'TP2', ratio: tp2Ratio, target: tp2Price },
            { label: 'TP3', ratio: tp3Ratio, target: tp3Price }
          ]
        : [
            { label: '减仓线', ratio: 0.5, target: signal?.resistance ?? null },
            { label: '退出线', ratio: 0.5, target: stopLoss }
          ],
    riskRule: {
      hardStop: stopLoss,
      trailStopPct: clamp01(tpl.trailStopPct, 0.05)
    }
  }
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
    backtestForm.symbols = candidate.symbols.join(', ')
  }
  if (typeof candidate.symbol === 'string' && candidate.symbol.trim()) {
    backtestForm.symbols = candidate.symbol.trim()
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
  backtestForm.symbols = text
  chartSymbol.value = text
  activeTab.value = 'strategy'
}

const inferMarketBySymbol = (symbol) => {
  const raw = String(symbol || '').trim().toLowerCase()
  if (raw.startsWith('us')) return 'US'
  if (raw.startsWith('hk')) return 'HK'
  if (raw.startsWith('sh')) return 'SH'
  if (raw.startsWith('sz3')) return '300'
  if (raw.startsWith('sz')) return 'SZ'
  return market.value || 'SH'
}

const applySymbolToAnalysis = async (symbol) => {
  if (!symbol) return
  const text = String(symbol).trim()
  if (!text) return
  toolForm.symbols = text
  toolForm.market = inferMarketBySymbol(text)
  activeTab.value = 'tools'
  await runTool()
}

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

const applyStrategyDefaults = (strategy, target) => {
  if (!strategy || !Array.isArray(strategy.params)) return
  strategy.params.forEach((param) => {
    if (target[param.key] === undefined) {
      target[param.key] = param.default
    }
  })
}

const resetStrategyParams = (strategy, target) => {
  Object.keys(target).forEach((key) => {
    delete target[key]
  })
  if (!strategy || !Array.isArray(strategy.params)) return
  strategy.params.forEach((param) => {
    target[param.key] = param.default
  })
}

const gridFallbackValue = (param) => {
  if (param.key === 'xd' && gridForm.buy_xd_list) return String(gridForm.buy_xd_list)
  if (param.key === 'stop_loss_n' && gridForm.stop_loss_n_list) return String(gridForm.stop_loss_n_list)
  if (param.key === 'stop_win_n' && gridForm.stop_win_n_list) return String(gridForm.stop_win_n_list)
  if (param.default === undefined || param.default === null) return ''
  return String(param.default)
}

const applyGridDefaults = (strategy, target) => {
  if (!strategy || !Array.isArray(strategy.params)) return
  strategy.params.forEach((param) => {
    if (target[param.key] === undefined) {
      target[param.key] = gridFallbackValue(param)
    }
  })
}

const resetGridParamLists = (strategy, target) => {
  Object.keys(target).forEach((key) => {
    delete target[key]
  })
  if (!strategy || !Array.isArray(strategy.params)) return
  strategy.params.forEach((param) => {
    target[param.key] = gridFallbackValue(param)
  })
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

const buildMarkers = () => {
  const orders = chartOrdersAll.value || []
  if (!orders.length) return []
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
  return markers.sort((a, b) => String(a.time).localeCompare(String(b.time)))
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
  if (!candleSeries.value || !selectedOrder.value) return
  const order = selectedOrder.value
  const lines = []
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
    : backtestForm.symbols.split(/[\s,;]+/).filter(Boolean)
  if (!symbols.length) return
  if (!chartSymbol.value) chartSymbol.value = symbols[0]
  klineLoading.value = true
  klineError.value = ''
  try {
    const { data } = await api.get('/quant/klines', {
      params: {
        symbol: chartSymbol.value,
        market: backtestForm.market,
        start: backtestForm.start || undefined,
        end: backtestForm.end || undefined,
        limit: 2000
      }
    })
    const items = data.data?.items || []
    klineData.value = items.slice().sort((a, b) => {
      const left = toDateInt(a.date) || 0
      const right = toDateInt(b.date) || 0
      return left - right
    })
    chartWindow.offset = 0
    await nextTick()
    updateChartData()
  } catch (err) {
    klineError.value = err?.message || String(err)
  } finally {
    klineLoading.value = false
  }
}

const parseStringList = (raw) =>
  String(raw)
    .split(/[\s,;，、]+/)
    .map((item) => item.trim())
    .filter(Boolean)

const parseNumberList = (raw) =>
  String(raw)
    .split(/[\s,;，、]+/)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item))

const parseBooleanList = (raw) =>
  parseStringList(raw).map((item) => {
    const value = item.toLowerCase()
    return ['true', '1', 'yes', 'y'].includes(value)
  })

const buildGridParamPayload = (strategy, source) => {
  if (!strategy || !Array.isArray(strategy.params)) return {}
  const payload = {}
  strategy.params.forEach((param) => {
    const raw = source[param.key]
    if (raw === undefined || raw === null || String(raw).trim() === '') return
    if (param.type === 'bool') {
      const list = parseBooleanList(raw)
      if (list.length) payload[param.key] = list
      return
    }
    if (param.type === 'int') {
      const list = parseNumberList(raw).map((item) => Math.round(item))
      if (list.length) payload[param.key] = list
      return
    }
    if (param.type === 'float') {
      const list = parseNumberList(raw)
      if (list.length) payload[param.key] = list
      return
    }
    const list = parseStringList(raw)
    if (list.length) payload[param.key] = list
  })
  return payload
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

const displaySymbol = (item) => {
  if (!item || !item.symbol) return ''
  const lower = item.symbol.toLowerCase()
  if (lower.startsWith('sh') || lower.startsWith('sz')) {
    return item.symbol.slice(2)
  }
  return item.symbol
}

const displayKind = (kind) => {
  if (kind === 'index') return '指数'
  if (kind === 'stock') return '个股'
  return '-'
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
  const name = window.prompt('保存组合名称')
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
  const text = selectedSymbols.value.join(', ')
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

const buildBacktestPayload = () => ({
  market: backtestForm.market,
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
})

const buildStockSelectPayload = () => {
  const rawSymbols = String(backtestForm.symbols || '').trim()
  const fallbackCandidateLimit = Math.max(Number(gridForm.symbol_eval_limit || 120), Number(gridForm.symbol_top_n || 10) * 3)
  return {
    market: backtestForm.market,
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
  const job = await store.startVerify()
  await store.fetchJob(job.id)
}

const runKlUpdate = async () => {
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
  await store.fetchJob(job.id)
}

const runBacktest = async () => {
  const job = await store.startBacktest(buildBacktestPayload())
  await store.fetchJob(job.id)
  return job
}

const runStockSelect = async () => {
  const job = await store.startStockSelect(buildStockSelectPayload())
  await store.fetchJob(job.id)
  return job
}

const runClosedLoop = async () => {
  flowRunning.value = true
  klineError.value = ''
  try {
    const selectQueued = await store.startStockSelect(buildStockSelectPayload())
    const selectDone = await waitForJobDone(selectQueued.id)
    const selectResult = selectDone?.result || {}
    const topSymbols = Array.isArray(selectResult.top_symbols)
      ? selectResult.top_symbols.map((item) => String(item.symbol || '').trim()).filter(Boolean)
      : []
    if (!topSymbols.length) {
      throw new Error('独立选股未返回可回测标的，请调整范围后重试')
    }

    const picked = topSymbols.slice(0, Math.max(1, Number(gridForm.symbol_top_n || 10)))
    backtestForm.symbols = picked.join(', ')
    chartSymbol.value = picked[0]

    const backtestQueued = await store.startBacktest(buildBacktestPayload())
    await waitForJobDone(backtestQueued.id)

    toolForm.market = backtestForm.market
    toolForm.tool = 'support_resistance'
    toolForm.symbols = picked[0]
    toolForm.start = backtestForm.start || ''
    toolForm.end = backtestForm.end || ''
    const analysisQueued = await store.startQuantTool({
      market: toolForm.market,
      tool: toolForm.tool,
      symbols: toolForm.symbols,
      n_folds: toolForm.n_folds,
      start: toolForm.start || undefined,
      end: toolForm.end || undefined,
      limit: toolForm.limit,
      options: buildToolOptions()
    })
    await waitForJobDone(analysisQueued.id)

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
  const baseMarket = gridUseBacktestBase.value ? backtestForm.market : gridForm.market
  const baseSymbols = gridUseBacktestBase.value ? backtestForm.symbols : gridForm.symbols
  const baseCash = gridUseBacktestBase.value ? backtestForm.cash : gridForm.cash
  const baseStart = gridUseBacktestBase.value ? backtestForm.start : gridForm.start
  const baseEnd = gridUseBacktestBase.value ? backtestForm.end : gridForm.end
  const baseNFolds = gridUseBacktestBase.value ? backtestForm.n_folds : gridForm.n_folds
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
    max_runs: gridForm.max_runs
  })
  await store.fetchJob(job.id)
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
  const job = await store.startQuantTool({
    market: toolForm.market,
    tool: toolForm.tool,
    symbols: toolForm.symbols,
    n_folds: toolForm.n_folds,
    start: toolForm.start || undefined,
    end: toolForm.end || undefined,
    limit: toolForm.limit,
    options: buildToolOptions()
  })
  await store.fetchJob(job.id)
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
  if (settingsSaveTimer) {
    clearTimeout(settingsSaveTimer)
    settingsSaveTimer = null
  }
  if (chartRef.value) {
    chartRef.value.remove()
    chartRef.value = null
  }
  if (equityChartRef.value) {
    equityChartRef.value.remove()
    equityChartRef.value = null
  }
})
</script>
