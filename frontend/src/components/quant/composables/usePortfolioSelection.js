import { ref } from 'vue'

const INDEX_KEY = 'doraemon_portfolios'
const PORTFOLIO_KEY_PREFIX = 'doraemon_portfolio_'

const safeJsonParse = (raw, fallback) => {
  try {
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

const normalizePortfolioList = (value) => {
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item || '').trim()).filter(Boolean)
}

export function usePortfolioSelection({ selectedSymbols, syncSelectedSymbols, splitSymbolInput }) {
  const savedPortfolios = ref([])
  const selectedPortfolio = ref('')
  const portfolioDraftName = ref('')
  const portfolioSaveOpen = ref(false)
  const portfolioSaveError = ref('')

  const refreshPortfolioIndex = () => {
    savedPortfolios.value = normalizePortfolioList(safeJsonParse(localStorage.getItem(INDEX_KEY) || '[]', []))
  }

  const openSaveSelection = () => {
    portfolioDraftName.value = selectedPortfolio.value || ''
    portfolioSaveError.value = ''
    portfolioSaveOpen.value = true
  }

  const cancelSaveSelection = () => {
    portfolioSaveOpen.value = false
    portfolioSaveError.value = ''
  }

  const confirmSaveSelection = () => {
    const trimmed = String(portfolioDraftName.value || '').trim()
    if (!trimmed) {
      portfolioSaveError.value = '请输入组合名称'
      return false
    }
    const payload = { name: trimmed, symbols: selectedSymbols.value }
    localStorage.setItem(`${PORTFOLIO_KEY_PREFIX}${trimmed}`, JSON.stringify(payload))
    const list = normalizePortfolioList(safeJsonParse(localStorage.getItem(INDEX_KEY) || '[]', []))
    if (!list.includes(trimmed)) list.push(trimmed)
    localStorage.setItem(INDEX_KEY, JSON.stringify(list))
    savedPortfolios.value = list
    selectedPortfolio.value = trimmed
    portfolioSaveOpen.value = false
    portfolioSaveError.value = ''
    return true
  }

  const loadPortfolio = () => {
    if (!selectedPortfolio.value) return
    const raw = localStorage.getItem(`${PORTFOLIO_KEY_PREFIX}${selectedPortfolio.value}`)
    if (!raw) return
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed?.symbols)) selectedSymbols.value = parsed.symbols
      else if (typeof parsed === 'string') selectedSymbols.value = splitSymbolInput(parsed)
      else selectedSymbols.value = []
      syncSelectedSymbols()
    } catch {
      // ignore malformed payload
    }
  }

  const deletePortfolio = () => {
    if (!selectedPortfolio.value) return
    localStorage.removeItem(`${PORTFOLIO_KEY_PREFIX}${selectedPortfolio.value}`)
    const list = normalizePortfolioList(safeJsonParse(localStorage.getItem(INDEX_KEY) || '[]', [])).filter(
      (name) => name !== selectedPortfolio.value
    )
    localStorage.setItem(INDEX_KEY, JSON.stringify(list))
    savedPortfolios.value = list
    selectedPortfolio.value = ''
    cancelSaveSelection()
  }

  return {
    savedPortfolios,
    selectedPortfolio,
    portfolioDraftName,
    portfolioSaveOpen,
    portfolioSaveError,
    refreshPortfolioIndex,
    openSaveSelection,
    cancelSaveSelection,
    confirmSaveSelection,
    loadPortfolio,
    deletePortfolio
  }
}
