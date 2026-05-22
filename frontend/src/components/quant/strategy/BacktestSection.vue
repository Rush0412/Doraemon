<template>
  <div class="panel strategy-main">
    <header class="panel-title">
      <div>
        <h2>历史回测</h2>
        <p class="muted">执行经典买入突破 + ATR 止损止盈。</p>
      </div>
      <span class="pill">回测</span>
    </header>
    <p class="panel-note">建议回测区间 ≥ 1 年；若无成交请缩短买入周期或扩大回测时间。</p>
    <div class="form-grid">
      <div>
        <label class="label">标的列表</label>
        <input v-model="backtestForm.symbols" placeholder="600036, 300249" />
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
        <label class="label">佣金费率</label>
        <input v-model.number="backtestForm.commission_rate" type="number" min="0" max="0.05" step="0.00001" />
      </div>
      <div>
        <label class="label">最低佣金</label>
        <input v-model.number="backtestForm.min_commission" type="number" min="0" max="1000" step="0.1" />
      </div>
      <div>
        <label class="label">印花税率</label>
        <input v-model.number="backtestForm.stamp_tax_rate" type="number" min="0" max="0.05" step="0.00001" />
      </div>
      <div>
        <label class="label">滑点(BP)</label>
        <input v-model.number="backtestForm.slippage_bp" type="number" min="0" max="500" step="0.5" />
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
      <button class="btn-secondary" @click="runStockSelect" :disabled="actionsBusy">独立选股</button>
      <button class="btn-secondary" @click="runClosedLoop" :disabled="actionsBusy">一键闭环</button>
      <button class="btn-secondary" @click="runQuickAnalysis" :disabled="actionsBusy">量化当前标的</button>
      <span class="muted">回测完成后可导出 CSV</span>
    </div>
    <p v-if="strategyError" class="error">{{ strategyError }}</p>

    <div v-if="backtestSummary" class="result-card">
      <h3>回测摘要</h3>
      <div class="result-grid">
        <div><p class="muted">订单行数</p><p class="metric-value">{{ backtestSummary.orders_rows }}</p></div>
        <div><p class="muted">行为行数</p><p class="metric-value">{{ backtestSummary.actions_rows }}</p></div>
        <div><p class="muted">基准</p><p class="metric-value">{{ backtestSummary.benchmark || '-' }}</p></div>
        <div><p class="muted">净收益</p><p class="metric-value">{{ metricText(backtestSummary.profit_sum) }}</p></div>
        <div><p class="muted">毛收益估算</p><p class="metric-value">{{ metricText(backtestSummary.estimated_gross_profit_sum) }}</p></div>
        <div><p class="muted">总收益率</p><p class="metric-value">{{ pctText(backtestSummary.total_return) }}</p></div>
        <div><p class="muted">年化收益</p><p class="metric-value">{{ pctText(backtestSummary.annual_return) }}</p></div>
        <div><p class="muted">波动率</p><p class="metric-value">{{ pctText(backtestSummary.volatility) }}</p></div>
        <div><p class="muted">下行波动</p><p class="metric-value">{{ pctText(backtestSummary.downside_volatility) }}</p></div>
        <div><p class="muted">夏普</p><p class="metric-value">{{ metricText(backtestSummary.sharpe, 2) }}</p></div>
        <div><p class="muted">Sortino</p><p class="metric-value">{{ metricText(backtestSummary.sortino, 2) }}</p></div>
        <div><p class="muted">Calmar</p><p class="metric-value">{{ metricText(backtestSummary.calmar, 2) }}</p></div>
        <div><p class="muted">最大回撤</p><p class="metric-value">{{ pctText(backtestSummary.max_drawdown) }}</p></div>
        <div><p class="muted">回撤持续</p><p class="metric-value">{{ backtestSummary.max_drawdown_duration ?? '-' }}</p></div>
        <div><p class="muted">VaR 95%</p><p class="metric-value">{{ pctText(backtestSummary.var_95) }}</p></div>
        <div><p class="muted">CVaR 95%</p><p class="metric-value">{{ pctText(backtestSummary.cvar_95) }}</p></div>
        <div><p class="muted">佣金</p><p class="metric-value">{{ metricText(backtestSummary.commission_total) }}</p></div>
        <div><p class="muted">滑点成本估算</p><p class="metric-value">{{ metricText(backtestSummary.estimated_slippage_cost) }}</p></div>
        <div><p class="muted">总成本估算</p><p class="metric-value">{{ metricText(backtestSummary.estimated_total_cost) }}</p></div>
        <div><p class="muted">换手率估算</p><p class="metric-value">{{ pctText(backtestSummary.turnover_ratio_est) }}</p></div>
      </div>
      <p class="muted">
        成本假设：佣金 {{ pctText(backtestSummary.trade_costs?.commission_rate, 3) }}，
        最低佣金 {{ metricText(backtestSummary.trade_costs?.min_commission) }}，
        印花税 {{ pctText(backtestSummary.trade_costs?.stamp_tax_rate, 3) }}，
        滑点 {{ metricText(backtestSummary.trade_costs?.slippage_bp, 1) }} BP
      </p>
    </div>

    <div v-if="backtestTopSymbols?.length" class="result-card">
      <h3>股票回测榜单（前 {{ backtestTopSymbols.length }}）</h3>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>#</th><th>标的</th><th>胜率</th><th>累计盈亏</th><th>已平仓</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="row in backtestTopSymbols" :key="`backtest-symbol-${row.rank}-${row.symbol}`">
              <td class="mono">{{ row.rank }}</td>
              <td class="mono">{{ formatSelectedSymbol(row.symbol, backtestForm.market) }}</td>
              <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
              <td class="mono">{{ formatNumber(row.profit_sum) }}</td>
              <td class="mono">{{ row.closed_orders }}</td>
              <td><button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="backtestActionableCandidates?.length" class="result-card">
      <h3>近期可操作候选（回测）</h3>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>标的</th><th>建议动作</th><th>建议仓位</th><th>胜率</th><th>止损/止盈</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="row in backtestActionableCandidates" :key="`backtest-action-${row.symbol}`">
              <td class="mono">{{ formatSelectedSymbol(row.symbol, backtestForm.market) }}</td>
              <td>{{ row.action }}</td>
              <td class="mono">{{ row.position_range }}</td>
              <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
              <td class="mono">{{ formatNumber(row.stop_loss) }} / {{ formatNumber(row.take_profit) }}</td>
              <td class="table-actions">
                <button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button>
                <button class="btn-secondary" @click="applySymbolToAnalysis(row.symbol)">量化分析</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="stockSelectSummary" class="result-card">
      <h3>独立选股结果</h3>
      <div class="result-grid">
        <div><p class="muted">请求标的数</p><p class="metric-value">{{ stockSelectSummary.requested_symbols ?? '-' }}</p></div>
        <div><p class="muted">有效标的数</p><p class="metric-value">{{ stockSelectSummary.available_symbols ?? '-' }}</p></div>
        <div><p class="muted">已评估标的数</p><p class="metric-value">{{ stockSelectSummary.evaluated_symbols ?? '-' }}</p></div>
        <div><p class="muted">推荐模式</p><p class="metric-value">{{ stockSelectRecommendation?.mode || '-' }}</p></div>
        <div><p class="muted">净收益</p><p class="metric-value">{{ metricText(stockSelectSummary.profit_sum) }}</p></div>
        <div><p class="muted">毛收益估算</p><p class="metric-value">{{ metricText(stockSelectSummary.estimated_gross_profit_sum) }}</p></div>
        <div><p class="muted">年化收益</p><p class="metric-value">{{ pctText(stockSelectSummary.annual_return) }}</p></div>
        <div>
          <p class="muted">夏普 / Sortino</p>
          <p class="metric-value">{{ metricText(stockSelectSummary.sharpe, 2) }} / {{ metricText(stockSelectSummary.sortino, 2) }}</p>
        </div>
        <div>
          <p class="muted">Calmar / 回撤</p>
          <p class="metric-value">{{ metricText(stockSelectSummary.calmar, 2) }} / {{ pctText(stockSelectSummary.max_drawdown) }}</p>
        </div>
        <div><p class="muted">总成本估算</p><p class="metric-value">{{ metricText(stockSelectSummary.estimated_total_cost) }}</p></div>
      </div>
      <p class="muted" v-if="stockSelectRecommendation?.notes?.length">{{ stockSelectRecommendation.notes.join('；') }}</p>
      <p class="muted" v-if="stockSelectDiagnostics">
        评估上限 {{ stockSelectDiagnostics.eval_limit ?? '-' }}，最小K线 {{ stockSelectDiagnostics.min_kline_rows ?? '-' }}
      </p>
    </div>

    <div v-if="stockSelectTopSymbols?.length" class="result-card">
      <h3>独立选股 Top {{ stockSelectTopSymbols.length }}</h3>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>#</th><th>标的</th><th>胜率</th><th>累计盈亏</th><th>夏普</th><th>Sortino</th><th>回撤</th><th>总成本</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="row in stockSelectTopSymbols" :key="`select-${row.rank}-${row.symbol}`">
              <td class="mono">{{ row.rank }}</td>
              <td class="mono">{{ formatSelectedSymbol(row.symbol, backtestForm.market) }}</td>
              <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
              <td class="mono">{{ formatNumber(row.profit_sum) }}</td>
              <td class="mono">{{ formatNumber(row.sharpe, 2) }}</td>
              <td class="mono">{{ formatNumber(row.sortino, 2) }}</td>
              <td class="mono">{{ formatNumber(row.max_drawdown, 3) }}</td>
              <td class="mono">{{ formatNumber(row.estimated_total_cost) }}</td>
              <td class="table-actions">
                <button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button>
                <button class="btn-secondary" @click="applySymbolToAnalysis(row.symbol)">量化分析</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="stockSelectActionableCandidates?.length" class="result-card">
      <h3>独立选股可操作候选</h3>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>标的</th><th>建议动作</th><th>建议仓位</th><th>止损/止盈</th><th>原因</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="row in stockSelectActionableCandidates" :key="`select-action-${row.symbol}`">
              <td class="mono">{{ formatSelectedSymbol(row.symbol, backtestForm.market) }}</td>
              <td>{{ row.action }}</td>
              <td class="mono">{{ row.position_range }}</td>
              <td class="mono">{{ formatNumber(row.stop_loss) }} / {{ formatNumber(row.take_profit) }}</td>
              <td>{{ row.reason }}</td>
              <td class="table-actions">
                <button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button>
                <button class="btn-secondary" @click="applySymbolToAnalysis(row.symbol)">量化分析</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  backtestForm: Object,
  strategyError: String,
  buyStrategies: Array,
  sellStrategies: Array,
  activeBuyStrategy: Object,
  activeSellStrategy: Object,
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
  formatNumber: Function,
  formatSelectedSymbol: Function,
  applySymbolToBacktest: Function,
  applySymbolToAnalysis: Function
})

const emit = defineEmits(['update:buyStrategyId', 'update:sellStrategyId'])

const buyStrategyIdProxy = computed({
  get: () => props.buyStrategyId,
  set: (value) => emit('update:buyStrategyId', value)
})

const sellStrategyIdProxy = computed({
  get: () => props.sellStrategyId,
  set: (value) => emit('update:sellStrategyId', value)
})

const metricText = (value, digits = 2) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return props.formatNumber(num, digits)
}

const pctText = (value, digits = 2) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return `${props.formatNumber(num * 100, digits)}%`
}

const runQuickAnalysis = () => {
  const first = String(props.backtestForm?.symbols || '')
    .split(/[\s,;]+/)
    .map((item) => item.trim())
    .filter(Boolean)[0]
  if (!first) return
  props.applySymbolToAnalysis(first)
}
</script>
