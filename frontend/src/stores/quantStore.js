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
    activeJobLoading: false
  }),
  actions: {
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
    async fetchJobs(limit = 50) {
      this.jobsLoading = true
      this.jobsError = null
      try {
        const { data } = await api.get('/jobs/', { params: { limit } })
        this.jobs = data.data || []
      } catch (err) {
        this.jobsError = err.message
      } finally {
        this.jobsLoading = false
      }
    },
    async fetchJob(id) {
      this.activeJobLoading = true
      try {
        const { data } = await api.get(`/jobs/${id}`)
        this.activeJob = data.data
      } finally {
        this.activeJobLoading = false
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
      await this.fetchJobs()
      return job
    },
    async startKlUpdate(params = {}) {
      const { data } = await api.post('/quant/kl/update', params)
      const job = data.data
      this.activeJob = job
      await this.fetchJobs()
      return job
    },
    async startBacktest(params = {}) {
      const { data } = await api.post('/quant/backtest', params)
      const job = data.data
      this.activeJob = job
      await this.fetchJobs()
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
      await this.fetchJobs()
      return job
    },
    async startQuantTool(params = {}) {
      const { data } = await api.post('/quant/tools', params)
      const job = data.data
      this.activeJob = job
      await this.fetchJobs()
      return job
    }
  }
})
