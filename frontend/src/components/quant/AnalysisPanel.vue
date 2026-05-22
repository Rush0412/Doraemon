<template>
  <section class="panel" v-show="active">
    <header class="panel-title">
      <div>
        <h2>量化分析工具</h2>
        <p class="muted">阻力位、跳空、相关性与涨跌幅分析。</p>
      </div>
      <span class="pill">Tools</span>
    </header>
    <p class="panel-note">工具结果用于解释回测结论：趋势线判断支撑/阻力，相关性用于组合分散，跳空用于风险提示。</p>
    <div class="tool-layout">
      <div class="tool-form">
        <div class="form-grid">
          <div>
            <label class="label">市场</label>
            <select v-model="toolForm.market" class="select">
              <option value="CN">CN (All A Shares)</option>
              <option value="SH">SH (Shanghai)</option>
              <option value="SZ">SZ (Shenzhen)</option>
              <option value="300">300 (ChiNext)</option>
              <option value="US">US</option>
              <option value="HK">HK</option>
            </select>
          </div>
          <div>
            <label class="label">工具类型</label>
            <select v-model="toolForm.tool" class="select">
              <option value="support_resistance">阻力/支撑位分析</option>
              <option value="jump_gap">跳空缺口分析</option>
              <option value="trend_speed">趋势敏感速度对比</option>
              <option value="shift_distance">位移路线比分析</option>
              <option value="regress">线性拟合分析</option>
              <option value="price_channel">价格通道分析</option>
              <option value="golden_ratio">黄金分割分析</option>
              <option value="correlation">相关系数分析</option>
              <option value="distance">距离矩阵分析</option>
              <option value="p_change_stats">涨跌幅统计</option>
              <option value="date_week_wave">交易日波动分析</option>
              <option value="date_week_win">交易日胜率分析</option>
              <option value="bcut_change_vc">涨跌区间分析(固定)</option>
              <option value="qcut_change_vc">涨跌区间分析(分位)</option>
              <option value="wave_change_rate">波动套利指标</option>
            </select>
          </div>
          <div>
            <label class="label">标的列表</label>
            <input v-model="toolForm.symbols" placeholder="600036, 000001" />
          </div>
          <div>
            <label class="label">回溯年数</label>
            <input v-model.number="toolForm.n_folds" type="number" min="1" />
          </div>
          <div>
            <label class="label">返回行数</label>
            <input v-model.number="toolForm.limit" type="number" min="50" />
          </div>
          <div>
            <label class="label">开始日期</label>
            <input v-model="toolForm.start" type="date" />
          </div>
          <div>
            <label class="label">结束日期</label>
            <input v-model="toolForm.end" type="date" />
          </div>
        </div>

        <div class="tool-options" v-if="toolOptionMode === 'support'">
          <label class="label">趋势线范围</label>
          <select v-model="toolOptions.only_last" class="select">
            <option :value="true">仅最近趋势线</option>
            <option :value="false">全部趋势线</option>
          </select>
        </div>

        <div class="tool-options" v-if="toolOptionMode === 'jump'">
          <div class="form-grid">
            <div>
              <label class="label">模式</label>
              <select v-model="toolOptions.mode" class="select">
                <option value="stats">统计模式</option>
                <option value="gap">缺口模式</option>
                <option value="weighted">权重模式</option>
              </select>
            </div>
            <div>
              <label class="label">跳空倍率</label>
              <input v-model.number="toolOptions.jump_diff_factor" type="number" step="0.1" />
            </div>
            <div>
              <label class="label">权重A</label>
              <input v-model.number="toolOptions.weight_a" type="number" step="0.1" />
            </div>
            <div>
              <label class="label">权重B</label>
              <input v-model.number="toolOptions.weight_b" type="number" step="0.1" />
            </div>
            <div>
              <label class="label">强度阈值</label>
              <input v-model.number="toolOptions.power_threshold" type="number" step="0.1" />
            </div>
          </div>
        </div>

        <div class="tool-options" v-if="toolOptionMode === 'trend'">
          <div class="form-grid">
            <div>
              <label class="label">对比基准</label>
              <input v-model="toolOptions.benchmark" placeholder="000001" />
            </div>
            <div>
              <label class="label">重采样</label>
              <input v-model.number="toolOptions.resample" type="number" min="2" />
            </div>
            <div>
              <label class="label">速度字段</label>
              <select v-model="toolOptions.speed_key" class="select">
                <option value="close">close</option>
                <option value="open">open</option>
                <option value="high">high</option>
                <option value="low">low</option>
              </select>
            </div>
          </div>
        </div>

        <div class="tool-options" v-if="toolOptionMode === 'shift'">
          <div class="form-grid">
            <div>
              <label class="label">步长</label>
              <input v-model.number="toolOptions.step_x" type="number" step="0.1" />
            </div>
            <div>
              <label class="label">位移模式</label>
              <select v-model="toolOptions.shift_mode" class="select">
                <option value="close">close</option>
                <option value="maxmin">max/min</option>
                <option value="summaxmin">sum+max/min</option>
              </select>
            </div>
          </div>
        </div>

        <div class="tool-options" v-if="toolOptionMode === 'regress'">
          <label class="label">回归模式</label>
          <select v-model="toolOptions.regress_mode" class="select">
            <option value="best">最优拟合</option>
            <option value="least">最少拟合</option>
            <option value="channel">通道拟合</option>
          </select>
        </div>

        <div class="tool-options" v-if="toolOptionMode === 'corr'">
          <div class="form-grid">
            <div>
              <label class="label">相关系数</label>
              <select v-model="toolOptions.corr_type" class="select">
                <option value="pears">pears</option>
                <option value="sperm">sperm</option>
                <option value="sign">sign</option>
                <option value="rolling">rolling</option>
              </select>
            </div>
            <div>
              <label class="label">字段</label>
              <select v-model="toolOptions.field" class="select">
                <option value="p_change">p_change</option>
                <option value="close">close</option>
              </select>
            </div>
          </div>
        </div>

        <div class="tool-options" v-if="toolOptionMode === 'distance'">
          <div class="form-grid">
            <div>
              <label class="label">距离类型</label>
              <select v-model="toolOptions.distance_type" class="select">
                <option value="manhattan">manhattan</option>
                <option value="euclidean">euclidean</option>
                <option value="cosine">cosine</option>
              </select>
            </div>
            <div>
              <label class="label">字段</label>
              <select v-model="toolOptions.field" class="select">
                <option value="p_change">p_change</option>
                <option value="close">close</option>
              </select>
            </div>
          </div>
        </div>

        <div class="toolbar">
          <button class="btn-primary" @click="runTool" :disabled="actionsBusy">执行分析</button>
          <span class="muted">{{ analysisStatusText || '执行后自动回填分析结果' }}</span>
        </div>
      </div>

      <div class="tool-result">
        <h3>分析结果预览</h3>
        <p v-if="analysisError" class="error">{{ analysisError }}</p>
        <div v-if="analysisResult" class="code-wrap">
          <pre class="code">{{ analysisText }}</pre>
        </div>
          <div v-if="analysisResult" class="info-card">
            <div class="toolbar">
              <button class="btn-secondary" @click="syncAnalysisToChart">同步到回测K线</button>
              <label class="toggle">
                <input
                  type="checkbox"
                  :checked="analysisOverlayEnabled"
                  @change="setAnalysisOverlayEnabled($event.target.checked)"
                />
                <span>叠加趋势线</span>
              </label>
            </div>
          <p class="muted">分析标的：{{ analysisResult.symbol || '-' }}</p>
          <p class="muted" v-if="analysisResult.trend_lines?.length">
            支撑/阻力线：{{ analysisResult.trend_lines.length }} 条
          </p>
          <p class="muted">切换到“策略验证”查看图表叠加效果。</p>
        </div>
        <div v-if="analysisResult?.signal" class="info-card">
          <h4>信号解读</h4>
          <p class="muted">操作建议：{{ formatSignalAction(analysisResult.signal.action) }}</p>
          <p class="muted">原因：{{ formatSignalReason(analysisResult.signal.action, analysisResult.signal.reason) }}</p>
          <div class="result-grid">
            <div>
              <p class="muted">最新收盘</p>
              <p class="metric-value">{{ formatNumber(analysisResult.signal.last_close) }}</p>
            </div>
            <div>
              <p class="muted">支撑位</p>
              <p class="metric-value">{{ formatNumber(analysisResult.signal.support) }}</p>
            </div>
            <div>
              <p class="muted">阻力位</p>
              <p class="metric-value">{{ formatNumber(analysisResult.signal.resistance) }}</p>
            </div>
            <div>
              <p class="muted">止损</p>
              <p class="metric-value">{{ formatNumber(analysisResult.signal.stop_loss) }}</p>
            </div>
            <div>
              <p class="muted">止盈</p>
              <p class="metric-value">{{ formatNumber(analysisResult.signal.take_profit) }}</p>
            </div>
          </div>
        </div>
        <p v-else class="muted">{{ analysisStatusText || '暂无分析结果。' }}</p>
      </div>
    </div>
  </section>
</template>

<script setup>
const formatNumber = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(2)
}

const formatSignalAction = (action) => {
  const key = String(action || '').toLowerCase()
  if (key === 'breakout') return '突破上行'
  if (key === 'breakdown') return '跌破支撑'
  if (key === 'near_support') return '接近支撑'
  if (key === 'near_resistance') return '接近阻力'
  if (key === 'hold') return '观望'
  return '观望'
}

const formatSignalReason = (action, reason) => {
  const key = String(action || '').toLowerCase()
  if (key === 'breakout') return '价格突破阻力位'
  if (key === 'breakdown') return '价格跌破支撑位'
  if (key === 'near_support') return '价格靠近支撑位'
  if (key === 'near_resistance') return '价格靠近阻力位'
  if (key === 'hold') return '暂无明确趋势信号'
  return reason || '暂无明确趋势信号'
}

defineProps({
  active: Boolean,
  toolForm: Object,
  toolOptions: Object,
  toolOptionMode: String,
  analysisResult: Object,
  analysisText: String,
  analysisError: String,
  analysisStatusText: String,
  analysisOverlayEnabled: Boolean,
  setAnalysisOverlayEnabled: Function,
  runTool: Function,
  syncAnalysisToChart: Function,
  actionsBusy: Boolean
})
</script>
