<template>
  <section class="panel" v-show="active">
    <header class="panel-title">
      <div>
        <h2>ML 模型引擎</h2>
        <p class="muted">特征构建 -> 训练 -> 预测 -> 推荐展示</p>
      </div>
      <span class="pill">ML</span>
    </header>

    <p class="panel-note">
      先确保已完成数据更新，再执行特征构建与训练。预测结果可直接回填到策略回测。
    </p>

    <div class="toolbar">
      <button class="btn-primary" @click="runMlPipeline" :disabled="actionsBusy || mlRunning">
        一键执行
      </button>
      <button class="btn-secondary" @click="refreshMlData" :disabled="actionsBusy || mlRunning || mlLoading">
        刷新模型与预测
      </button>
      <span class="muted" v-if="mlRunning">ML 任务执行中...</span>
    </div>

    <p v-if="mlError" class="error">{{ mlError }}</p>

    <div class="grid grid-2">
      <div class="info-card">
        <h3>1) 特征构建</h3>
        <div class="form-grid">
          <div>
            <label class="label">市场</label>
            <select v-model="mlFeatureForm.market" class="select">
              <option value="SH">SH</option>
              <option value="SZ">SZ</option>
              <option value="300">300</option>
              <option value="CN">CN</option>
            </select>
          </div>
          <div>
            <label class="label">标的列表</label>
            <input v-model="mlFeatureForm.symbols" placeholder="sz300249, sz300750" />
          </div>
          <div>
            <label class="label">特征版本</label>
            <input v-model="mlFeatureForm.feature_version" />
          </div>
          <div>
            <label class="label">最小K线行数</label>
            <input v-model.number="mlFeatureForm.min_rows" type="number" min="60" />
          </div>
          <div>
            <label class="label">最大标的数</label>
            <input v-model.number="mlFeatureForm.symbol_limit" type="number" min="10" max="2000" />
          </div>
          <div>
            <label class="label">开始日期</label>
            <input v-model="mlFeatureForm.start" type="date" />
          </div>
          <div>
            <label class="label">结束日期</label>
            <input v-model="mlFeatureForm.end" type="date" />
          </div>
        </div>
        <div class="toolbar">
          <button class="btn-secondary" @click="runMlFeatureBuild" :disabled="actionsBusy || mlRunning">
            构建特征
          </button>
        </div>
        <div v-if="mlFeatureResult" class="code-wrap">
          <pre class="code">{{ JSON.stringify(mlFeatureResult, null, 2) }}</pre>
        </div>
      </div>

      <div class="info-card">
        <h3>2) 训练模型</h3>
        <div class="form-grid">
          <div>
            <label class="label">市场</label>
            <select v-model="mlTrainForm.market" class="select">
              <option value="SH">SH</option>
              <option value="SZ">SZ</option>
              <option value="300">300</option>
              <option value="CN">CN</option>
            </select>
          </div>
          <div>
            <label class="label">目标</label>
            <input v-model="mlTrainForm.target" />
          </div>
          <div>
            <label class="label">特征版本</label>
            <input v-model="mlTrainForm.feature_version" />
          </div>
          <div>
            <label class="label">训练比例</label>
            <input v-model.number="mlTrainForm.train_ratio" type="number" min="0.6" max="0.95" step="0.01" />
          </div>
          <div>
            <label class="label">最大样本</label>
            <input v-model.number="mlTrainForm.max_samples" type="number" min="1000" max="1000000" />
          </div>
          <div>
            <label class="label">模型名称</label>
            <input v-model="mlTrainForm.model_name" placeholder="hgb_300_v1" />
          </div>
          <div>
            <label class="label">max_iter</label>
            <input v-model.number="mlTrainForm.max_iter" type="number" min="50" />
          </div>
          <div>
            <label class="label">learning_rate</label>
            <input v-model.number="mlTrainForm.learning_rate" type="number" min="0.001" step="0.001" />
          </div>
          <div>
            <label class="label">max_depth</label>
            <input v-model.number="mlTrainForm.max_depth" type="number" min="2" />
          </div>
          <div>
            <label class="label">min_samples_leaf</label>
            <input v-model.number="mlTrainForm.min_samples_leaf" type="number" min="5" />
          </div>
          <div>
            <label class="label">l2_regularization</label>
            <input v-model.number="mlTrainForm.l2_regularization" type="number" min="0" step="0.001" />
          </div>
        </div>
        <div class="toolbar">
          <button class="btn-secondary" @click="runMlTrain" :disabled="actionsBusy || mlRunning">
            训练模型
          </button>
        </div>
        <div v-if="mlTrainResult" class="code-wrap">
          <pre class="code">{{ JSON.stringify(mlTrainResult, null, 2) }}</pre>
        </div>
      </div>
    </div>

    <div class="grid grid-2">
      <div class="info-card">
        <h3>3) 生成预测</h3>
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
            <label class="label">模型ID（可选）</label>
            <input v-model.number="mlPredictForm.model_id" type="number" min="1" />
          </div>
          <div>
            <label class="label">标的列表（可选）</label>
            <input v-model="mlPredictForm.symbols" placeholder="sz300249, sz300750" />
          </div>
          <div>
            <label class="label">输出条数</label>
            <input v-model.number="mlPredictForm.limit" type="number" min="1" max="500" />
          </div>
        </div>
        <div class="toolbar">
          <button class="btn-secondary" @click="runMlPredict" :disabled="actionsBusy || mlRunning">
            生成预测
          </button>
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
                <th>状态</th>
                <th>AUC</th>
                <th>准确率</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in mlModels" :key="m.id">
                <td class="mono">#{{ m.id }}</td>
                <td>{{ m.name }}</td>
                <td>
                  <span :class="['status', m.is_active ? 'status-succeeded' : 'status-queued']">
                    {{ m.is_active ? 'active' : (m.status || 'trained') }}
                  </span>
                </td>
                <td class="mono">{{ formatMetric(m.metrics?.auc) }}</td>
                <td class="mono">{{ formatMetric(m.metrics?.accuracy) }}</td>
                <td>
                  <button class="btn-secondary" @click="promoteMlModel(m.id)" :disabled="m.is_active || actionsBusy || mlRunning">
                    设为当前模型
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="muted">暂无模型</p>
      </div>
    </div>

    <div class="info-card">
      <h3>4) 推荐展示（最新预测）</h3>
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
                <button class="btn-secondary" @click="applyPredictionToBacktest(row.symbol)">
                  用于回测
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="muted">暂无预测结果</p>
    </div>
  </section>
</template>

<script setup>
defineProps({
  active: Boolean,
  actionsBusy: Boolean,
  mlRunning: Boolean,
  mlLoading: Boolean,
  mlError: String,
  mlFeatureForm: Object,
  mlTrainForm: Object,
  mlPredictForm: Object,
  mlFeatureResult: Object,
  mlTrainResult: Object,
  mlPredictResult: Object,
  mlModels: Array,
  mlPredictions: Array,
  runMlFeatureBuild: Function,
  runMlTrain: Function,
  runMlPredict: Function,
  runMlPipeline: Function,
  refreshMlData: Function,
  promoteMlModel: Function,
  applyPredictionToBacktest: Function
})

const formatMetric = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(4)
}
</script>

