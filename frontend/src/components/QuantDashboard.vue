<template>
  <div style="margin-top: 16px; display: grid; gap: 20px;">
    <section class="panel">
      <header class="panel-header">
        <div>
          <h2 style="margin: 0;">量化集成</h2>
          <p class="muted" style="margin: 6px 0 0;">股票检索、任务队列、状态同步</p>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end;">
          <button class="btn-secondary" @click="runVerify" :disabled="actionsBusy">
            环境验证
          </button>
          <button class="btn-primary" @click="runBacktest" :disabled="actionsBusy">
            回测任务
          </button>
        </div>
      </header>
      <div class="grid-2">
        <div>
          <label class="label">市场</label>
          <select v-model="market" class="select">
            <option value="CN">CN</option>
            <option value="HK">HK</option>
            <option value="US">US</option>
          </select>
        </div>
        <div>
          <label class="label">检索</label>
          <input v-model="q" placeholder="symbol 或 公司名，如 AAPL / 600812 / 小米" @keyup.enter="search" />
        </div>
      </div>
      <div style="display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap;">
        <button class="btn-secondary" @click="search" :disabled="store.symbolsLoading">
          查询
        </button>
        <button class="btn-secondary" @click="refreshJobs" :disabled="store.jobsLoading">
          刷新任务
        </button>
        <button class="btn-secondary" @click="runKlUpdate" :disabled="actionsBusy">
          数据更新任务
        </button>
      </div>
      <p v-if="store.symbolsError" class="error" style="margin: 12px 0 0;">{{ store.symbolsError }}</p>
      <div v-if="store.symbolsLoading" class="muted" style="margin-top: 12px;">加载中...</div>
      <div v-else class="table-wrap" style="margin-top: 12px;">
        <table class="table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Market</th>
              <th>Name</th>
              <th>Exchange</th>
              <th>Industry</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in store.symbols" :key="`${item.market}-${item.symbol}`">
              <td class="mono">{{ item.symbol }}</td>
              <td>{{ item.market }}</td>
              <td>{{ item.name || '-' }}</td>
              <td>{{ item.exchange || '-' }}</td>
              <td>{{ item.industry || '-' }}</td>
            </tr>
            <tr v-if="store.symbols.length === 0">
              <td colspan="5" class="muted" style="padding: 12px;">无结果</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <header class="panel-header">
        <div>
          <h3 style="margin: 0;">任务队列</h3>
          <p class="muted" style="margin: 6px 0 0;">running / succeeded / failed 状态轮询同步</p>
        </div>
        <div v-if="store.activeJob" class="pill">
          当前任务 #{{ store.activeJob.id }} · {{ store.activeJob.type }} ·
          <span :class="['status', `status-${store.activeJob.status}`]">{{ store.activeJob.status }}</span>
        </div>
      </header>

      <p v-if="store.jobsError" class="error" style="margin: 0 0 10px;">{{ store.jobsError }}</p>
      <div v-if="store.jobsLoading" class="muted">加载中...</div>
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
              <td>
                <span :class="['status', `status-${job.status}`]">{{ job.status }}</span>
              </td>
              <td class="mono">{{ formatTime(job.created_at) }}</td>
              <td class="mono">{{ formatTime(job.updated_at) }}</td>
              <td class="mono">{{ brief(job.result) }}</td>
              <td class="mono">{{ brief(job.error) }}</td>
              <td style="text-align: right;">
                <div style="display: inline-flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end;">
                  <a v-if="job.status === 'succeeded'" class="btn-secondary" :href="exportUrl(job.id, 'json')" target="_blank" rel="noreferrer">
                    导出JSON
                  </a>
                  <a
                    v-if="job.status === 'succeeded' && job.result && job.result.orders"
                    class="btn-secondary"
                    :href="exportUrl(job.id, 'csv', 'orders')"
                  >
                    订单CSV
                  </a>
                  <a
                    v-if="job.status === 'succeeded' && job.result && job.result.actions"
                    class="btn-secondary"
                    :href="exportUrl(job.id, 'csv', 'actions')"
                  >
                    行为CSV
                  </a>
                  <button class="btn-secondary" @click="selectJob(job.id)">详情</button>
                </div>
              </td>
            </tr>
            <tr v-if="store.jobs.length === 0">
              <td colspan="8" class="muted" style="padding: 12px;">暂无任务</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="store.activeJob" style="margin-top: 14px;">
        <h4 style="margin: 0 0 8px;">任务详情</h4>
        <pre class="code">{{ store.activeJob }}</pre>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useQuantStore } from '../stores/quantStore'

const store = useQuantStore()
const market = ref(store.market)
const q = ref(store.query)

const actionsBusy = computed(
  () => store.jobsLoading || store.activeJobLoading || store.symbolsLoading
)

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

const search = async () => {
  await store.searchSymbols({ market: market.value, q: q.value })
}

const refreshJobs = async () => {
  await store.fetchJobs()
}

const selectJob = async (id) => {
  await store.fetchJob(id)
}

const exportUrl = (id, format, section) => {
  const params = new URLSearchParams()
  if (format) params.set('format', format)
  if (section) params.set('section', section)
  const qs = params.toString()
  return `/api/v1/jobs/${encodeURIComponent(String(id))}/export${qs ? `?${qs}` : ''}`
}

const runVerify = async () => {
  const job = await store.startVerify()
  await store.fetchJob(job.id)
}

const runKlUpdate = async () => {
  const job = await store.startKlUpdate({ market: market.value, n_folds: 1, how: 'thread', n_jobs: 8 })
  await store.fetchJob(job.id)
}

const runBacktest = async () => {
  const symbols = market.value === 'US' ? ['usAAPL'] : market.value === 'HK' ? ['hk00700'] : ['600812']
  const job = await store.startBacktest({ market: market.value, symbols, n_folds: 1, cash: 1000000 })
  await store.fetchJob(job.id)
}

let timer = null
onMounted(async () => {
  await Promise.all([store.fetchJobs(), store.searchSymbols({ market: market.value, q: q.value })])
  timer = setInterval(async () => {
    await store.fetchJobs()
    if (store.activeJob?.id) {
      await store.fetchJob(store.activeJob.id)
    }
  }, 2500)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
