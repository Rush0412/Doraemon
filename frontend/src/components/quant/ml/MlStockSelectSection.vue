<template>
  <div class="info-card">
    <h3>4. ML + 量化联动选股</h3>
    <p class="panel-note">4 是“ML 初筛 + 当前量化策略复筛”的可执行候选，不等于 5 的纯 ML 概率榜。若 5 分数更高却没进 4，通常是被量化策略门槛、评估范围或 K 线覆盖淘汰。</p>
    <div class="form-grid">
      <div>
        <label class="label">市场</label>
        <select v-model="mlSelectForm.market" class="select">
          <option value="SH">SH</option>
          <option value="SZ">SZ</option>
          <option value="300">300</option>
          <option value="CN">CN</option>
        </select>
      </div>
      <div>
        <label class="label">目标</label>
        <input v-model="mlSelectForm.target" />
      </div>
      <div>
        <label class="label">模型 ID</label>
        <input v-model.number="mlSelectForm.model_id" type="number" min="1" placeholder="留空自动选最优市场模型" />
      </div>
      <div>
        <label class="label">限制标的</label>
        <input v-model="mlSelectForm.symbols" placeholder="留空表示当前市场全量候选" />
      </div>
      <div>
        <label class="label">最小分数</label>
        <input v-model.number="mlSelectForm.min_score" type="number" min="0" max="1" step="0.01" />
      </div>
      <div>
        <label class="label">预测池大小</label>
        <input v-model.number="mlSelectForm.prediction_limit" type="number" min="20" max="50000" />
      </div>
      <div>
        <label class="label">候选池大小</label>
        <input v-model.number="mlSelectForm.candidate_limit" type="number" min="10" max="50000" />
      </div>
      <div>
        <label class="label">输出 TopN</label>
        <input v-model.number="mlSelectForm.symbol_top_n" type="number" min="1" max="100" />
      </div>
      <div>
        <label class="label">评估上限</label>
        <input v-model.number="mlSelectForm.symbol_eval_limit" type="number" min="10" max="50000" />
      </div>
      <div>
        <label class="label">最少 K 线</label>
        <input v-model.number="mlSelectForm.min_kline_rows" type="number" min="60" max="2000" />
      </div>
    </div>
    <div class="toolbar">
      <button class="btn-secondary" @click="runMlStockSelect" :disabled="actionsBusy || mlRunning">联动选股</button>
    </div>

    <p v-if="mlSelectResult?.summary?.warning" class="muted">{{ mlSelectResult.summary.warning }}</p>
    <p v-if="mlSelectResult?.diagnostics?.filter_warning && mlSelectResult?.diagnostics?.filter_warning !== mlSelectResult?.summary?.warning" class="muted">{{ mlSelectResult.diagnostics.filter_warning }}</p>
    <p v-if="mlSelectResult?.diagnostics?.model_warning && mlSelectResult?.diagnostics?.model_warning !== mlSelectResult?.summary?.warning" class="muted">{{ mlSelectResult.diagnostics.model_warning }}</p>

    <div v-if="mlSelectResult?.summary" class="result-card">
      <div class="result-grid">
        <div>
          <p class="muted">模型</p>
          <p class="metric-value">{{ formatModelLabel(mlSelectResult.summary) }}</p>
        </div>
        <div>
          <p class="muted">模型范围</p>
          <p class="metric-value">{{ formatModelScope(mlSelectResult.summary.model_scope) }}</p>
        </div>
        <div>
          <p class="muted">模型覆盖标的</p>
          <p class="metric-value">{{ formatCount(mlSelectResult.summary.model_symbol_count) }}</p>
        </div>
        <div>
          <p class="muted">打分股票</p>
          <p class="metric-value">{{ mlSelectResult.diagnostics?.rows_scored || 0 }}</p>
        </div>
        <div>
          <p class="muted">ML 候选</p>
          <p class="metric-value">{{ mlSelectResult.summary.ml_candidates || 0 }}</p>
        </div>
        <div>
          <p class="muted">量化评估</p>
          <p class="metric-value">{{ mlSelectResult.summary.evaluated_symbols || 0 }}</p>
        </div>
        <div>
          <p class="muted">可买候选</p>
          <p class="metric-value">{{ mlSelectResult.summary.buy_candidates || 0 }}</p>
        </div>
        <div>
          <p class="muted">筛选模式</p>
          <p class="metric-value">{{ mlSelectResult.diagnostics?.filter_mode || 'strict' }}</p>
        </div>
        <div>
          <p class="muted">净收益</p>
          <p class="metric-value">{{ formatNumberMetric(mlSelectResult.summary.profit_sum) }}</p>
        </div>
        <div>
          <p class="muted">毛收益估算</p>
          <p class="metric-value">{{ formatNumberMetric(mlSelectResult.summary.estimated_gross_profit_sum) }}</p>
        </div>
        <div>
          <p class="muted">年化收益</p>
          <p class="metric-value">{{ formatPercentMetric(mlSelectResult.summary.annual_return) }}</p>
        </div>
        <div>
          <p class="muted">夏普 / Sortino</p>
          <p class="metric-value">
            {{ formatNumberMetric(mlSelectResult.summary.sharpe) }} / {{ formatNumberMetric(mlSelectResult.summary.sortino) }}
          </p>
        </div>
        <div>
          <p class="muted">Calmar / 回撤</p>
          <p class="metric-value">
            {{ formatNumberMetric(mlSelectResult.summary.calmar) }} / {{ formatPercentMetric(mlSelectResult.summary.max_drawdown) }}
          </p>
        </div>
        <div>
          <p class="muted">总成本估算</p>
          <p class="metric-value">{{ formatNumberMetric(mlSelectResult.summary.estimated_total_cost) }}</p>
        </div>
      </div>
    </div>

    <div class="table-wrap" v-if="mlSelectResult?.buy_candidates?.length">
      <table class="table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>ML 动作</th>
            <th>上涨概率</th>
            <th>预期收益(5d)</th>
            <th>量化动作</th>
            <th>仓位</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in mlSelectResult.buy_candidates" :key="`ml-select-${row.symbol}`">
            <td class="mono">{{ row.symbol }}</td>
            <td>{{ row.ml_action || '-' }}</td>
            <td class="mono">{{ formatMetric(row.score_up_5d) }}</td>
            <td class="mono">{{ formatMetric(row.expected_ret_5d) }}</td>
            <td>{{ row.action || '-' }}</td>
            <td class="mono">{{ row.position_range || '-' }}</td>
            <td>
              <div class="table-actions">
                <button class="btn-secondary" @click="applyPredictionToPool(row.symbol)">加入自选</button>
                <button class="btn-secondary" @click="applyPredictionToBacktest(row.symbol)">用于回测</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="table-wrap" v-if="mlSelectResult?.excluded_ml_candidates?.length">
      <h4>高分 ML 但未入选原因</h4>
      <table class="table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>上涨概率</th>
            <th>预期收益(5D)</th>
            <th>量化动作</th>
            <th>未入选原因</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in mlSelectResult.excluded_ml_candidates" :key="`ml-excluded-${row.symbol}`">
            <td class="mono">{{ row.symbol }}</td>
            <td class="mono">{{ formatMetric(row.score_up_5d) }}</td>
            <td class="mono">{{ formatMetric(row.expected_ret_5d) }}</td>
            <td>{{ row.quant_action || '-' }}</td>
            <td>{{ row.reason || row.reason_code || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else-if="mlSelectResult" class="muted">当前没有同时满足 ML 与量化条件的候选股。</p>
  </div>
</template>

<script setup>
import {
  formatCount,
  formatMetric,
  formatModelLabel,
  formatModelScope,
  formatNumberMetric,
  formatPercentMetric
} from './formatters'

defineProps({
  actionsBusy: Boolean,
  mlRunning: Boolean,
  mlSelectForm: Object,
  mlSelectResult: Object,
  runMlStockSelect: Function,
  applyPredictionToBacktest: Function,
  applyPredictionToPool: Function
})
</script>
