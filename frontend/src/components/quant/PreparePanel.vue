<template>
  <section class="grid grid-2" v-show="active">
    <div class="panel glass">
      <header class="panel-title">
        <div>
          <h2>股票检索</h2>
          <p class="muted">检索股票代码、公司名称与交易所信息。</p>
        </div>
        <span class="pill">Symbols</span>
      </header>
      <p class="panel-note">建议先导入股票库，再检索并加入选股篮。选股篮会同步到更新、回测、寻优与分析。</p>
      <div class="form-grid">
        <div>
          <label class="label">市场</label>
          <select :value="market" class="select" @change="emit('update:market', $event.target.value)">
            <option value="SH">SH (Shanghai)</option>
            <option value="SZ">SZ (Shenzhen)</option>
            <option value="300">300 (ChiNext)</option>
          </select>
        </div>
        <div>
          <label class="label">关键词</label>
          <input
            :value="query"
            placeholder="symbol / 公司名 / 关键字"
            @input="emit('update:query', $event.target.value)"
            @keyup.enter="search"
          />
        </div>
        <div>
          <label class="label">类型</label>
          <select :value="kind" class="select" @change="emit('update:kind', $event.target.value)">
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
          <select
            :value="selectedPortfolio"
            class="select"
            @change="emit('update:selectedPortfolio', $event.target.value)"
          >
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
          <select
            :value="pageSize"
            class="select"
            @change="emit('update:pageSize', Number($event.target.value)); applyPageSize()"
          >
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
      <p class="panel-note">更新会将K线写入PG；建议回溯至少 1 年。选股篮为空时将全量更新当前市场。</p>
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
      <div v-if="lastUpdateSummary" class="info-card">
        <p class="muted">最近更新</p>
        <div class="result-grid">
          <div>
            <p class="muted">更新标的</p>
            <p class="metric-value">{{ lastUpdateSummary.updated_symbols || 0 }}</p>
          </div>
          <div>
            <p class="muted">写入行数</p>
            <p class="metric-value">{{ lastUpdateSummary.rows || 0 }}</p>
          </div>
          <div>
            <p class="muted">缺失标的</p>
            <p class="metric-value">{{ (lastUpdateSummary.missing_symbols || []).length }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const emit = defineEmits([
  'update:market',
  'update:query',
  'update:kind',
  'update:pageSize',
  'update:selectedPortfolio'
])

defineProps({
  active: Boolean,
  store: Object,
  market: String,
  query: String,
  kind: String,
  pageSize: Number,
  selectedSymbols: Array,
  savedPortfolios: Array,
  selectedPortfolio: String,
  updateForm: Object,
  lastUpdateSummary: Object,
  totalPages: Number,
  actionsBusy: Boolean,
  search: Function,
  importSymbols: Function,
  importAllSymbols: Function,
  selectPage: Function,
  invertPage: Function,
  displaySymbol: Function,
  displayKind: Function,
  toggleSymbol: Function,
  isSelected: Function,
  clearSymbols: Function,
  saveSelection: Function,
  loadPortfolio: Function,
  deletePortfolio: Function,
  removeSymbol: Function,
  changePage: Function,
  applyPageSize: Function,
  runKlUpdate: Function
})
</script>
