<template>
  <section class="panel" v-show="active">
    <header class="panel-title">
      <div>
        <h2>ML 模型引擎</h2>
        <p class="muted">支持特征构建、训练、预测，以及 ML + 量化联动选股。</p>
      </div>
      <span class="pill">ML</span>
    </header>

    <p class="panel-note">大模型按市场分别维护。`SH`、`SZ`、`300` 建议各自单独训练，选股时会优先匹配同市场模型。</p>

    <div class="toolbar">
      <button class="btn-primary" @click="runMlPipeline" :disabled="actionsBusy || mlRunning">一键执行</button>
      <button class="btn-secondary" @click="runMarketModelPipeline('SH')" :disabled="actionsBusy || mlRunning">
        训练 SH 大模型
      </button>
      <button class="btn-secondary" @click="runMarketModelPipeline('SZ')" :disabled="actionsBusy || mlRunning">
        训练 SZ 大模型
      </button>
      <button class="btn-secondary" @click="runMarketModelPipeline('300')" :disabled="actionsBusy || mlRunning">
        训练 300 大模型
      </button>
      <button class="btn-secondary" @click="refreshMlData" :disabled="actionsBusy || mlRunning || mlLoading">
        刷新模型与预测
      </button>
      <span class="muted" v-if="mlRunning">ML 任务执行中...</span>
    </div>

    <p v-if="mlError" class="error">{{ mlError }}</p>

    <div class="grid grid-2">
      <div class="info-card">
        <h3>1. 特征构建</h3>
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
            <input v-model="mlFeatureForm.symbols" placeholder="留空表示当前市场全量训练" />
          </div>
          <div>
            <label class="label">特征版本</label>
            <input v-model="mlFeatureForm.feature_version" />
          </div>
          <div>
            <label class="label">最少 K 线</label>
            <input v-model.number="mlFeatureForm.min_rows" type="number" min="60" />
          </div>
          <div>
            <label class="label">最大标的数</label>
            <input v-model.number="mlFeatureForm.symbol_limit" type="number" min="10" max="10000" />
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
          <button class="btn-secondary" @click="runMlFeatureBuild" :disabled="actionsBusy || mlRunning">构建特征</button>
        </div>
        <div v-if="mlFeatureResult" class="code-wrap">
          <pre class="code">{{ JSON.stringify(mlFeatureResult, null, 2) }}</pre>
        </div>
      </div>

      <div class="info-card">
        <h3>2. 模型训练</h3>
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
            <input v-model="mlTrainForm.model_name" placeholder="market_hgb_300_y_up_5d_v1" />
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
          <button class="btn-secondary" @click="runMlTrain" :disabled="actionsBusy || mlRunning">训练模型</button>
        </div>
        <div v-if="mlTrainResult" class="code-wrap">
          <pre class="code">{{ JSON.stringify(mlTrainResult, null, 2) }}</pre>
        </div>
      </div>
    </div>

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
                      :disabled="actionsBusy || mlRunning || model.scope !== 'market' || Number(model.symbol_count || 0) < 10"
                    >
                      用于预测/选股
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

    <div class="info-card">
      <h3>4. ML + 量化联动选股</h3>
      <p class="panel-note">先用同市场模型给最新特征打分，再按当前量化买卖参数做二次筛选，输出可优先加入自选池的候选股。</p>
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
            <p class="metric-value">#{{ mlSelectResult.summary.model_id }} {{ mlSelectResult.summary.model_name || '' }}</p>
          </div>
          <div>
            <p class="muted">模型范围</p>
            <p class="metric-value">{{ mlSelectResult.summary.model_scope === 'market' ? '市场大模型' : '自定义模型' }}</p>
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
      <p v-else-if="mlSelectResult" class="muted">当前没有同时满足 ML 与量化条件的候选股。</p>
    </div>

    <div class="info-card">
      <h3>5. 最新预测结果</h3>
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
  mlSelectForm: Object,
  mlFeatureResult: Object,
  mlTrainResult: Object,
  mlPredictResult: Object,
  mlSelectResult: Object,
  mlModels: Array,
  mlPredictions: Array,
  runMlFeatureBuild: Function,
  runMlTrain: Function,
  runMlPredict: Function,
  runMlStockSelect: Function,
  runMlPipeline: Function,
  runMarketModelPipeline: Function,
  refreshMlData: Function,
  useMlModel: Function,
  promoteMlModel: Function,
  applyPredictionToBacktest: Function,
  applyPredictionToPool: Function
})

const formatMetric = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(4)
}

const formatCount = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num) || num <= 0) return '-'
  return String(num)
}
</script>
