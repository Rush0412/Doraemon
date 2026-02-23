import { defineStore } from 'pinia'
import { api } from '../services/api'

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
      const rest = rows.filter((item) => item?.id !== job.id)
      this.jobs = [job, ...rest]
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
        this.activeJob = data.data
        this._upsertJob(data.data)
      } finally {
        if (!silent) this.activeJobLoading = false
      }
    },
    async deleteJob(id) {
      await api.delete(`/jobs/${id}`)
      this.jobs = this.jobs.filter((job) => job.id !== id)
      if (this.activeJob?.id === id) {
        this.activeJob = null
      }
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
    async fetchMlModels({ market = 'CN', target = 'y_up_5d', limit = 100 } = {}) {
      this.mlLoading = true
      this.mlError = null
      try {
        const { data } = await api.get('/quant/ml/models', {
          params: { market, target, limit }
        })
        this.mlModels = Array.isArray(data.data) ? data.data : []
      } catch (err) {
        this.mlError = err.message
      } finally {
        this.mlLoading = false
      }
    },
    async fetchMlPredictions({ market = 'CN', modelId = null, limit = 100 } = {}) {
      this.mlLoading = true
      this.mlError = null
      try {
        const params = { market, limit }
        if (modelId) params.model_id = modelId
        const { data } = await api.get('/quant/ml/predictions', { params })
        this.mlPredictions = Array.isArray(data.data) ? data.data : []
      } catch (err) {
        this.mlError = err.message
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
