<template>
  <div class="panel strategy-side">
    <header class="panel-title">
      <div>
        <h2>参数交叉验证</h2>
        <p class="muted">多参数组合网格寻优。</p>
      </div>
      <span class="pill">寻优</span>
    </header>
    <p class="panel-note">结果里的最佳参数可一键回填到回测；寻优范围越大运行越久。</p>
    <div class="toolbar strategy-merge-toggle">
      <label class="toggle">
        <input type="checkbox" v-model="gridUseBacktestBaseProxy" />
        <span>复用回测基础参数（市场、标的、资金、日期、年数）</span>
      </label>
    </div>
    <div class="toolbar strategy-merge-toggle">
      <label class="toggle">
        <input type="checkbox" v-model="gridExploreAllStrategiesProxy" />
        <span>自动探索全部买卖策略组合（用于筛选最优组合）</span>
      </label>
    </div>
    <div v-if="gridUseBacktestBaseProxy" class="selection strategy-shared-summary">
      <div class="selection-head">
        <strong>当前共用回测基础参数</strong>
      </div>
      <div class="result-grid">
        <div><p class="muted">市场</p><p class="mono">{{ backtestForm.market || '-' }}</p></div>
        <div><p class="muted">标的</p><p class="mono">{{ formatSymbolText(backtestForm.symbols, backtestForm.market) }}</p></div>
        <div><p class="muted">初始资金</p><p class="mono">{{ formatNumber(backtestForm.cash, 0) }}</p></div>
        <div><p class="muted">开始/结束</p><p class="mono">{{ backtestForm.start || '-' }} / {{ backtestForm.end || '-' }}</p></div>
        <div><p class="muted">回溯年数</p><p class="mono">{{ backtestForm.n_folds ?? '-' }}</p></div>
      </div>
    </div>
    <div class="form-grid">
      <div v-if="!gridUseBacktestBaseProxy">
        <label class="label">标的列表</label>
        <input v-model="gridForm.symbols" placeholder="600036, 000001" />
      </div>
      <div v-if="!gridUseBacktestBaseProxy">
        <label class="label">初始资金</label>
        <input v-model.number="gridForm.cash" type="number" min="1000" />
      </div>
      <div v-if="!gridUseBacktestBaseProxy">
        <label class="label">开始日期</label>
        <input v-model="gridForm.start" type="date" />
      </div>
      <div v-if="!gridUseBacktestBaseProxy">
        <label class="label">结束日期</label>
        <input v-model="gridForm.end" type="date" />
      </div>
      <div>
        <label class="label">买入策略</label>
        <select v-model="buyStrategyIdProxy" class="select">
          <option v-for="item in buyStrategies" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
      </div>
      <div>
        <label class="label">卖出策略</label>
        <select v-model="sellStrategyIdProxy" class="select">
          <option v-for="item in sellStrategies" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
      </div>
      <div>
        <label class="label">买入策略列表</label>
        <input v-model="gridForm.buy_strategies" placeholder="breakout, macd_cross" />
      </div>
      <div>
        <label class="label">卖出策略列表</label>
        <input v-model="gridForm.sell_strategies" placeholder="atr_stop, macd_cross" />
      </div>
      <div v-for="param in (activeBuyStrategy?.params || [])" :key="`grid-buy-${param.key}`">
        <label class="label">{{ param.label }}列表</label>
        <input v-model="gridBuyParamLists[param.key]" type="text" :placeholder="param.type === 'bool' ? 'true,false' : '20, 42, 60'" />
      </div>
      <div v-for="param in (activeSellStrategy?.params || [])" :key="`grid-sell-${param.key}`">
        <label class="label">{{ param.label }}列表</label>
        <input v-model="gridSellParamLists[param.key]" type="text" :placeholder="param.type === 'bool' ? 'true,false' : '0.5, 1.0'" />
      </div>
      <div>
        <label class="label">验证模式</label>
        <select v-model="gridForm.validation_mode" class="select">
          <option value="none">不启用</option>
          <option value="holdout">训练/验证切分</option>
          <option value="walk_forward">滚动验证</option>
        </select>
      </div>
      <div>
        <label class="label">训练比例</label>
        <input v-model.number="gridForm.train_ratio" type="number" min="0.5" max="0.9" step="0.05" />
      </div>
      <div v-if="gridForm.validation_mode === 'walk_forward'">
        <label class="label">滚动窗口天数</label>
        <input v-model.number="gridForm.walk_forward_days" type="number" min="60" />
      </div>
      <div v-if="gridForm.validation_mode === 'walk_forward'">
        <label class="label">滚动步长天数</label>
        <input v-model.number="gridForm.walk_forward_step_days" type="number" min="30" />
      </div>
      <div>
        <label class="label">最大运行次数</label>
        <input v-model.number="gridForm.max_runs" type="number" min="1" />
      </div>
      <div>
        <label class="label">排序指标</label>
        <select v-model="gridForm.ranking_metric" class="select">
          <option value="profit">累计收益优先</option>
          <option value="win_rate">胜率优先</option>
          <option value="sharpe">夏普优先</option>
          <option value="annual_return">年化收益优先</option>
          <option value="custom">自定义指标</option>
        </select>
      </div>
      <div v-if="gridForm.ranking_metric === 'custom'"><label class="label">自定义: 收益权重</label><input v-model.number="gridForm.ranking_weights.profit" type="number" min="0" step="0.1" /></div>
      <div v-if="gridForm.ranking_metric === 'custom'"><label class="label">自定义: 胜率权重</label><input v-model.number="gridForm.ranking_weights.win_rate" type="number" min="0" step="0.1" /></div>
      <div v-if="gridForm.ranking_metric === 'custom'"><label class="label">自定义: 夏普权重</label><input v-model.number="gridForm.ranking_weights.sharpe" type="number" min="0" step="0.1" /></div>
      <div v-if="gridForm.ranking_metric === 'custom'"><label class="label">自定义: 年化权重</label><input v-model.number="gridForm.ranking_weights.annual_return" type="number" min="0" step="0.1" /></div>
      <div v-if="gridForm.ranking_metric === 'custom'"><label class="label">自定义: 回撤惩罚</label><input v-model.number="gridForm.ranking_weights.drawdown" type="number" min="0" step="0.1" /></div>
      <div><label class="label">前N股票数量</label><input v-model.number="gridForm.symbol_top_n" type="number" min="1" max="50" /></div>
      <div><label class="label">股票评估上限</label><input v-model.number="gridForm.symbol_eval_limit" type="number" min="10" max="20000" /></div>
      <div v-if="!gridUseBacktestBaseProxy"><label class="label">回溯年数</label><input v-model.number="gridForm.n_folds" type="number" min="1" /></div>
    </div>
    <div class="toolbar">
      <button class="btn-secondary" @click="runGridSearch" :disabled="actionsBusy">启动寻优</button>
      <span class="muted">输出最佳参数组合</span>
    </div>

    <div v-if="gridSummary" class="result-card">
      <h3>最佳组合</h3>
      <div class="toolbar">
        <button class="btn-secondary" @click="applyGridToBacktest">应用到回测参数</button>
        <button v-if="gridNextParamSuggestions" class="btn-secondary" @click="applyGridNextSuggestions">生成下一轮参数组合</button>
        <span class="muted">自动填充买入周期/止损/止盈</span>
      </div>
      <div v-if="gridDiagnostics" class="info-card">
        <div class="result-grid">
          <div><p class="muted">候选组合</p><p class="mono">{{ gridDiagnostics.candidate_runs ?? '-' }}</p></div>
          <div><p class="muted">已测试组合</p><p class="mono">{{ gridDiagnostics.tested_runs ?? '-' }}</p></div>
          <div><p class="muted">是否完整测试</p><p class="mono">{{ gridDiagnostics.fully_tested ? '是' : '否' }}</p></div>
          <div><p class="muted">是否被截断</p><p class="mono">{{ gridDiagnostics.truncated ? '是' : '否' }}</p></div>
          <div><p class="muted">报错组合数</p><p class="mono">{{ gridDiagnostics.error_count ?? 0 }}</p></div>
        </div>
      </div>
      <div v-if="gridRecommendation" class="info-card">
        <p class="muted">推荐操作模式</p>
        <p class="metric-value">{{ gridRecommendation.mode || '-' }}</p>
        <p class="muted">建议策略：{{ gridRecommendation.buy_strategy || '-' }} / {{ gridRecommendation.sell_strategy || '-' }}</p>
        <p class="muted">建议仓位区间：{{ gridRecommendation.position_range || '-' }}</p>
        <p class="muted" v-if="gridRecommendation.notes?.length">{{ gridRecommendation.notes.join('；') }}</p>
      </div>
      <div class="info-card">
        <div class="result-grid">
          <div><p class="muted">净收益</p><p class="metric-value">{{ metricText(metricOf(gridSummary, 'profit_sum')) }}</p></div>
          <div><p class="muted">毛收益估算</p><p class="metric-value">{{ metricText(metricOf(gridSummary, 'estimated_gross_profit_sum')) }}</p></div>
          <div><p class="muted">年化收益</p><p class="metric-value">{{ pctText(metricOf(gridSummary, 'annual_return')) }}</p></div>
          <div><p class="muted">夏普 / Sortino</p><p class="metric-value">{{ metricText(metricOf(gridSummary, 'sharpe'), 2) }} / {{ metricText(metricOf(gridSummary, 'sortino'), 2) }}</p></div>
          <div><p class="muted">Calmar / 回撤</p><p class="metric-value">{{ metricText(metricOf(gridSummary, 'calmar'), 2) }} / {{ pctText(metricOf(gridSummary, 'max_drawdown')) }}</p></div>
          <div><p class="muted">总成本估算</p><p class="metric-value">{{ metricText(metricOf(gridSummary, 'estimated_total_cost')) }}</p></div>
        </div>
      </div>
      <div v-if="gridErrors?.length" class="info-card">
        <p class="muted">寻优报错样本（最多展示 {{ gridErrors.length }} 条）</p>
        <div class="code-wrap"><pre class="code">{{ JSON.stringify(gridErrors, null, 2) }}</pre></div>
      </div>
      <pre class="code">{{ gridSummaryText }}</pre>
    </div>

    <div v-if="gridTopSymbols?.length" class="result-card">
      <h3>最佳组合股票榜单（前 {{ gridTopSymbols.length }}）</h3>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>#</th><th>标的</th><th>胜率</th><th>累计盈亏</th><th>夏普</th><th>Sortino</th><th>回撤</th><th>总成本</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="row in gridTopSymbols" :key="`grid-symbol-${row.rank}-${row.symbol}`">
              <td class="mono">{{ row.rank }}</td>
              <td class="mono">{{ formatSelectedSymbol(row.symbol, backtestForm.market) }}</td>
              <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
              <td class="mono">{{ formatNumber(row.profit_sum) }}</td>
              <td class="mono">{{ formatNumber(row.sharpe, 2) }}</td>
              <td class="mono">{{ formatNumber(row.sortino, 2) }}</td>
              <td class="mono">{{ formatNumber(row.max_drawdown, 3) }}</td>
              <td class="mono">{{ formatNumber(row.estimated_total_cost) }}</td>
              <td><button class="btn-secondary" @click="applySymbolToBacktest(row.symbol)">用于回测</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="gridActionableCandidates?.length" class="result-card">
      <h3>近期可操作候选（最佳组合）</h3>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>标的</th><th>建议动作</th><th>建议仓位</th><th>胜率</th><th>止损/止盈</th><th>原因</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="row in gridActionableCandidates" :key="`grid-action-${row.symbol}`">
              <td class="mono">{{ formatSelectedSymbol(row.symbol, backtestForm.market) }}</td>
              <td>{{ row.action }}</td>
              <td class="mono">{{ row.position_range }}</td>
              <td class="mono">{{ formatNumber(row.win_rate, 1) }}%</td>
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

    <div v-if="gridTopRuns?.length" class="result-card">
      <h3>策略组合榜单（前 {{ gridTopRuns.length }}）</h3>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>#</th><th>买入</th><th>卖出</th><th>收益</th><th>胜率</th><th>Sortino</th><th>回撤</th><th>评分</th><th>参数</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="row in gridTopRuns" :key="`grid-top-${row.rank}`">
              <td class="mono">{{ row.rank }}</td>
              <td class="mono">{{ row.buy_strategy }}</td>
              <td class="mono">{{ row.sell_strategy }}</td>
              <td class="mono">{{ formatNumber(metricOf(row, 'profit_sum')) }}</td>
              <td class="mono">{{ formatNumber(metricOf(row, 'win_rate'), 1) }}%</td>
              <td class="mono">{{ formatNumber(metricOf(row, 'sortino'), 2) }}</td>
              <td class="mono">{{ formatNumber(metricOf(row, 'max_drawdown'), 3) }}</td>
              <td class="mono">{{ formatNumber(row.score, 2) }}</td>
              <td class="mono params-cell">{{ paramsBrief(row) }}</td>
              <td><button class="btn-secondary" @click="applyGridRunToBacktest(row)">应用</button></td>
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
  gridForm: Object,
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
  runGridSearch: Function,
  actionsBusy: Boolean,
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
  formatNumber: Function
})

const emit = defineEmits([
  'update:buyStrategyId',
  'update:sellStrategyId',
  'update:gridUseBacktestBase',
  'update:gridExploreAllStrategies'
])

const buyStrategyIdProxy = computed({
  get: () => props.buyStrategyId,
  set: (value) => emit('update:buyStrategyId', value)
})
const sellStrategyIdProxy = computed({
  get: () => props.sellStrategyId,
  set: (value) => emit('update:sellStrategyId', value)
})
const gridUseBacktestBaseProxy = computed({
  get: () => !!props.gridUseBacktestBase,
  set: (value) => emit('update:gridUseBacktestBase', value)
})
const gridExploreAllStrategiesProxy = computed({
  get: () => !!props.gridExploreAllStrategies,
  set: (value) => emit('update:gridExploreAllStrategies', value)
})

const metricOf = (row, key) => {
  if (!row) return null
  const validationValue = row[`validation_${key}`]
  if (validationValue !== undefined && validationValue !== null) return Number(validationValue)
  if (row[key] !== undefined && row[key] !== null) return Number(row[key])
  return null
}
const paramsBrief = (row) => {
  const buy = row?.buy_params ? Object.entries(row.buy_params).map(([k, v]) => `B.${k}:${v}`) : []
  const sell = row?.sell_params ? Object.entries(row.sell_params).map(([k, v]) => `S.${k}:${v}`) : []
  const merged = [...buy, ...sell]
  if (!merged.length) return '-'
  return merged.join(', ')
}
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
</script>
