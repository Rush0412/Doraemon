<template>
  <section class="panel" v-show="active">
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
    <p class="panel-note">成功任务可导出 JSON/CSV，用于后续复盘或策略记录。</p>

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
</template>

<script setup>
defineProps({
  active: Boolean,
  store: Object,
  formatTime: Function,
  brief: Function,
  exportUrl: Function,
  selectJob: Function,
  removeJob: Function,
  activeParamsText: String,
  activeResultText: String,
  activeErrorText: String
})
</script>
