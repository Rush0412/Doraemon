<template>
  <section class="grid grid-2 strategy-layout" v-show="active">
    <BacktestSection
      :backtest-form="backtestForm"
      :strategy-error="strategyError"
      :buy-strategies="buyStrategies"
      :sell-strategies="sellStrategies"
      :active-buy-strategy="activeBuyStrategy"
      :active-sell-strategy="activeSellStrategy"
      :buy-strategy-id="buyStrategyId"
      :sell-strategy-id="sellStrategyId"
      :buy-strategy-params="buyStrategyParams"
      :sell-strategy-params="sellStrategyParams"
      :run-backtest="runBacktest"
      :run-stock-select="runStockSelect"
      :run-closed-loop="runClosedLoop"
      :actions-busy="actionsBusy"
      :backtest-summary="backtestSummary"
      :backtest-top-symbols="backtestTopSymbols"
      :backtest-actionable-candidates="backtestActionableCandidates"
      :stock-select-summary="stockSelectSummary"
      :stock-select-diagnostics="stockSelectDiagnostics"
      :stock-select-top-symbols="stockSelectTopSymbols"
      :stock-select-actionable-candidates="stockSelectActionableCandidates"
      :stock-select-recommendation="stockSelectRecommendation"
      :format-number="formatNumber"
      :format-selected-symbol="formatSelectedSymbol"
      :apply-symbol-to-backtest="applySymbolToBacktest"
      :apply-symbol-to-analysis="applySymbolToAnalysis"
      @update:buy-strategy-id="emit('update:buyStrategyId', $event)"
      @update:sell-strategy-id="emit('update:sellStrategyId', $event)"
    />
    <GridSearchSection
      :backtest-form="backtestForm"
      :grid-form="gridForm"
      :grid-use-backtest-base="gridUseBacktestBase"
      :grid-explore-all-strategies="gridExploreAllStrategies"
      :buy-strategies="buyStrategies"
      :sell-strategies="sellStrategies"
      :active-buy-strategy="activeBuyStrategy"
      :active-sell-strategy="activeSellStrategy"
      :grid-buy-param-lists="gridBuyParamLists"
      :grid-sell-param-lists="gridSellParamLists"
      :buy-strategy-id="buyStrategyId"
      :sell-strategy-id="sellStrategyId"
      :run-grid-search="runGridSearch"
      :actions-busy="actionsBusy"
      :grid-summary="gridSummary"
      :grid-diagnostics="gridDiagnostics"
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
      :format-number="formatNumber"
      @update:buy-strategy-id="emit('update:buyStrategyId', $event)"
      @update:sell-strategy-id="emit('update:sellStrategyId', $event)"
      @update:grid-use-backtest-base="emit('update:gridUseBacktestBase', $event)"
      @update:grid-explore-all-strategies="emit('update:gridExploreAllStrategies', $event)"
    />
    <BacktestVisualSection
      :backtest-form="backtestForm"
      :backtest-trade-stats="backtestTradeStats"
      :backtest-symbols="backtestSymbols"
      :chart-symbol="chartSymbol"
      :order-filter="orderFilter"
      :selected-order-key="selectedOrderKey"
      :show-stop-lines="showStopLines"
      :chart-window="chartWindow"
      :kline-loading="klineLoading"
      :kline-error="klineError"
      :hover-info="hoverInfo"
      :kline-data="klineData"
      :equity-data="equityData"
      :operation-suggestion="operationSuggestion"
      :advice-profile="adviceProfile"
      :advice-templates="adviceTemplates"
      :filtered-orders="filteredOrders"
      :paged-orders="pagedOrders"
      :order-page="orderPage"
      :order-page-size="orderPageSize"
      :order-total-pages="orderTotalPages"
      :order-key="orderKey"
      :format-number="formatNumber"
      :format-kline-date="formatKlineDate"
      :resolve-order-profit="resolveOrderProfit"
      :select-order="selectOrder"
      :shift-window="shiftWindow"
      :load-kline-chart="loadKlineChart"
      :show-backtest-visual="showBacktestVisual"
      :format-selected-symbol="formatSelectedSymbol"
      :set-kline-container="setKlineContainer"
      :set-equity-container="setEquityContainer"
      @update:advice-profile="emit('update:adviceProfile', $event)"
      @update:chart-symbol="emit('update:chartSymbol', $event)"
      @update:order-filter="emit('update:orderFilter', $event)"
      @update:selected-order-key="emit('update:selectedOrderKey', $event)"
      @update:show-stop-lines="emit('update:showStopLines', $event)"
      @update:order-page="emit('update:orderPage', $event)"
      @update:order-page-size="emit('update:orderPageSize', $event)"
    />
  </section>
</template>

<script setup>
import BacktestSection from './strategy/BacktestSection.vue'
import BacktestVisualSection from './strategy/BacktestVisualSection.vue'
import GridSearchSection from './strategy/GridSearchSection.vue'

defineProps({
  active: Boolean,
  backtestForm: Object,
  gridForm: Object,
  strategyError: String,
  gridUseBacktestBase: Boolean,
  gridExploreAllStrategies: Boolean,
  buyStrategies: Array,
  sellStrategies: Array,
  activeBuyStrategy: Object,
  activeSellStrategy: Object,
  gridBuyParamLists: Object,
  gridSellParamLists: Object,
  buyStrategyId: String,
  sellStrategyId: String,
  buyStrategyParams: Object,
  sellStrategyParams: Object,
  runBacktest: Function,
  runStockSelect: Function,
  runClosedLoop: Function,
  actionsBusy: Boolean,
  backtestSummary: Object,
  backtestTopSymbols: Array,
  backtestActionableCandidates: Array,
  stockSelectSummary: Object,
  stockSelectDiagnostics: Object,
  stockSelectTopSymbols: Array,
  stockSelectActionableCandidates: Array,
  stockSelectRecommendation: Object,
  backtestTradeStats: Object,
  backtestSymbols: Array,
  chartSymbol: String,
  orderFilter: String,
  selectedOrderKey: String,
  showStopLines: Boolean,
  chartWindow: Object,
  klineLoading: Boolean,
  klineError: String,
  hoverInfo: Object,
  klineData: Array,
  equityData: Array,
  operationSuggestion: Object,
  adviceProfile: String,
  adviceTemplates: Object,
  filteredOrders: Array,
  pagedOrders: Array,
  orderPage: Number,
  orderPageSize: Number,
  orderTotalPages: Number,
  orderKey: Function,
  formatNumber: Function,
  formatKlineDate: Function,
  resolveOrderProfit: Function,
  selectOrder: Function,
  shiftWindow: Function,
  loadKlineChart: Function,
  showBacktestVisual: Boolean,
  runGridSearch: Function,
  gridSummary: Object,
  gridDiagnostics: Object,
  gridTopSymbols: Array,
  gridActionableCandidates: Array,
  gridRecommendation: Object,
  gridErrors: Array,
  gridNextParamSuggestions: Object,
  gridTopRuns: Array,
  gridSummaryText: String,
  applyGridToBacktest: Function,
  applyGridRunToBacktest: Function,
  applyGridNextSuggestions: Function,
  applySymbolToBacktest: Function,
  applySymbolToAnalysis: Function,
  formatSymbolText: Function,
  formatSelectedSymbol: Function,
  setKlineContainer: Function,
  setEquityContainer: Function
})

const emit = defineEmits([
  'update:buyStrategyId',
  'update:sellStrategyId',
  'update:adviceProfile',
  'update:gridUseBacktestBase',
  'update:gridExploreAllStrategies',
  'update:chartSymbol',
  'update:orderFilter',
  'update:selectedOrderKey',
  'update:showStopLines',
  'update:orderPage',
  'update:orderPageSize'
])
</script>

