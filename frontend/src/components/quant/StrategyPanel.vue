<template>
  <section class="grid grid-2" v-show="active">
    <div class="panel">
      <header class="panel-title">
        <div>
          <h2>历史回测</h2>
          <p class="muted">执行经典买入突破 + ATR 止损止盈。</p>
        </div>
        <span class="pill">Backtest</span>
      </header>
      <p class="panel-note">建议回测区间 ≥ 1 年；若无成交请缩短买入周期或扩大回测时间。</p>
      <div class="form-grid">
        <div>
          <label class="label">标的列表</label>
          <input v-model="backtestForm.symbols" placeholder="sh600036, sz000001" />
        </div>
        <div>
          <label class="label">初始资金</label>
          <input v-model.number="backtestForm.cash" type="number" min="1000" />
        </div>
        <div>
          <label class="label">买入周期</label>
          <input v-model.number="backtestForm.buy_xd" type="number" min="1" />
        </div>
        <div>
          <label class="label">止损倍数</label>
          <input v-model.number="backtestForm.stop_loss_n" type="number" step="0.1" />
        </div>
        <div>
          <label class="label">止盈倍数</label>
          <input v-model.number="backtestForm.stop_win_n" type="number" step="0.1" />
        </div>
        <div>
          <label class="label">回溯年数</label>
          <input v-model.number="backtestForm.n_folds" type="number" min="1" />
        </div>
        <div>
          <label class="label">开始日期</label>
          <input v-model="backtestForm.start" type="date" />
        </div>
        <div>
          <label class="label">结束日期</label>
          <input v-model="backtestForm.end" type="date" />
        </div>
      </div>
      <div class="form-grid">
        <div>
          <label class="label">买入策略</label>
          <select v-model="buyStrategyIdProxy" class="select">
            <option v-for="item in buyStrategies" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </div>
        <div>
          <label class="label">卖出策略</label>
          <select v-model="sellStrategyIdProxy" class="select">
            <option v-for="item in sellStrategies" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </div>
        <div v-for="param in (activeBuyStrategy?.params || [])" :key="`buy-${param.key}`">
          <label class="label">{{ param.label }}</label>
          <input
            v-if="param.type !== 'bool'"
            v-model.number="buyStrategyParams[param.key]"
            :type="param.type === 'int' || param.type === 'float' ? 'number' : 'text'"
            :step="param.step || (param.type === 'int' ? 1 : 0.1)"
            :min="param.min"
            :max="param.max"
          />
          <label v-else class="toggle">
            <input type="checkbox" v-model="buyStrategyParams[param.key]" />
            <span>{{ param.label }}</span>
          </label>
        </div>
        <div v-for="param in (activeSellStrategy?.params || [])" :key="`sell-${param.key}`">
          <label class="label">{{ param.label }}</label>
          <input
            v-if="param.type !== 'bool'"
            v-model.number="sellStrategyParams[param.key]"
            :type="param.type === 'int' || param.type === 'float' ? 'number' : 'text'"
            :step="param.step || (param.type === 'int' ? 1 : 0.1)"
            :min="param.min"
            :max="param.max"
          />
          <label v-else class="toggle">
            <input type="checkbox" v-model="sellStrategyParams[param.key]" />
            <span>{{ param.label }}</span>
          </label>
        </div>
      </div>
      <div class="toolbar">
        <button class="btn-primary" @click="runBacktest" :disabled="actionsBusy">启动回测</button>
        <span class="muted">回测完成后可导出 CSV</span>
      </div>
      <div v-if="backtestSummary" class="result-card">
        <h3>回测摘要</h3>
        <div class="result-grid">
          <div>
            <p class="muted">订单行数</p>
            <p class="metric-value">{{ backtestSummary.orders_rows }}</p>
          </div>
          <div>
            <p class="muted">行为行数</p>
            <p class="metric-value">{{ backtestSummary.actions_rows }}</p>
          </div>
          <div>
            <p class="muted">基准</p>
            <p class="metric-value">{{ backtestSummary.benchmark || '-' }}</p>
          </div>
        </div>
      </div>
      <div v-if="showBacktestVisual" class="result-card backtest-visual">
        <h3>回测可视化</h3>
        <div class="result-grid" v-if="backtestTradeStats">
          <div>
            <p class="muted">交易次数</p>
            <p class="metric-value">{{ backtestTradeStats.total }}</p>
          </div>
          <div>
            <p class="muted">胜率</p>
            <p class="metric-value">{{ formatNumber(backtestTradeStats.winRate, 1) }}%</p>
          </div>
          <div>
            <p class="muted">总盈利</p>
            <p class="metric-value">{{ formatNumber(backtestTradeStats.totalProfit, 2) }}</p>
          </div>
          <div>
            <p class="muted">单笔均值</p>
            <p class="metric-value">{{ formatNumber(backtestTradeStats.avgProfit, 2) }}</p>
          </div>
        </div>
        <p v-else class="muted">暂无交易明细，建议扩大回测区间或调整买入周期。</p>
        <div class="toolbar">
          <label class="label">展示标的</label>
          <select v-model="chartSymbolProxy" class="select">
            <option v-for="symbol in backtestSymbols" :key="symbol" :value="symbol">
              {{ symbol }}
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
        <div v-if="filteredOrders.length" class="result-card">
          <h3>交易明细</h3>
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>买入日期</th>
                  <th>买入价</th>
                  <th>卖出日期</th>
                  <th>卖出价</th>
                  <th>止损价</th>
                  <th>止盈价</th>
                  <th>盈亏</th>
                </tr>
              </thead>
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
              <button
                class="btn-secondary"
                @click="orderPageProxy = Math.max(1, orderPageProxy - 1)"
                :disabled="orderPageProxy <= 1"
              >
                上一页
              </button>
              <span class="mono">{{ orderPageProxy }} / {{ orderTotalPages }}</span>
              <button
                class="btn-secondary"
                @click="orderPageProxy = Math.min(orderTotalPages, orderPageProxy + 1)"
                :disabled="orderPageProxy >= orderTotalPages"
              >
                下一页
              </button>
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
    </div>

    <div class="panel">
      <header class="panel-title">
        <div>
          <h2>参数交叉验证</h2>
          <p class="muted">多参数组合网格寻优。</p>
        </div>
        <span class="pill">Grid</span>
      </header>
      <p class="panel-note">结果里的最佳参数可一键回填到回测；寻优范围越大运行越久。</p>
      <div class="form-grid">
        <div>
          <label class="label">标的列表</label>
          <input v-model="gridForm.symbols" placeholder="sh600036, sz000001" />
        </div>
        <div>
          <label class="label">初始资金</label>
          <input v-model.number="gridForm.cash" type="number" min="1000" />
        </div>
        <div>
          <label class="label">开始日期</label>
          <input v-model="gridForm.start" type="date" />
        </div>
        <div>
          <label class="label">结束日期</label>
          <input v-model="gridForm.end" type="date" />
        </div>
        <div>
          <label class="label">买入策略</label>
          <select v-model="buyStrategyIdProxy" class="select">
            <option v-for="item in buyStrategies" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </div>
        <div>
          <label class="label">卖出策略</label>
          <select v-model="sellStrategyIdProxy" class="select">
            <option v-for="item in sellStrategies" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </div>
        <div v-for="param in (activeBuyStrategy?.params || [])" :key="`grid-buy-${param.key}`">
          <label class="label">{{ param.label }}列表</label>
          <input
            v-model="gridBuyParamLists[param.key]"
            type="text"
            :placeholder="param.type === 'bool' ? 'true,false' : '20, 42, 60'"
          />
        </div>
        <div v-for="param in (activeSellStrategy?.params || [])" :key="`grid-sell-${param.key}`">
          <label class="label">{{ param.label }}列表</label>
          <input
            v-model="gridSellParamLists[param.key]"
            type="text"
            :placeholder="param.type === 'bool' ? 'true,false' : '0.5, 1.0'"
          />
        </div>
        <div>
          <label class="label">最大运行次数</label>
          <input v-model.number="gridForm.max_runs" type="number" min="1" />
        </div>
        <div>
          <label class="label">回溯年数</label>
          <input v-model.number="gridForm.n_folds" type="number" min="1" />
        </div>
      </div>
      <div class="toolbar">
        <button class="btn-secondary" @click="runGridSearch" :disabled="actionsBusy">启动寻优</button>
        <span class="muted">输出最佳参数组合</span>
      </div>
      <div v-if="gridSummary" class="result-card">
        <h3>最佳组合</h3>
        <div class="toolbar">
          <button class="btn-secondary" @click="applyGridToBacktest">应用到回测参数</button>
          <span class="muted">自动填充买入周期/止损/止盈</span>
        </div>
        <pre class="code">{{ gridSummaryText }}</pre>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  active: Boolean,
  backtestForm: Object,
  gridForm: Object,
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
  actionsBusy: Boolean,
  backtestSummary: Object,
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
  gridSummaryText: String,
  applyGridToBacktest: Function,
  setKlineContainer: Function,
  setEquityContainer: Function
})

const emit = defineEmits([
  'update:buyStrategyId',
  'update:sellStrategyId',
  'update:chartSymbol',
  'update:orderFilter',
  'update:selectedOrderKey',
  'update:showStopLines',
  'update:orderPage',
  'update:orderPageSize'
])

const buyStrategyIdProxy = computed({
  get: () => props.buyStrategyId,
  set: (value) => emit('update:buyStrategyId', value)
})

const sellStrategyIdProxy = computed({
  get: () => props.sellStrategyId,
  set: (value) => emit('update:sellStrategyId', value)
})

const chartSymbolProxy = computed({
  get: () => props.chartSymbol,
  set: (value) => emit('update:chartSymbol', value)
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
</script>
