<template>
  <div class="grid grid-2">
    <div class="info-card">
      <h3>3. 生成预测</h3>
      <div class="form-grid">
        <div>
          <label class="label">市场</label>
          <select v-model="mlPredictForm.market" class="select">
            <option value="SH">SH</option>
            <option value="SZ">SZ</option>
            <option value="300">300</option>
            <option value="CN">CN</option>
          </select>
        </div>
        <div>
          <label class="label">目标</label>
          <input v-model="mlPredictForm.target" />
        </div>
        <div>
          <label class="label">模型 ID</label>
          <input v-model.number="mlPredictForm.model_id" type="number" min="1" placeholder="留空自动选最优市场模型" />
        </div>
        <div>
          <label class="label">标的列表</label>
          <input v-model="mlPredictForm.symbols" placeholder="留空表示使用当前市场最新特征" />
        </div>
        <div>
          <label class="label">输出条数</label>
          <input v-model.number="mlPredictForm.limit" type="number" min="1" max="500" />
        </div>
      </div>
      <div class="toolbar">
        <button class="btn-secondary" @click="runMlPredict" :disabled="actionsBusy || mlRunning">生成预测</button>
      </div>
      <div v-if="mlPredictResult" class="code-wrap">
        <pre class="code">{{ JSON.stringify(mlPredictResult, null, 2) }}</pre>
      </div>
    </div>

    <div class="info-card">
      <h3>模型列表</h3>
      <div class="table-wrap" v-if="mlModels?.length">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>市场</th>
              <th>范围</th>
              <th>覆盖标的</th>
              <th>AUC</th>
              <th>准确率</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in mlModels" :key="model.id">
              <td class="mono">#{{ model.id }}</td>
              <td>{{ model.name }}<span v-if="model.is_recommended" class="muted">（推荐）</span></td>
              <td>{{ model.market }}</td>
              <td>{{ model.scope === 'market' ? '市场大模型' : '自定义模型' }}</td>
              <td class="mono">{{ formatCount(model.symbol_count) }}</td>
              <td class="mono">{{ formatMetric(model.metrics?.auc) }}</td>
              <td class="mono">{{ formatMetric(model.metrics?.accuracy) }}</td>
              <td>
                <span :class="['status', model.is_active ? 'status-succeeded' : 'status-queued']">
                  {{ model.is_active ? 'active' : (model.status || 'trained') }}
                </span>
              </td>
              <td>
                <div class="table-actions">
                  <button
                    class="btn-secondary"
                    @click="useMlModel(model)"
                    :disabled="actionsBusy || mlRunning || !model.is_qualified_market_model"
                  >
                    用于预测/选股
                  </button>
                  <button class="btn-secondary" @click="loadModelTrainingParams(model)" :disabled="actionsBusy || mlRunning">
                    带入训练参数
                  </button>
                  <button class="btn-secondary" @click="promoteMlModel(model.id)" :disabled="model.is_active || actionsBusy || mlRunning">
                    设为当前模型
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="muted">暂无模型</p>
    </div>
  </div>
</template>

<script setup>
import { formatCount, formatMetric } from './formatters'

defineProps({
  actionsBusy: Boolean,
  mlRunning: Boolean,
  mlPredictForm: Object,
  mlPredictResult: Object,
  mlModels: Array,
  runMlPredict: Function,
  useMlModel: Function,
  promoteMlModel: Function,
  loadModelTrainingParams: Function
})
</script>
