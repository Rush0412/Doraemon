import { defineStore } from 'pinia'
import { api } from '../services/api'

export const useQuantStore = defineStore('quant', {
  state: () => ({
    market: 'CN',
    query: '',
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
    async searchSymbols({ market, q, limit = 50 } = {}) {
      const nextMarket = market ?? this.market
      const nextQuery = q ?? this.query
      this.market = nextMarket
      this.query = nextQuery

      this.symbolsLoading = true
      this.symbolsError = null
      try {
        const { data } = await api.get('/quant/symbols', {
          params: { market: nextMarket, q: nextQuery, limit }
        })
        this.symbols = data.data || []
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
    }
  }
})

