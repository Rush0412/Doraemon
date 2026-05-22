import { defineStore } from 'pinia'
import { api } from '../services/api'

const isIgnorableRequestError = (err) => /request aborted|aborted|canceled|cancelled/i.test(String(err?.message || ''))

export const useQuantStore = defineStore('quant', {
  state: () => ({
    market: 'SH',
    query: '',
    kind: 'stock',
    page: 1,
    pageSize: 20,
    total: 0,
    symbols: [],
    symbolsLoading: false,
    symbolsError: null,
    jobs: [],
    jobsLoading: false,
    jobsError: null,
    activeJob: null,
    activeJobLoading: false,
    strategies: { buy: [], sell: [] },
    strategiesLoading: false,
    strategiesError: null,
    mlModels: [],
    mlPredictions: [],
    mlLoading: false,
    mlError: null
  }),
  actions: {
    _upsertJob(job) {
      if (!job || typeof job !== 'object') return
      const rows = Array.isArray(this.jobs) ? this.jobs : []
      const merged = [job, ...rows.filter((item) => item?.id !== job.id)]
      this.jobs = merged.sort((a, b) => Number(b?.id || 0) - Number(a?.id || 0))
    },
    async searchSymbols({ market, q, kind, page, pageSize } = {}) {
      const nextMarket = market ?? this.market
      const nextQuery = q ?? this.query
      const nextKind = kind ?? this.kind
      const nextPage = page ?? this.page
      const nextPageSize = pageSize ?? this.pageSize
      this.market = nextMarket
      this.query = nextQuery
      this.kind = nextKind
      this.page = nextPage
      this.pageSize = nextPageSize

      this.symbolsLoading = true
      this.symbolsError = null
      try {
        const { data } = await api.get('/quant/symbols', {
          params: {
            market: nextMarket,
            q: nextQuery,
            kind: nextKind,
            page: nextPage,
            page_size: nextPageSize
          }
        })
        const payload = data.data || {}
        this.symbols = payload.items || []
        this.total = payload.total || 0
        this.page = payload.page || nextPage
        this.pageSize = payload.page_size || nextPageSize
      } catch (err) {
        this.symbolsError = err.message
      } finally {
        this.symbolsLoading = false
      }
    },
    async fetchJobs(limit = 50, options = {}) {
      const silent = !!options.silent
      if (!silent) this.jobsLoading = true
      this.jobsError = null
      try {
        const { data } = await api.get('/jobs/', { params: { limit } })
        this.jobs = data.data || []
      } catch (err) {
        this.jobsError = err.message
      } finally {
        if (!silent) this.jobsLoading = false
      }
    },
    async fetchJob(id, options = {}) {
      const silent = !!options.silent
      if (!silent) this.activeJobLoading = true
      try {
        const { data } = await api.get(`/jobs/${id}`)
        const job = data.data
        this.activeJob = job
        this._upsertJob(job)
        return job
      } catch (err) {
        if (!silent) this.jobsError = err.message
        throw err
      } finally {
        if (!silent) this.activeJobLoading = false
      }
    },
    async deleteJob(id, options = {}) {
      const params = {}
      if (options.force) params.force = true
      await api.delete(`/jobs/${id}`, { params })
      this.jobs = this.jobs.filter((job) => job.id !== id)
      if (this.activeJob?.id === id) {
        this.activeJob = null
      }
    },
    async deleteJobsBatch(payload = { delete_finished: true }) {
      const { data } = await api.post('/jobs/batch-delete', payload)
      const deletedIds = Array.isArray(data?.data?.deleted_ids) ? data.data.deleted_ids : []
      if (deletedIds.length) {
        const idSet = new Set(deletedIds)
        this.jobs = this.jobs.filter((job) => !idSet.has(job.id))
        if (this.activeJob?.id && idSet.has(this.activeJob.id)) {
          this.activeJob = null
        }
      }
      return data.data || { deleted_ids: [], skipped_running_ids: [], matched: 0 }
    },
    async startVerify() {
      const { data } = await api.get('/quant/verify')
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async startKlUpdate(params = {}) {
      const { data } = await api.post('/quant/kl/update', params)
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async startBacktest(params = {}) {
      const { data } = await api.post('/quant/backtest', params)
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async importSymbols(market = 'CN') {
      this.symbolsLoading = true
      this.symbolsError = null
      try {
        const { data } = await api.post('/quant/symbols/import', { market })
        return data.data
      } catch (err) {
        this.symbolsError = err.message
        return null
      } finally {
        this.symbolsLoading = false
      }
    },
    async startGridSearch(params = {}) {
      const { data } = await api.post('/quant/grid-search', params)
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async startStockSelect(params = {}) {
      const { data } = await api.post('/quant/stock-select', params)
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async startQuantTool(params = {}) {
      const { data } = await api.post('/quant/tools', params)
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async runTrendAnalysisDemo(params = {}) {
      const { data } = await api.post('/quant/trend-analysis/demo', params)
      return data.data
    },
    async startMlFeatureBuild(params = {}) {
      const { data } = await api.post('/quant/ml/features/build', params)
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async startMlTrain(params = {}) {
      const { data } = await api.post('/quant/ml/train', params)
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async startMlPredict(params = {}) {
      const { data } = await api.post('/quant/ml/predict', params)
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async startMlStockSelect(params = {}) {
      const { data } = await api.post('/quant/ml/stock-select', params)
      const job = data.data
      this.activeJob = job
      this._upsertJob(job)
      return job
    },
    async fetchMlModels({ market = 'CN', target = 'y_up_5d', limit = 100 } = {}) {
      this.mlLoading = true
      this.mlError = null
      try {
        const { data } = await api.get('/quant/ml/models', {
          params: { market, target, limit }
        })
        this.mlModels = Array.isArray(data.data) ? data.data : []
      } catch (err) {
        if (!isIgnorableRequestError(err)) {
          this.mlError = err.message
        }
      } finally {
        this.mlLoading = false
      }
    },
    async fetchMlPredictions({
      market = 'CN',
      target = 'y_up_5d',
      modelId = null,
      limit = 100,
      actions = null,
      recommendedOnly = true,
      uniqueSymbols = true
    } = {}) {
      this.mlLoading = true
      this.mlError = null
      try {
        const params = {
          market,
          target,
          limit,
          recommended_only: recommendedOnly,
          unique_symbols: uniqueSymbols
        }
        if (modelId) params.model_id = modelId
        if (actions) params.actions = actions
        const { data } = await api.get('/quant/ml/predictions', { params })
        this.mlPredictions = Array.isArray(data.data) ? data.data : []
      } catch (err) {
        if (!isIgnorableRequestError(err)) {
          this.mlError = err.message
        }
      } finally {
        this.mlLoading = false
      }
    },
    async promoteMlModel(modelId) {
      const { data } = await api.post(`/quant/ml/models/${modelId}/promote`)
      return data.data
    },
    async fetchStrategies() {
      this.strategiesLoading = true
      this.strategiesError = null
      try {
        const { data } = await api.get('/quant/strategies')
        this.strategies = data.data || { buy: [], sell: [] }
      } catch (err) {
        this.strategiesError = err.message
      } finally {
        this.strategiesLoading = false
      }
    }
  }
})
