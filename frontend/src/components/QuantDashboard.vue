<template>
  <div class="quant-shell">
    <section class="hero">
      <div class="hero-head">
        <div>
          <p class="eyebrow">Doraemon Quant Suite</p>
          <h1>阿布量化控制台</h1>
          <p class="hero-sub">
            数据更新、回测、参数寻优与量化分析一体化视图。
          </p>
        </div>
        <div class="hero-actions">
          <button class="btn-ghost" @click="refreshJobs" :disabled="actionsBusy">刷新任务</button>
          <button class="btn-primary" @click="runVerify" :disabled="actionsBusy">环境验证</button>
        </div>
      </div>
      <div class="hero-metrics">
        <div class="metric-card">
          <p class="metric-label">任务总数</p>
          <p class="metric-value">{{ jobStats.total }}</p>
        </div>
        <div class="metric-card">
          <p class="metric-label">运行中</p>
          <p class="metric-value">{{ jobStats.running }}</p>
        </div>
        <div class="metric-card">
          <p class="metric-label">成功</p>
          <p class="metric-value">{{ jobStats.succeeded }}</p>
        </div>
        <div class="metric-card">
          <p class="metric-label">失败</p>
          <p class="metric-value">{{ jobStats.failed }}</p>
        </div>
      </div>
    </section>

    <section class="grid grid-2">
      <div class="panel glass">
        <header class="panel-title">
          <div>
            <h2>股票检索</h2>
            <p class="muted">检索股票代码、公司名称与交易所信息。</p>
          </div>
          <span class="pill">Symbols</span>
        </header>
        <div class="form-grid">
          <div>
            <label class="label">市场</label>
            <select v-model="market" class="select">
              <option value="SH">SH (Shanghai)</option>
              <option value="SZ">SZ (Shenzhen)</option>
              <option value="300">300 (ChiNext)</option>
            </select>
          </div>
          <div>
            <label class="label">关键词</label>
            <input v-model="query" placeholder="symbol / 公司名 / 关键字" @keyup.enter="search" />
          </div>
          <div>
            <label class="label">类型</label>
            <select v-model="kind" class="select">
              <option value="stock">个股</option>
              <option value="index">指数</option>
              <option value="all">全部</option>
            </select>
          </div>
        </div>
        <div class="toolbar">
          <button class="btn-secondary" @click="search" :disabled="store.symbolsLoading">查询</button>
          <button class="btn-ghost" @click="importSymbols" :disabled="store.symbolsLoading">初始化当前市场</button>
          <button class="btn-ghost" @click="importAllSymbols" :disabled="store.symbolsLoading">导入全部A股</button>
          <button class="btn-ghost" @click="selectPage" :disabled="store.symbolsLoading">全选当前页</button>
          <button class="btn-ghost" @click="invertPage" :disabled="store.symbolsLoading">反选当前页</button>
          <span class="muted">{{ store.symbolsLoading ? '加载中…' : ' ' }}</span>
          <span v-if="selectedSymbols.length" class="muted">已选 {{ selectedSymbols.length }} 只</span>
        </div>
        <p v-if="store.symbolsError" class="error">{{ store.symbolsError }}</p>
        <div class="table-wrap" v-if="!store.symbolsLoading">
          <table class="table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Market</th>
                <th>Type</th>
                <th>Name</th>
                <th>Exchange</th>
                <th>Industry</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in store.symbols" :key="`${item.market}-${item.symbol}`">
                <td class="mono">{{ displaySymbol(item) }}</td>
                <td>{{ item.market }}</td>
                <td>{{ displayKind(item.kind) }}</td>
                <td>{{ item.name || '-' }}</td>
                <td>{{ item.exchange || '-' }}</td>
                <td>{{ item.industry || '-' }}</td>
                <td>
                  <button class="btn-ghost" @click="toggleSymbol(item.symbol)">
                    {{ isSelected(item.symbol) ? '移除' : '使用' }}
                  </button>
                </td>
              </tr>
              <tr v-if="store.symbols.length === 0">
                <td colspan="7" class="muted">暂无结果</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="selectedSymbols.length" class="selection">
          <div class="selection-head">
            <span class="pill">选股篮</span>
            <div class="selection-actions">
              <button class="btn-secondary" @click="clearSymbols">清空</button>
              <button class="btn-secondary" @click="saveSelection">保存组合</button>
            </div>
          </div>
          <div class="selection-load">
            <select v-model="selectedPortfolio" class="select">
              <option value="">加载组合</option>
              <option v-for="name in savedPortfolios" :key="name" :value="name">{{ name }}</option>
            </select>
            <button class="btn-secondary" @click="loadPortfolio" :disabled="!selectedPortfolio">加载</button>
            <button class="btn-secondary" @click="deletePortfolio" :disabled="!selectedPortfolio">删除</button>
          </div>
          <div class="selection-chips">
            <button v-for="symbol in selectedSymbols" :key="symbol" class="chip" @click="removeSymbol(symbol)">
              {{ symbol }}
              <span class="chip-close">×</span>
            </button>
          </div>
        </div>
        <div class="pager">
          <span class="muted">共 {{ store.total }} 条</span>
          <div class="pager-controls">
            <button class="btn-secondary" @click="changePage(store.page - 1)" :disabled="store.page <= 1">
              上一页
            </button>
            <span class="mono">{{ store.page }} / {{ totalPages }}</span>
            <button class="btn-secondary" @click="changePage(store.page + 1)" :disabled="store.page >= totalPages">
              下一页
            </button>
          </div>
          <div class="pager-size">
            <span class="muted">每页</span>
            <select v-model.number="pageSize" class="select" @change="applyPageSize">
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
        </div>
      </div>

      <div class="panel glass">
        <header class="panel-title">
          <div>
            <h2>数据更新</h2>
            <p class="muted">批量更新市场数据缓存，建议先执行。</p>
          </div>
          <span class="pill">Update</span>
        </header>
        <div class="form-grid">
          <div>
            <label class="label">回溯年数</label>
            <input v-model.number="updateForm.n_folds" type="number" min="1" />
          </div>
          <div>
            <label class="label">并发数</label>
            <input v-model.number="updateForm.n_jobs" type="number" min="1" />
          </div>
          <div>
            <label class="label">开始日期</label>
            <input v-model="updateForm.start" type="date" />
          </div>
          <div>
            <label class="label">结束日期</label>
            <input v-model="updateForm.end" type="date" />
          </div>
          <div>
            <label class="label">执行模式</label>
            <select v-model="updateForm.how" class="select">
              <option value="thread">thread</option>
              <option value="process">process</option>
              <option value="main">main</option>
            </select>
          </div>
        </div>
        <div class="toolbar">
          <button class="btn-primary" @click="runKlUpdate" :disabled="actionsBusy">启动更新</button>
          <span class="muted">将创建异步任务</span>
        </div>
        <div class="update-targets">
          <p class="muted">更新标的</p>
          <div v-if="selectedSymbols.length" class="selection-chips">
            <button v-for="symbol in selectedSymbols" :key="symbol" class="chip" @click="removeSymbol(symbol)">
              {{ symbol }}
              <span class="chip-close">×</span>
            </button>
          </div>
          <p v-else class="muted">全量更新当前市场</p>
        </div>
      </div>
    </section>

    <section class="grid grid-2">
      <div class="panel">
        <header class="panel-title">
          <div>
            <h2>历史回测</h2>
            <p class="muted">执行经典买入突破 + ATR 止损止盈。</p>
          </div>
          <span class="pill">Backtest</span>
        </header>
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
      </div>

      <div class="panel">
        <header class="panel-title">
          <div>
            <h2>参数交叉验证</h2>
            <p class="muted">多参数组合网格寻优。</p>
          </div>
          <span class="pill">Grid</span>
        </header>
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
            <label class="label">买入周期列表</label>
            <input v-model="gridForm.buy_xd_list" placeholder="20, 42, 60" />
          </div>
          <div>
            <label class="label">止损倍数列表</label>
            <input v-model="gridForm.stop_loss_n_list" placeholder="0.5, 1.0" />
          </div>
          <div>
            <label class="label">止盈倍数列表</label>
            <input v-model="gridForm.stop_win_n_list" placeholder="2.0, 3.0" />
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
          <pre class="code">{{ gridSummaryText }}</pre>
        </div>
      </div>
    </section>

    <section class="panel">
      <header class="panel-title">
        <div>
          <h2>量化分析工具</h2>
          <p class="muted">阻力位、跳空、相关性与涨跌幅分析。</p>
        </div>
        <span class="pill">Tools</span>
      </header>
      <div class="tool-layout">
        <div class="tool-form">
          <div class="form-grid">
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
                <option value="correlation">相关性分析</option>
                <option value="distance">距离矩阵分析</option>
                <option value="p_change_stats">涨跌幅统计</option>
                <option value="date_week_wave">交易日波动分析</option>
                <option value="date_week_win">交易日涨跌概率</option>
                <option value="bcut_change_vc">涨跌区间分析(固定)</option>
                <option value="qcut_change_vc">涨跌区间分析(分位)</option>
                <option value="wave_change_rate">波动套利指标</option>
              </select>
            </div>
            <div>
              <label class="label">标的列表</label>
              <input v-model="toolForm.symbols" placeholder="sh600036, sz000001" />
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
            <label class="label">跳空模式</label>
            <select v-model="toolOptions.mode" class="select">
              <option value="stats">统计模式</option>
              <option value="gap">缺口筛选</option>
              <option value="weighted">缺口加权筛选</option>
            </select>
            <div class="form-grid">
              <div>
                <label class="label">能量阈值</label>
                <input v-model.number="toolOptions.power_threshold" type="number" step="0.1" />
              </div>
              <div>
                <label class="label">跳空阈值因子</label>
                <input v-model.number="toolOptions.jump_diff_factor" type="number" step="0.1" />
              </div>
              <div>
                <label class="label">权重 A</label>
                <input v-model.number="toolOptions.weight_a" type="number" step="0.1" />
              </div>
              <div>
                <label class="label">权重 B</label>
                <input v-model.number="toolOptions.weight_b" type="number" step="0.1" />
              </div>
            </div>
          </div>

          <div class="tool-options" v-if="toolOptionMode === 'trend'">
            <div class="form-grid">
              <div>
                <label class="label">对比标的</label>
                <input v-model="toolOptions.benchmark" placeholder="usSPY / sh000001" />
              </div>
              <div>
                <label class="label">重采样周期</label>
                <input v-model.number="toolOptions.resample" type="number" min="1" />
              </div>
              <div>
                <label class="label">对比字段</label>
                <select v-model="toolOptions.speed_key" class="select">
                  <option value="close">close</option>
                  <option value="high">high</option>
                  <option value="low">low</option>
                  <option value="p_change">p_change</option>
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
            <span class="muted">执行后查看任务详情</span>
          </div>
        </div>

        <div class="tool-result">
          <h3>分析结果预览</h3>
          <div v-if="analysisResult" class="code-wrap">
            <pre class="code">{{ analysisText }}</pre>
          </div>
          <p v-else class="muted">暂无分析结果。</p>
        </div>
      </div>
    </section>

    <section class="panel">
      <header class="panel-title">
        <div>
          <h2>任务队列</h2>
          <p class="muted">回测、更新与分析任务统一管理。</p>
        </div>
        <div v-if="store.activeJob" class="pill">
          当前任务 #{{ store.activeJob.id }} · {{ store.activeJob.type }} ·
          <span :class="['status', `status-${store.activeJob.status}`]">{{ store.activeJob.status }}</span>
        </div>
      </header>

      <p v-if="store.jobsError" class="error">{{ store.jobsError }}</p>
      <div v-if="store.jobsLoading" class="muted">加载中…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Created</th>
              <th>Updated</th>
              <th>Result</th>
              <th>Error</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in store.jobs" :key="job.id">
              <td class="mono">#{{ job.id }}</td>
              <td>{{ job.type }}</td>
              <td><span :class="['status', `status-${job.status}`]">{{ job.status }}</span></td>
              <td class="mono">{{ formatTime(job.created_at) }}</td>
              <td class="mono">{{ formatTime(job.updated_at) }}</td>
              <td class="mono">{{ brief(job.result) }}</td>
              <td class="mono">{{ brief(job.error) }}</td>
              <td>
                <div class="table-actions">
                  <a v-if="job.status === 'succeeded'" class="btn-ghost" :href="exportUrl(job.id, 'json')" target="_blank" rel="noreferrer">
                    导出 JSON
                  </a>
                  <a v-if="job.status === 'succeeded' && job.result?.orders" class="btn-ghost" :href="exportUrl(job.id, 'csv', 'orders')">
                    订单 CSV
                  </a>
                  <a v-if="job.status === 'succeeded' && job.result?.actions" class="btn-ghost" :href="exportUrl(job.id, 'csv', 'actions')">
                    行为 CSV
                  </a>
                  <button class="btn-secondary" @click="selectJob(job.id)">详情</button>
                  <button class="btn-secondary" @click="removeJob(job)" :disabled="job.status === 'running'">删除</button>
                </div>
              </td>
            </tr>
            <tr v-if="store.jobs.length === 0">
              <td colspan="8" class="muted">暂无任务</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="store.activeJob" class="result-card">
        <h3>任务详情</h3>
        <div class="result-grid">
          <div>
            <p class="muted">任务编号</p>
            <p class="metric-value">#{{ store.activeJob.id }}</p>
          </div>
          <div>
            <p class="muted">任务类型</p>
            <p class="metric-value">{{ store.activeJob.type }}</p>
          </div>
          <div>
            <p class="muted">状态</p>
            <p class="metric-value">{{ store.activeJob.status }}</p>
          </div>
          <div>
            <p class="muted">更新时间</p>
            <p class="metric-value">{{ formatTime(store.activeJob.updated_at) }}</p>
          </div>
        </div>
        <div class="code-wrap" v-if="store.activeJob.params">
          <p class="muted">参数</p>
          <pre class="code">{{ activeParamsText }}</pre>
        </div>
        <div class="code-wrap" v-if="store.activeJob.result">
          <p class="muted">结果</p>
          <pre class="code">{{ activeResultText }}</pre>
        </div>
        <div class="code-wrap" v-if="store.activeJob.error">
          <p class="muted">错误</p>
          <pre class="code">{{ activeErrorText }}</pre>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useQuantStore } from '../stores/quantStore'

const store = useQuantStore()
const market = ref(store.market)
const query = ref(store.query)
const kind = ref(store.kind)
const pageSize = ref(store.pageSize)
const selectedSymbols = ref([])
const savedPortfolios = ref([])
const selectedPortfolio = ref('')

const updateForm = reactive({
  market: market.value,
  n_folds: 1,
  start: '',
  end: '',
  n_jobs: 8,
  how: 'thread',
  symbols: ''
})

const backtestForm = reactive({
  market: market.value,
  symbols: '',
  cash: 1000000,
  buy_xd: 42,
  stop_loss_n: 0.5,
  stop_win_n: 3.0,
  n_folds: 1,
  start: '',
  end: ''
})

const gridForm = reactive({
  market: market.value,
  symbols: '',
  cash: 1000000,
  buy_xd_list: '20, 42, 60',
  stop_loss_n_list: '0.5, 1.0',
  stop_win_n_list: '2.0, 3.0',
  n_folds: 1,
  start: '',
  end: '',
  max_runs: 30
})

const toolForm = reactive({
  market: market.value,
  tool: 'support_resistance',
  symbols: '',
  n_folds: 1,
  start: '',
  end: '',
  limit: 200
})

const toolOptions = reactive({
  only_last: true,
  mode: 'stats',
  jump_diff_factor: 1.0,
  power_threshold: 2.0,
  weight_a: 0.5,
  weight_b: 0.5,
  benchmark: '',
  resample: 5,
  speed_key: 'close',
  step_x: 1.0,
  shift_mode: 'close',
  regress_mode: 'best',
  corr_type: 'pears',
  distance_type: 'manhattan',
  field: 'p_change'
})

const actionsBusy = computed(
  () => store.jobsLoading || store.activeJobLoading || store.symbolsLoading
)

const defaultSymbolForMarket = (value) => {
  if (value === 'SH') return 'sh600036'
  if (value === 'SZ') return 'sz000001'
  if (value === '300') return 'sz300750'
  if (value === 'US') return 'usAAPL'
  if (value === 'HK') return 'hk00700'
  return 'sh600036'
}

if (!backtestForm.symbols) backtestForm.symbols = defaultSymbolForMarket(market.value)
if (!gridForm.symbols) gridForm.symbols = defaultSymbolForMarket(market.value)
if (!toolForm.symbols) toolForm.symbols = defaultSymbolForMarket(market.value)

watch(market, (val) => {
  updateForm.market = val
  backtestForm.market = val
  gridForm.market = val
  toolForm.market = val
  if (!backtestForm.symbols) backtestForm.symbols = defaultSymbolForMarket(val)
  if (!gridForm.symbols) gridForm.symbols = defaultSymbolForMarket(val)
  if (!toolForm.symbols) toolForm.symbols = defaultSymbolForMarket(val)
})

const jobStats = computed(() => {
  const stats = { total: 0, running: 0, succeeded: 0, failed: 0 }
  stats.total = store.jobs.length
  for (const job of store.jobs) {
    if (job.status === 'running') stats.running += 1
    if (job.status === 'succeeded') stats.succeeded += 1
    if (job.status === 'failed') stats.failed += 1
  }
  return stats
})

const backtestSummary = computed(() => {
  if (!store.activeJob || store.activeJob.type !== 'backtest') return null
  return store.activeJob.result?.summary || null
})

const gridSummary = computed(() => {
  if (!store.activeJob || store.activeJob.type !== 'grid_search') return null
  return store.activeJob.result?.best || null
})

const analysisResult = computed(() => {
  if (!store.activeJob || store.activeJob.type !== 'analysis') return null
  return store.activeJob.result || null
})

const gridSummaryText = computed(() =>
  gridSummary.value ? JSON.stringify(gridSummary.value, null, 2) : ''
)

const analysisText = computed(() =>
  analysisResult.value ? JSON.stringify(analysisResult.value, null, 2) : ''
)

const activeParamsText = computed(() =>
  store.activeJob?.params ? JSON.stringify(store.activeJob.params, null, 2) : ''
)
const activeResultText = computed(() =>
  store.activeJob?.result ? JSON.stringify(store.activeJob.result, null, 2) : ''
)
const activeErrorText = computed(() =>
  store.activeJob?.error ? String(store.activeJob.error) : ''
)

const toolOptionMode = computed(() => {
  if (toolForm.tool === 'support_resistance') return 'support'
  if (toolForm.tool === 'jump_gap') return 'jump'
  if (toolForm.tool === 'trend_speed') return 'trend'
  if (toolForm.tool === 'shift_distance') return 'shift'
  if (toolForm.tool === 'regress' || toolForm.tool === 'price_channel') return 'regress'
  if (toolForm.tool === 'correlation') return 'corr'
  if (toolForm.tool === 'distance') return 'distance'
  return 'base'
})

const totalPages = computed(() => Math.max(1, Math.ceil(store.total / store.pageSize)))

const formatTime = (v) => {
  if (!v) return '-'
  try {
    const d = typeof v === 'string' ? new Date(v) : new Date(String(v))
    if (Number.isNaN(d.getTime())) return String(v)
    return d.toLocaleString()
  } catch {
    return String(v)
  }
}

const brief = (v) => {
  if (!v) return ''
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 60 ? `${s.slice(0, 57)}...` : s
}

const parseNumberList = (raw) =>
  String(raw)
    .split(/[\s,;]+/)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item))

const search = async () => {
  await store.searchSymbols({
    market: market.value,
    q: query.value,
    kind: kind.value,
    page: 1,
    pageSize: pageSize.value
  })
}

const importSymbols = async () => {
  const data = await store.importSymbols(market.value)
  if (data) {
    await store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page: 1,
      pageSize: pageSize.value
    })
  }
}

const importAllSymbols = async () => {
  const data = await store.importSymbols('CN')
  if (data) {
    await store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page: 1,
      pageSize: pageSize.value
    })
  }
}

const refreshJobs = async () => {
  await store.fetchJobs()
}

const selectJob = async (id) => {
  await store.fetchJob(id)
}

const removeJob = async (job) => {
  if (job.status === 'running') return
  await store.deleteJob(job.id)
}

const exportUrl = (id, format, section) => {
  const params = new URLSearchParams()
  if (format) params.set('format', format)
  if (section) params.set('section', section)
  const qs = params.toString()
  return `/api/v1/jobs/${encodeURIComponent(String(id))}/export${qs ? `?${qs}` : ''}`
}

const addSymbol = (symbol) => {
  if (!symbol || selectedSymbols.value.includes(symbol)) return
  selectedSymbols.value = [...selectedSymbols.value, symbol]
  syncSelectedSymbols()
}

const displaySymbol = (item) => {
  if (!item || !item.symbol) return ''
  const lower = item.symbol.toLowerCase()
  if (lower.startsWith('sh') || lower.startsWith('sz')) {
    return item.symbol.slice(2)
  }
  return item.symbol
}

const displayKind = (kind) => {
  if (kind === 'index') return '指数'
  if (kind === 'stock') return '个股'
  return '-'
}

const isSelected = (symbol) => selectedSymbols.value.includes(symbol)

const toggleSymbol = (symbol) => {
  if (isSelected(symbol)) {
    removeSymbol(symbol)
    return
  }
  addSymbol(symbol)
}

const removeSymbol = (symbol) => {
  selectedSymbols.value = selectedSymbols.value.filter((item) => item !== symbol)
  syncSelectedSymbols()
}

const clearSymbols = () => {
  selectedSymbols.value = []
  syncSelectedSymbols()
}

const selectPage = () => {
  const pageSymbols = store.symbols.map((item) => item.symbol)
  const merged = new Set([...selectedSymbols.value, ...pageSymbols])
  selectedSymbols.value = Array.from(merged)
  syncSelectedSymbols()
}

const invertPage = () => {
  const pageSymbols = new Set(store.symbols.map((item) => item.symbol))
  const next = selectedSymbols.value.filter((symbol) => !pageSymbols.has(symbol))
  for (const symbol of pageSymbols) {
    if (!selectedSymbols.value.includes(symbol)) {
      next.push(symbol)
    }
  }
  selectedSymbols.value = next
  syncSelectedSymbols()
}

const saveSelection = () => {
  const name = window.prompt('保存组合名称')
  if (!name) return
  const trimmed = name.trim()
  if (!trimmed) return
  const payload = { name: trimmed, symbols: selectedSymbols.value }
  localStorage.setItem(`doraemon_portfolio_${trimmed}`, JSON.stringify(payload))
  const indexKey = 'doraemon_portfolios'
  const list = JSON.parse(localStorage.getItem(indexKey) || '[]')
  if (!list.includes(trimmed)) list.push(trimmed)
  localStorage.setItem(indexKey, JSON.stringify(list))
  savedPortfolios.value = list
  selectedPortfolio.value = trimmed
}

const loadPortfolio = () => {
  if (!selectedPortfolio.value) return
  const raw = localStorage.getItem(`doraemon_portfolio_${selectedPortfolio.value}`)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    selectedSymbols.value = Array.isArray(parsed.symbols) ? parsed.symbols : []
    syncSelectedSymbols()
  } catch {
    // ignore malformed payload
  }
}

const deletePortfolio = () => {
  if (!selectedPortfolio.value) return
  localStorage.removeItem(`doraemon_portfolio_${selectedPortfolio.value}`)
  const indexKey = 'doraemon_portfolios'
  const list = JSON.parse(localStorage.getItem(indexKey) || '[]').filter(
    (name) => name !== selectedPortfolio.value
  )
  localStorage.setItem(indexKey, JSON.stringify(list))
  savedPortfolios.value = list
  selectedPortfolio.value = ''
}

const syncSelectedSymbols = () => {
  const text = selectedSymbols.value.join(', ')
  backtestForm.symbols = text
  gridForm.symbols = text
  toolForm.symbols = text
  updateForm.symbols = text
}

const changePage = async (nextPage) => {
  if (nextPage < 1 || nextPage > totalPages.value) return
  await store.searchSymbols({
    market: market.value,
    q: query.value,
    kind: kind.value,
    page: nextPage,
    pageSize: pageSize.value
  })
}

const applyPageSize = async () => {
  await store.searchSymbols({
    market: market.value,
    q: query.value,
    kind: kind.value,
    page: 1,
    pageSize: pageSize.value
  })
}

const runVerify = async () => {
  const job = await store.startVerify()
  await store.fetchJob(job.id)
}

const runKlUpdate = async () => {
  const symbols = selectedSymbols.value.length ? selectedSymbols.value.join(',') : ''
  const job = await store.startKlUpdate({
    market: updateForm.market,
    n_folds: updateForm.n_folds,
    start: updateForm.start || undefined,
    end: updateForm.end || undefined,
    how: updateForm.how,
    n_jobs: updateForm.n_jobs,
    symbols: symbols || undefined,
    all: !symbols
  })
  await store.fetchJob(job.id)
}

const runBacktest = async () => {
  const job = await store.startBacktest({
    market: backtestForm.market,
    symbols: backtestForm.symbols,
    n_folds: backtestForm.n_folds,
    start: backtestForm.start || undefined,
    end: backtestForm.end || undefined,
    cash: backtestForm.cash,
    buy_xd: backtestForm.buy_xd,
    stop_loss_n: backtestForm.stop_loss_n,
    stop_win_n: backtestForm.stop_win_n
  })
  await store.fetchJob(job.id)
}

const runGridSearch = async () => {
  const job = await store.startGridSearch({
    market: gridForm.market,
    symbols: gridForm.symbols,
    n_folds: gridForm.n_folds,
    start: gridForm.start || undefined,
    end: gridForm.end || undefined,
    cash: gridForm.cash,
    buy_xd_list: parseNumberList(gridForm.buy_xd_list).map((n) => Math.round(n)),
    stop_loss_n_list: parseNumberList(gridForm.stop_loss_n_list),
    stop_win_n_list: parseNumberList(gridForm.stop_win_n_list),
    max_runs: gridForm.max_runs
  })
  await store.fetchJob(job.id)
}

const buildToolOptions = () => {
  const opts = {}
  if (toolForm.tool === 'support_resistance') opts.only_last = toolOptions.only_last
  if (toolForm.tool === 'jump_gap') {
    opts.mode = toolOptions.mode
    opts.jump_diff_factor = toolOptions.jump_diff_factor
    opts.power_threshold = toolOptions.power_threshold
    opts.weight = [toolOptions.weight_a, toolOptions.weight_b]
  }
  if (toolForm.tool === 'trend_speed') {
    opts.benchmark = toolOptions.benchmark
    opts.resample = toolOptions.resample
    opts.speed_key = toolOptions.speed_key
  }
  if (toolForm.tool === 'shift_distance') {
    opts.step_x = toolOptions.step_x
    opts.mode = toolOptions.shift_mode
  }
  if (toolForm.tool === 'regress' || toolForm.tool === 'price_channel') {
    opts.mode = toolOptions.regress_mode
  }
  if (toolForm.tool === 'correlation') {
    opts.corr_type = toolOptions.corr_type
    opts.field = toolOptions.field
  }
  if (toolForm.tool === 'distance') {
    opts.distance_type = toolOptions.distance_type
    opts.field = toolOptions.field
  }
  return opts
}

const runTool = async () => {
  const job = await store.startQuantTool({
    market: toolForm.market,
    tool: toolForm.tool,
    symbols: toolForm.symbols,
    n_folds: toolForm.n_folds,
    start: toolForm.start || undefined,
    end: toolForm.end || undefined,
    limit: toolForm.limit,
    options: buildToolOptions()
  })
  await store.fetchJob(job.id)
}

onMounted(async () => {
  savedPortfolios.value = JSON.parse(localStorage.getItem('doraemon_portfolios') || '[]')
  await Promise.all([
    store.fetchJobs(),
    store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page: store.page,
      pageSize: store.pageSize
    })
  ])
})
</script>
