import { computed } from 'vue'
import { usePortfolioSelection } from './usePortfolioSelection'

export function usePrepareWorkflow({
  store,
  market,
  query,
  kind,
  pageSize,
  selectedSymbols,
  updateForm,
  backtestForm,
  gridForm,
  toolForm,
  syncMlSymbols,
  splitSymbolInput,
  normalizeSymbolsInputForUi
}) {
  const searchSymbolsPage = async (page) => {
    await store.searchSymbols({
      market: market.value,
      q: query.value,
      kind: kind.value,
      page,
      pageSize: pageSize.value
    })
  }

  const syncSelectedSymbols = () => {
    const text = normalizeSymbolsInputForUi(selectedSymbols.value.join(', '))
    backtestForm.symbols = text
    gridForm.symbols = text
    toolForm.symbols = text
    syncMlSymbols(text)
    updateForm.symbols = text
  }

  const addSymbol = (symbol) => {
    if (!symbol || selectedSymbols.value.includes(symbol)) return
    selectedSymbols.value = [...selectedSymbols.value, symbol]
    syncSelectedSymbols()
  }

  const isSelected = (symbol) => selectedSymbols.value.includes(symbol)

  const removeSymbol = (symbol) => {
    selectedSymbols.value = selectedSymbols.value.filter((item) => item !== symbol)
    syncSelectedSymbols()
  }

  const toggleSymbol = (symbol) => {
    if (isSelected(symbol)) {
      removeSymbol(symbol)
      return
    }
    addSymbol(symbol)
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

  const search = async () => {
    await searchSymbolsPage(1)
  }

  const importSymbols = async () => {
    const data = await store.importSymbols(market.value)
    if (data) {
      await searchSymbolsPage(1)
    }
  }

  const importAllSymbols = async () => {
    const data = await store.importSymbols('CN')
    if (data) {
      await searchSymbolsPage(1)
    }
  }

  const totalPages = computed(() => Math.max(1, Math.ceil(store.total / Math.max(1, Number(pageSize.value || 20)))))

  const changePage = async (nextPage) => {
    if (nextPage < 1 || nextPage > totalPages.value) return
    await searchSymbolsPage(nextPage)
  }

  const applyPageSize = async () => {
    await searchSymbolsPage(1)
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
      source_order: 'akshare,abupy',
      quick_fail: true,
      symbol_timeout_sec: 20,
      coverage_mode: 'all',
      min_kline_rows: updateForm.min_kline_rows,
      symbols: symbols || undefined,
      all: !symbols
    })
    await store.fetchJob(job.id)
  }

  const runMarketCoverageUpdate = async () => {
    await store.importSymbols(updateForm.market || market.value || 'CN')
    const job = await store.startKlUpdate({
      market: updateForm.market,
      n_folds: updateForm.n_folds,
      start: updateForm.start || undefined,
      end: updateForm.end || undefined,
      how: updateForm.how,
      n_jobs: updateForm.n_jobs,
      source_order: 'akshare,abupy',
      quick_fail: true,
      symbol_timeout_sec: 20,
      coverage_mode: updateForm.coverage_mode || 'below_min_rows',
      min_kline_rows: updateForm.min_kline_rows,
      symbols: undefined,
      all: true
    })
    await store.fetchJob(job.id)
  }

  const runFullAshareUpdate = async () => {
    await store.importSymbols('CN')
    const job = await store.startKlUpdate({
      market: 'CN',
      n_folds: updateForm.n_folds,
      start: updateForm.start || undefined,
      end: updateForm.end || undefined,
      how: updateForm.how,
      n_jobs: updateForm.n_jobs,
      source_order: 'akshare,abupy',
      quick_fail: true,
      symbol_timeout_sec: 20,
      coverage_mode: 'all',
      min_kline_rows: updateForm.min_kline_rows,
      symbols: undefined,
      all: true
    })
    await store.fetchJob(job.id)
  }

  const portfolioSelection = usePortfolioSelection({
    selectedSymbols,
    syncSelectedSymbols,
    splitSymbolInput
  })

  return {
    totalPages,
    searchSymbolsPage,
    search,
    importSymbols,
    importAllSymbols,
    addSymbol,
    isSelected,
    toggleSymbol,
    removeSymbol,
    clearSymbols,
    selectPage,
    invertPage,
    syncSelectedSymbols,
    changePage,
    applyPageSize,
    runKlUpdate,
    runMarketCoverageUpdate,
    runFullAshareUpdate,
    ...portfolioSelection
  }
}
