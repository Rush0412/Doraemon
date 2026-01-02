<template>
  <div class="quant-shell">
    <section class="hero">
      <div class="hero-head">
        <div>
          <p class="eyebrow">Doraemon Quant Suite</p>
          <h1>阿布量化控制台</h1>
          <p class="hero-sub">
            数据更新、回测、参数寻优与量化分析一体化视图。
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
      :actions-busy="actionsBusy"
      :backtest-summary="backtestSummary"
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
      :grid-summary-text="gridSummaryText"
      :apply-grid-to-backtest="applyGridToBacktest"
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
    subtitle: '检索 → 更新',
    hint: '先检索并建立选股篮，再更新 K 线到 PG 数据库。'
  },
  {
    id: 'strategy',
    step: '02',
    title: '策略验证',
    subtitle: '回测 → 寻优',
    hint: '先回测验证，再用网格寻优确定参数并回填。'
  },
  {
    id: 'tools',
    step: '03',
    title: '量化分析',
    subtitle: '解释与对比',
    hint: '用趋势线、相关性与统计指标解释策略表现。'
  },
  {
    id: 'jobs',
    step: '04',
    title: '任务记录',
    subtitle: '导出与复盘',
    hint: '查看执行过程、导出结果并沉淀结论。'
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
  n_folds: 1,
  start: '',
  end: '',
  max_runs: 30
})

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

const actionsBusy = computed(
  () => store.jobsLoading || store.activeJobLoading || store.symbolsLoading
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

const backtestOrders = computed(() => backtestJob.value?.result?.orders || [])

const filteredOrders = computed(() => {
  const orders = backtestOrders.value || []
  const scoped = chartSymbol.value
    ? orders.filter((item) => String(item.symbol || '').toLowerCase() === chartSymbol.value.toLowerCase())
    : orders
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
  if (!orders.length) return null
  const profits = orders.map((item) => resolveOrderProfit(item))
  const total = orders.length
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
  size: 160,
  offset: 0
})
const hoverInfo = ref(null)

const gridSummary = computed(() => {
  if (!store.activeJob || store.activeJob.type !== 'grid_search') return null
  return store.activeJob.result?.best || null
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

const applyGridToBacktest = async () => {
  if (!gridSummary.value) return
  if (gridSummary.value.buy_strategy) {
    buyStrategyId.value = gridSummary.value.buy_strategy
  }
  if (gridSummary.value.sell_strategy) {
    sellStrategyId.value = gridSummary.value.sell_strategy
  }
  await nextTick()
  if (gridSummary.value.buy_params) {
    resetStrategyParams(activeBuyStrategy.value, buyStrategyParams)
    Object.assign(buyStrategyParams, gridSummary.value.buy_params)
    if (gridSummary.value.buy_params.xd !== undefined) {
      backtestForm.buy_xd = Number(gridSummary.value.buy_params.xd) || backtestForm.buy_xd
    }
  }
  if (gridSummary.value.sell_params) {
    resetStrategyParams(activeSellStrategy.value, sellStrategyParams)
    Object.assign(sellStrategyParams, gridSummary.value.sell_params)
    if (gridSummary.value.sell_params.stop_loss_n !== undefined) {
      backtestForm.stop_loss_n = Number(gridSummary.value.sell_params.stop_loss_n)
    }
    if (gridSummary.value.sell_params.stop_win_n !== undefined) {
      backtestForm.stop_win_n = Number(gridSummary.value.sell_params.stop_win_n)
    }
  }
  if (gridSummary.value.buy_xd) backtestForm.buy_xd = gridSummary.value.buy_xd
  if (gridSummary.value.stop_loss_n !== undefined) backtestForm.stop_loss_n = gridSummary.value.stop_loss_n
  if (gridSummary.value.stop_win_n !== undefined) backtestForm.stop_win_n = gridSummary.value.stop_win_n
  if (Array.isArray(gridSummary.value.symbols) && gridSummary.value.symbols.length) {
    backtestForm.symbols = gridSummary.value.symbols.join(', ')
  }
  if (gridSummary.value.market) backtestForm.market = gridSummary.value.market
  activeTab.value = 'strategy'
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
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  const raw = String(value).trim()
  if (!raw) return null
  if (/^\d{8}$/.test(raw)) return Number(raw)
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

const focusOrder = (order) => {
  if (!order || !klineData.value.length) return
  const dateInt = toDateInt(order.buy_date)
  if (!dateInt) return
  const index = klineData.value.findIndex((item) => toDateInt(item.date) === dateInt)
  if (index < 0) return
  const total = klineData.value.length
  const size = Math.max(60, Math.min(chartWindow.size || 160, total))
  const to = Math.min(total - 1, index + Math.floor(size / 2))
  chartWindow.offset = Math.max(0, total - 1 - to)
  applyVisibleRange()
}

const resolveOrderProfit = (order) => {
  if (!order) return 0
  if (order.profit !== undefined && order.profit !== null) {
    const val = Number(order.profit)
    if (Number.isFinite(val)) return val
  }
  const buy = Number(order.buy_price)
  const sell = Number(order.sell_price)
  if (Number.isFinite(buy) && Number.isFinite(sell)) return sell - buy
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
    height: 340,
    width,
    layout: {
      background: { color: '#ffffff' },
      textColor: '#1b1a18',
      fontFamily: "Sora, 'Noto Sans SC', sans-serif"
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
    upColor: '#1f7a4b',
    downColor: '#b33a3a',
    wickUpColor: '#1f7a4b',
    wickDownColor: '#b33a3a',
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
    height: 220,
    width,
    layout: {
      background: { color: '#ffffff' },
      textColor: '#1b1a18',
      fontFamily: "Sora, 'Noto Sans SC', sans-serif"
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
  const size = Math.max(60, Math.min(chartWindow.size || 160, total))
  const maxOffset = Math.max(0, total - size)
  if (chartWindow.offset > maxOffset) chartWindow.offset = maxOffset
  if (chartWindow.offset < 0) chartWindow.offset = 0
  const to = total - 1 - chartWindow.offset
  const from = Math.max(0, to - size + 1)
  chartRef.value.timeScale().setVisibleLogicalRange({ from, to })
}

const buildMarkers = () => {
  const orders = (filteredOrders.value || []).slice(0, 200)
  const markers = []
  orders.forEach((order) => {
    const buyTime = toChartTime(order.buy_date)
    const sellTime = toChartTime(order.sell_date)
    if (buyTime) {
      markers.push({
        time: buyTime,
        position: 'belowBar',
        color: '#1f7a4b',
        shape: 'arrowUp',
        text: `买 ${formatNumber(order.buy_price)}`
      })
    }
    if (sellTime && Number(order.sell_date) > 0) {
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
    const startIdx = Math.max(0, Math.min(klineData.value.length - 1, Math.round(Number(line.x_start) || 0)))
    const endIdx = Math.max(0, Math.min(klineData.value.length - 1, Math.round(Number(line.x_end) || 0)))
    const startTime = toChartTime(klineData.value[startIdx]?.date)
    const endTime = toChartTime(klineData.value[endIdx]?.date)
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
  const data = (klineData.value || []).slice().sort((a, b) => {
    const left = toDateInt(a.date) || 0
    const right = toDateInt(b.date) || 0
    return left - right
  })
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
            ? 'rgba(31, 122, 75, 0.4)'
            : 'rgba(179, 58, 58, 0.4)'
      }))
      .filter((item) => item.time)
  )
  candleSeries.value.setMarkers(buildMarkers())
  applyVisibleRange()
  applyOrderLines()
  applyAnalysisOverlay()
}

const buildEquitySeries = () => {
  const orders = filteredOrders.value || []
  const rows = orders
    .map((order) => {
      const time = toChartTime(order.sell_date || order.buy_date)
      return {
        time,
        profit: resolveOrderProfit(order)
      }
    })
    .filter((row) => row.time)
    .sort((a, b) => String(a.time).localeCompare(String(b.time)))
  let cumulative = 0
  return rows.map((row) => {
    cumulative += row.profit
    return { time: row.time, value: Number(cumulative.toFixed(2)) }
  })
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
  const step = Math.max(10, Math.floor((chartWindow.size || 160) / 5))
  const size = Math.max(60, Math.min(chartWindow.size || 160, data.length))
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
        limit: 600
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
    .split(/[\s,;]+/)
    .map((item) => item.trim())
    .filter(Boolean)

const parseNumberList = (raw) =>
  String(raw)
    .split(/[\s,;]+/)
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
  const job = await store.startBacktest({
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
    sell_params: { ...sellStrategyParams }
  })
  await store.fetchJob(job.id)
}

const runGridSearch = async () => {
  const buyGrid = buildGridParamPayload(activeBuyStrategy.value, gridBuyParamLists)
  const sellGrid = buildGridParamPayload(activeSellStrategy.value, gridSellParamLists)
  const job = await store.startGridSearch({
    market: gridForm.market,
    symbols: gridForm.symbols,
    n_folds: gridForm.n_folds,
    start: gridForm.start || undefined,
    end: gridForm.end || undefined,
    cash: gridForm.cash,
    buy_strategy: buyStrategyId.value,
    sell_strategy: sellStrategyId.value,
    buy_params_grid: buyGrid,
    sell_params_grid: sellGrid,
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
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
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
