<template>
  <section class="grid grid-2 trend-layout" v-show="active">
    <div class="panel glass">
      <header class="panel-title">
        <div>
          <h2>走势分析预留模块</h2>
          <p class="muted">上传 K 线截图元数据并录入结构化特征，完成未来走势分析 Demo 联调。</p>
        </div>
        <span class="pill">Trend Lab</span>
      </header>
      <p class="panel-note">
        当前为架构预留版：前端已支持图片选择、特征录入与结果展示，后端已提供标准 Demo
        契约，后续可直接接入真实文件上传、特征工程和模型推理服务。
      </p>
      <div class="form-grid">
        <div>
          <label class="label">市场</label>
          <select v-model="trendForm.market" class="select">
            <option value="CN">CN (A 股)</option>
            <option value="SH">SH (上证)</option>
            <option value="SZ">SZ (深证)</option>
            <option value="US">US (美股)</option>
            <option value="HK">HK (港股)</option>
          </select>
        </div>
        <div>
          <label class="label">标的代码</label>
          <input v-model="trendForm.symbol" placeholder="600036 / AAPL / 0700.HK" />
        </div>
        <div>
          <label class="label">预测周期</label>
          <select v-model.number="trendForm.horizon_days" class="select">
            <option :value="3">3 天</option>
            <option :value="5">5 天</option>
            <option :value="10">10 天</option>
            <option :value="20">20 天</option>
          </select>
        </div>
        <div>
          <label class="label">备注</label>
          <input v-model="trendForm.note" placeholder="记录图形形态、事件驱动或行业背景" />
        </div>
      </div>

      <div class="trend-upload">
        <div class="trend-upload-card">
          <label class="label">K 线截图</label>
          <input type="file" accept="image/*" @change="handleTrendImageChange" />
          <p class="muted">当前 Demo 发送图片元数据，不直接上传二进制文件。</p>
          <div v-if="trendImageMeta" class="meta-list">
            <p class="muted">文件名：{{ trendImageMeta.name }}</p>
            <p class="muted">类型：{{ trendImageMeta.type || 'unknown' }}</p>
            <p class="muted">大小：{{ trendImageMeta.sizeKb }} KB</p>
          </div>
          <div class="toolbar">
            <button class="btn-secondary" @click="clearTrendImage" :disabled="!trendImageMeta">清除图片</button>
          </div>
        </div>
        <div class="trend-upload-card">
          <label class="label">特征 JSON</label>
          <textarea
            :value="trendFeatureInput"
            rows="12"
            class="textarea"
            placeholder='[{"trade_date":"2026-05-20","close":12.31,"ma5":12.12,"ma20":11.84,"rsi14":61.2,"macd":0.18}]'
            @input="emit('update:trendFeatureInput', $event.target.value)"
          />
          <p class="muted">建议至少提供 `close`、`ma5`、`ma20`、`rsi14`、`macd` 等关键特征。</p>
        </div>
      </div>

      <div v-if="trendImagePreview" class="trend-preview">
        <img :src="trendImagePreview" alt="trend preview" />
      </div>

      <div class="toolbar">
        <button class="btn-primary" @click="runTrendDemo" :disabled="trendBusy">运行 Demo</button>
        <button class="btn-secondary" @click="applySymbolToBacktest(trendForm.symbol)" :disabled="!trendForm.symbol">
          用于回测
        </button>
        <span class="muted">{{ trendBusy ? '分析中...' : 'Demo 模式返回结构化建议与扩展架构' }}</span>
      </div>

      <p v-if="trendError" class="error">{{ trendError }}</p>
    </div>

    <div class="panel glass">
      <header class="panel-title">
        <div>
          <h2>分析结果</h2>
          <p class="muted">输出方向判断、置信度、输入摘要与后续接入能力。</p>
        </div>
        <span class="pill">Result</span>
      </header>

      <div v-if="trendDemoResult" class="trend-results">
        <div class="result-grid">
          <div class="metric-card">
            <p class="metric-label">方向</p>
            <p class="metric-value">{{ trendDemoResult.analysis?.direction || '-' }}</p>
          </div>
          <div class="metric-card">
            <p class="metric-label">置信度</p>
            <p class="metric-value">{{ trendDemoResult.analysis?.confidence ?? '-' }}</p>
          </div>
          <div class="metric-card">
            <p class="metric-label">预测周期</p>
            <p class="metric-value">{{ trendDemoResult.forecast_horizon_days || '-' }}d</p>
          </div>
          <div class="metric-card">
            <p class="metric-label">特征行数</p>
            <p class="metric-value">{{ trendDemoResult.feature_summary?.rows || 0 }}</p>
          </div>
        </div>

        <div class="result-card">
          <h3>建议动作</h3>
          <p>{{ trendDemoResult.recommendation?.action }}</p>
          <p class="muted" v-if="trendDemoResult.recommendation?.note">
            备注：{{ trendDemoResult.recommendation.note }}
          </p>
        </div>

        <div class="result-card">
          <h3>信号说明</h3>
          <div class="selection-chips">
            <span v-for="signal in trendDemoResult.analysis?.signals || []" :key="signal" class="chip chip-static">
              {{ signal }}
            </span>
          </div>
        </div>

        <div class="result-card">
          <h3>输入摘要</h3>
          <p class="muted">
            日期范围：
            {{ trendDemoResult.feature_summary?.date_range?.start || '-' }}
            至
            {{ trendDemoResult.feature_summary?.date_range?.end || '-' }}
          </p>
          <div class="selection-chips">
            <span
              v-for="feature in trendDemoResult.feature_summary?.feature_columns || []"
              :key="feature"
              class="chip chip-static"
            >
              {{ feature }}
            </span>
          </div>
        </div>

        <div class="result-card">
          <h3>扩展架构</h3>
          <p class="muted">契约版本：{{ trendDemoResult.architecture?.data_contract_version || '-' }}</p>
          <div class="selection-chips">
            <span
              v-for="capability in trendDemoResult.architecture?.next_stage_capabilities || []"
              :key="capability"
              class="chip chip-static"
            >
              {{ capability }}
            </span>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <h3>等待趋势分析输入</h3>
        <p class="muted">录入图片元数据或结构化特征后，即可得到 Demo 结果与后续扩展建议。</p>
      </div>
    </div>
  </section>
</template>

<script setup>
const props = defineProps({
  active: { type: Boolean, default: false },
  trendForm: { type: Object, required: true },
  trendFeatureInput: { type: String, default: '' },
  trendDemoResult: { type: Object, default: null },
  trendBusy: { type: Boolean, default: false },
  trendError: { type: String, default: '' },
  trendImagePreview: { type: String, default: '' },
  trendImageMeta: { type: Object, default: null },
  handleTrendImageChange: { type: Function, required: true },
  clearTrendImage: { type: Function, required: true },
  runTrendDemo: { type: Function, required: true },
  applySymbolToBacktest: { type: Function, required: true }
})

const emit = defineEmits(['update:trendFeatureInput'])

const handleTrendImageChange = (event) => props.handleTrendImageChange(event)
const clearTrendImage = () => props.clearTrendImage()
const runTrendDemo = () => props.runTrendDemo()
const applySymbolToBacktest = (symbol) => props.applySymbolToBacktest(symbol)
</script>
