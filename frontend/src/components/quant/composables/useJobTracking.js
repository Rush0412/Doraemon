import { computed } from 'vue'

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export function useJobTracking({ store, trackedJobRunning }) {
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

  const lastUpdateSummary = computed(() => {
    const job = store.jobs.find((item) => item.type === 'kl_update' && item.status === 'succeeded')
    return job?.result || null
  })

  const latestJobByType = (type) => {
    if (!type) return null
    const jobs = store.jobs.filter((job) => job.type === type)
    if (!jobs.length) return null
    return jobs.reduce((latest, job) => (job.id > latest.id ? job : latest), jobs[0])
  }

  const refreshJobs = async () => {
    await store.fetchJobs()
  }

  const selectJob = async (id) => {
    await store.fetchJob(id)
  }

  const removeJob = async (job) => {
    await store.deleteJob(job.id, { force: job.status === 'running' })
  }

  const batchDeleteFinished = async () => {
    const result = await store.deleteJobsBatch({ delete_finished: true })
    if ((result.deleted_ids || []).length === 0) {
      await store.fetchJobs()
    }
  }

  const batchDeleteFailed = async () => {
    const result = await store.deleteJobsBatch({ statuses: ['failed'], delete_finished: false })
    if ((result.deleted_ids || []).length === 0) {
      await store.fetchJobs()
    }
  }

  const exportUrl = (id, format, section) => {
    const params = new URLSearchParams()
    if (format) params.set('format', format)
    if (section) params.set('section', section)
    const qs = params.toString()
    return `/api/v1/jobs/${encodeURIComponent(String(id))}/export${qs ? `?${qs}` : ''}`
  }

  const jobExportSections = (job) => {
    if (job?.status !== 'succeeded' || !job?.result || typeof job.result !== 'object') return []
    const candidates = [
      { key: 'orders', section: 'orders', format: 'csv', label: '订单 CSV' },
      { key: 'actions', section: 'actions', format: 'csv', label: '行为 CSV' },
      { key: 'top_symbols', section: 'top_symbols', format: 'json', label: '榜单 JSON' },
      { key: 'actionable_candidates', section: 'actionable_candidates', format: 'json', label: '候选 JSON' },
      { key: 'runs', section: 'runs', format: 'json', label: '参数 JSON' },
      { key: 'diagnostics', section: 'diagnostics', format: 'json', label: '诊断 JSON' }
    ]
    return candidates.filter((item) => job.result?.[item.key])
  }

  const activeParamsText = computed(() =>
    store.activeJob?.params ? JSON.stringify(store.activeJob.params, null, 2) : ''
  )

  const activeResultText = computed(() =>
    store.activeJob?.result ? JSON.stringify(store.activeJob.result, null, 2) : ''
  )

  const activeErrorText = computed(() =>
    store.activeJob?.error ? String(store.activeJob.error) : ''
  )

  const waitForJobDone = async (jobId, timeoutMs = 20 * 60 * 1000, pollMs = 1200) => {
    const startedAt = Date.now()
    while (Date.now() - startedAt <= timeoutMs) {
      let current = null
      try {
        current = await store.fetchJob(jobId, { silent: true })
      } catch (err) {
        if (err?.response?.status === 404) {
          throw new Error(`任务 ${jobId} 已被移除`)
        }
        throw err
      }
      if (current?.id === jobId && ['succeeded', 'failed', 'cancelled'].includes(current.status)) {
        await store.fetchJobs()
        if (current.status === 'failed' || current.status === 'cancelled') {
          throw new Error(current.error || `任务 ${jobId} 执行失败`)
        }
        return current
      }
      await sleep(pollMs)
    }
    throw new Error(`任务 ${jobId} 超时未完成`)
  }

  const runTrackedJob = async ({ startJob, timeoutMs = 20 * 60 * 1000, onDone, onError }) => {
    trackedJobRunning.value = true
    try {
      const job = await startJob()
      await store.fetchJob(job.id)
      const done = await waitForJobDone(job.id, timeoutMs)
      if (typeof onDone === 'function') {
        await onDone(done)
      }
      return done
    } catch (err) {
      if (typeof onError === 'function') {
        onError(err)
      }
      throw err
    } finally {
      trackedJobRunning.value = false
    }
  }

  return {
    jobStats,
    lastUpdateSummary,
    latestJobByType,
    refreshJobs,
    selectJob,
    removeJob,
    batchDeleteFinished,
    batchDeleteFailed,
    exportUrl,
    jobExportSections,
    activeParamsText,
    activeResultText,
    activeErrorText,
    waitForJobDone,
    runTrackedJob
  }
}
