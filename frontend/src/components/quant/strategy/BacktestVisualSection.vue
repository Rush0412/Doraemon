<template>
  <div v-if="showBacktestVisual" class="result-card backtest-visual trading-stage">
    <h3>回测可视化</h3>
    <div class="result-grid" v-if="backtestTradeStats">
      <div><p class="muted">交易次数</p><p class="metric-value">{{ backtestTradeStats.total }}</p></div>
      <div><p class="muted">胜率</p><p class="metric-value">{{ formatNumber(backtestTradeStats.winRate, 1) }}%</p></div>
      <div><p class="muted">总盈利</p><p class="metric-value">{{ formatNumber(backtestTradeStats.totalProfit, 2) }}</p></div>
      <div><p class="muted">单笔均值</p><p class="metric-value">{{ formatNumber(backtestTradeStats.avgProfit, 2) }}</p></div>
    </div>
    <p v-else class="muted">暂无交易明细，建议扩大回测区间或调整买入周期。</p>
    <div class="toolbar">
      <label class="label">展示标的</label>
      <select v-model="chartSymbolProxy" class="select">
        <option v-for="symbol in backtestSymbols" :key="symbol" :value="symbol">
          {{ formatSelectedSymbol(symbol, backtestForm.market) }}
        </option>
      </select>
      <label class="label">订单筛选</label>
      <select v-model="orderFilterProxy" class="select">
        <option value="all">全部</option>
        <option value="win">盈利</option>
        <option value="loss">亏损</option>
        <option value="hold">持仓</option>
      </select>
      <label class="label">选中订单</label>
      <select v-model="selectedOrderKeyProxy" class="select">
        <option value="">未选择</option>
        <option v-for="order in filteredOrders" :key="orderKey(order)" :value="orderKey(order)">
          {{ order.symbol }} · {{ formatKlineDate(order.buy_date) }} · {{ formatNumber(order.buy_price) }}
        </option>
      </select>
      <label class="label">显示区间</label>
      <input v-model.number="chartWindow.size" type="range" min="60" max="360" step="20" />
      <span class="muted">最近 {{ chartWindow.size }} 根</span>
      <button class="btn-secondary" @click="shiftWindow(1)">更早</button>
      <button class="btn-secondary" @click="shiftWindow(-1)">更晚</button>
      <label class="toggle">
        <input type="checkbox" v-model="showStopLinesProxy" />
        <span>止损/止盈线</span>
      </label>
      <button class="btn-secondary" @click="loadKlineChart" :disabled="klineLoading">
        {{ klineLoading ? '加载中' : '加载K线' }}
      </button>
      <span class="muted">上三角为买入，下三角为卖出</span>
    </div>
    <p v-if="klineError" class="error">{{ klineError }}</p>
    <div class="kline-chart" :ref="setKlineContainer">
      <div v-if="hoverInfo" class="kline-tooltip">
        <div class="mono">日期 {{ hoverInfo.date }}</div>
        <div class="mono">开 {{ formatNumber(hoverInfo.open) }}</div>
        <div class="mono">高 {{ formatNumber(hoverInfo.high) }}</div>
        <div class="mono">低 {{ formatNumber(hoverInfo.low) }}</div>
        <div class="mono">收 {{ formatNumber(hoverInfo.close) }}</div>
        <div class="mono">量 {{ hoverInfo.volume ?? '-' }}</div>
      </div>
      <p v-if="klineLoading" class="muted">K线加载中…</p>
      <p v-else-if="!klineData.length" class="muted">请点击“加载K线”查看图表</p>
    </div>
    <p class="muted">收益曲线（累计盈亏）</p>
    <div class="equity-chart" :ref="setEquityContainer">
      <p v-if="!equityData.length" class="muted">暂无收益曲线</p>
    </div>

    <div v-if="operationSuggestion" class="result-card advice-card">
      <h3>当日操作建议</h3>
      <div class="toolbar advice-profile-toolbar">
        <label class="label">风险模板</label>
        <select v-model="adviceProfileProxy" class="select">
          <option v-for="item in adviceProfileOptions" :key="item.key" :value="item.key">
            {{ item.label }}
          </option>
        </select>
        <span class="muted">可手动调整仓位、建仓比例、止盈比例、移动止损</span>
      </div>
      <div v-if="adviceTemplate" class="info-card advice-template-card">
        <p class="muted">模板参数（当前档位）</p>
        <div class="form-grid">
          <div><label class="label">强信号买入仓位</label><input v-model.number="adviceTemplate.position.buyHigh" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">中信号买入仓位</label><input v-model.number="adviceTemplate.position.buyMid" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">观察买入(强)仓位</label><input v-model.number="adviceTemplate.position.buyWatchHigh" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">观察买入(中)仓位</label><input v-model.number="adviceTemplate.position.buyWatchMid" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">减仓比例</label><input v-model.number="adviceTemplate.position.reduce" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">观望仓位</label><input v-model.number="adviceTemplate.position.watch" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">建仓一批比例</label><input v-model.number="adviceTemplate.entry.first" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">回踩加仓比例</label><input v-model.number="adviceTemplate.entry.pullback" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">突破加仓比例</label><input v-model.number="adviceTemplate.entry.breakout" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">止盈一批比例</label><input v-model.number="adviceTemplate.takeProfit.tp1" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">止盈二批比例</label><input v-model.number="adviceTemplate.takeProfit.tp2" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">止盈三批比例</label><input v-model.number="adviceTemplate.takeProfit.tp3" type="number" min="0" max="1" step="0.05" /></div>
          <div><label class="label">移动止损比例</label><input v-model.number="adviceTemplate.trailStopPct" type="number" min="0" max="1" step="0.01" /></div>
        </div>
      </div>
      <div class="result-grid">
        <div><p class="muted">建议动作</p><p class="metric-value">{{ operationSuggestion.actionText }}</p></div>
        <div><p class="muted">信号强度</p><p class="metric-value">{{ operationSuggestion.confidence }}</p></div>
        <div><p class="muted">最新收盘</p><p class="metric-value">{{ formatNumber(operationSuggestion.lastClose) }}</p></div>
        <div>
          <p class="muted">建议仓位</p>
          <p class="metric-value">{{ operationSuggestion.positionText }}</p>
          <p class="muted">模板：{{ operationSuggestion.profileLabel || operationSuggestion.profileKey }}</p>
        </div>
        <div>
          <p class="muted">止损 / 止盈</p>
          <p class="metric-value">{{ formatNumber(operationSuggestion.stopLoss) }} / {{ formatNumber(operationSuggestion.takeProfit) }}</p>
        </div>
      </div>
      <p class="panel-note">{{ operationSuggestion.reason }}</p>
      <p class="muted" v-if="operationSuggestion.hint">{{ operationSuggestion.hint }}</p>
      <div class="info-card" v-if="operationSuggestion.tranchePlan?.length">
        <p class="muted">建仓规则</p>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>批次</th><th>仓位占比</th><th>触发条件</th></tr></thead>
            <tbody>
              <tr v-for="row in operationSuggestion.tranchePlan" :key="`entry-${row.label}`">
                <td>{{ row.label }}</td>
                <td class="mono">{{ formatNumber((row.ratio || 0) * 100, 0) }}%</td>
                <td>{{ row.trigger }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="info-card" v-if="operationSuggestion.takeProfitPlan?.length">
        <p class="muted">分批止盈</p>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>批次</th><th>减仓占比</th><th>目标价</th></tr></thead>
            <tbody>
              <tr v-for="row in operationSuggestion.takeProfitPlan" :key="`tp-${row.label}`">
                <td>{{ row.label }}</td>
                <td class="mono">{{ formatNumber((row.ratio || 0) * 100, 0) }}%</td>
                <td class="mono">{{ formatNumber(row.target) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="muted">
          硬止损：{{ formatNumber(operationSuggestion.riskRule?.hardStop) }}，
          移动止损：{{ formatNumber((operationSuggestion.riskRule?.trailStopPct || 0) * 100, 0) }}%
        </p>
      </div>
    </div>

    <div v-if="filteredOrders.length" class="result-card">
      <h3>交易明细</h3>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Symbol</th><th>买入日期</th><th>买入价</th><th>卖出日期</th><th>卖出价</th><th>止损价</th><th>止盈价</th><th>盈亏</th></tr></thead>
          <tbody>
            <tr
              v-for="order in pagedOrders"
              :key="orderKey(order)"
              :class="{ 'is-selected': orderKey(order) === selectedOrderKeyProxy }"
              @click="selectOrder(order)"
            >
              <td class="mono">{{ order.symbol }}</td>
              <td class="mono">{{ formatKlineDate(order.buy_date) }}</td>
              <td class="mono">{{ formatNumber(order.buy_price) }}</td>
              <td class="mono">{{ formatKlineDate(order.sell_date) }}</td>
              <td class="mono">{{ formatNumber(order.sell_price) }}</td>
              <td class="mono">{{ formatNumber(order.stop_loss_price) }}</td>
              <td class="mono">{{ formatNumber(order.stop_win_price) }}</td>
              <td class="mono">{{ formatNumber(resolveOrderProfit(order)) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="muted">共 {{ filteredOrders.length }} 条</span>
        <div class="pager-controls">
          <button class="btn-secondary" @click="orderPageProxy = Math.max(1, orderPageProxy - 1)" :disabled="orderPageProxy <= 1">上一页</button>
          <span class="mono">{{ orderPageProxy }} / {{ orderTotalPages }}</span>
          <button class="btn-secondary" @click="orderPageProxy = Math.min(orderTotalPages, orderPageProxy + 1)" :disabled="orderPageProxy >= orderTotalPages">下一页</button>
        </div>
        <div class="pager-size">
          <span class="muted">每页</span>
          <select v-model.number="orderPageSizeProxy" class="select">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </div>
      </div>
      <p class="muted">点击行可定位到K线标记。</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  backtestForm: Object,
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
  formatSelectedSymbol: Function,
  setKlineContainer: Function,
  setEquityContainer: Function
})

const emit = defineEmits([
  'update:adviceProfile',
  'update:chartSymbol',
  'update:orderFilter',
  'update:selectedOrderKey',
  'update:showStopLines',
  'update:orderPage',
  'update:orderPageSize'
])

const chartSymbolProxy = computed({
  get: () => props.chartSymbol,
  set: (value) => emit('update:chartSymbol', value)
})
const adviceProfileProxy = computed({
  get: () => props.adviceProfile || 'balanced',
  set: (value) => emit('update:adviceProfile', value)
})
const orderFilterProxy = computed({
  get: () => props.orderFilter,
  set: (value) => emit('update:orderFilter', value)
})
const selectedOrderKeyProxy = computed({
  get: () => props.selectedOrderKey,
  set: (value) => emit('update:selectedOrderKey', value)
})
const showStopLinesProxy = computed({
  get: () => props.showStopLines,
  set: (value) => emit('update:showStopLines', value)
})
const orderPageProxy = computed({
  get: () => props.orderPage ?? 1,
  set: (value) => emit('update:orderPage', value)
})
const orderPageSizeProxy = computed({
  get: () => props.orderPageSize ?? 20,
  set: (value) => emit('update:orderPageSize', value)
})
const adviceProfileOptions = computed(() => {
  const templates = props.adviceTemplates || {}
  return Object.entries(templates).map(([key, template]) => ({
    key,
    label: template?.label || key
  }))
})
const adviceTemplate = computed(() => {
  const templates = props.adviceTemplates || {}
  return templates[adviceProfileProxy.value] || null
})
</script>
