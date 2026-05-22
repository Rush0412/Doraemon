<template>
  <div class="info-card">
    <h3>5. 最新预测结果</h3>
    <p class="panel-note">5 只按模型分数排序，展示纯 ML 观点，不包含当前量化买卖策略复筛。</p>
    <div class="table-wrap" v-if="mlPredictions?.length">
      <table class="table">
        <thead>
          <tr>
            <th>标的</th>
            <th>日期</th>
            <th>动作</th>
            <th>上涨概率</th>
            <th>预期收益(5d)</th>
            <th>建议仓位</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in mlPredictions" :key="`${row.model_id}-${row.symbol}-${row.trade_date}`">
            <td class="mono">{{ row.symbol }}</td>
            <td class="mono">{{ row.trade_date || '-' }}</td>
            <td>{{ row.action || '-' }}</td>
            <td class="mono">{{ formatMetric(row.score_up_5d) }}</td>
            <td class="mono">{{ formatMetric(row.expected_ret_5d) }}</td>
            <td class="mono">{{ formatMetric(row.position_min) }} ~ {{ formatMetric(row.position_max) }}</td>
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
    <p v-else class="muted">暂无预测结果</p>
  </div>
</template>

<script setup>
import { formatMetric } from './formatters'

defineProps({
  mlPredictions: Array,
  applyPredictionToBacktest: Function,
  applyPredictionToPool: Function
})
</script>
