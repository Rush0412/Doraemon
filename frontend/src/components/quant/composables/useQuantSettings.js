import { nextTick, ref } from 'vue'

const SETTINGS_KEY = 'doraemon_quant_settings_v1'
const SETTINGS_SCHEMA_VERSION = 2

const plainObject = (value) => {
  try {
    return JSON.parse(JSON.stringify(value ?? {}))
  } catch {
    return {}
  }
}

const restoreAdviceTemplates = (payload, adviceTemplates) => {
  if (!payload || typeof payload !== 'object') return
  ;['conservative', 'balanced', 'aggressive'].forEach((key) => {
    const source = payload[key]
    const target = adviceTemplates[key]
    if (!source || !target) return
    if (typeof source.label === 'string' && source.label.trim()) target.label = source.label
    if (source.position && typeof source.position === 'object') {
      Object.assign(target.position, source.position)
    }
    if (source.entry && typeof source.entry === 'object') {
      Object.assign(target.entry, source.entry)
    }
    if (source.takeProfit && typeof source.takeProfit === 'object') {
      Object.assign(target.takeProfit, source.takeProfit)
    }
    if (source.trailStopPct !== undefined) {
      target.trailStopPct = Number(source.trailStopPct)
    }
  })
}

export const useQuantSettings = ({
  market,
  query,
  kind,
  pageSize,
  backtestForm,
  gridForm,
  toolForm,
  updateForm,
  buyStrategyId,
  sellStrategyId,
  buyStrategyParams,
  sellStrategyParams,
  gridBuyParamLists,
  gridSellParamLists,
  gridUseBacktestBase,
  gridExploreAllStrategies,
  adviceProfile,
  adviceTemplates
}) => {
  const settingsReady = ref(false)
  let settingsSaveTimer = null

  const saveQuantSettings = () => {
    if (!settingsReady.value) return
    const snapshot = {
      settingsVersion: SETTINGS_SCHEMA_VERSION,
      market: market.value,
      query: query.value,
      kind: kind.value,
      pageSize: pageSize.value,
      backtestForm: plainObject(backtestForm),
      gridForm: plainObject(gridForm),
      toolForm: plainObject(toolForm),
      updateForm: plainObject(updateForm),
      buyStrategyId: buyStrategyId.value,
      sellStrategyId: sellStrategyId.value,
      buyStrategyParams: plainObject(buyStrategyParams),
      sellStrategyParams: plainObject(sellStrategyParams),
      gridBuyParamLists: plainObject(gridBuyParamLists),
      gridSellParamLists: plainObject(gridSellParamLists),
      gridUseBacktestBase: !!gridUseBacktestBase.value,
      gridExploreAllStrategies: !!gridExploreAllStrategies.value,
      adviceProfile: adviceProfile.value,
      adviceTemplates: plainObject(adviceTemplates),
    }
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(snapshot))
    } catch {
      // ignore storage write error
    }
  }

  const scheduleSaveQuantSettings = () => {
    if (!settingsReady.value) return
    if (settingsSaveTimer) clearTimeout(settingsSaveTimer)
    settingsSaveTimer = setTimeout(() => {
      saveQuantSettings()
      settingsSaveTimer = null
    }, 180)
  }

  const restoreQuantSettings = async () => {
    try {
      const raw = localStorage.getItem(SETTINGS_KEY)
      if (!raw) return
      const snapshot = JSON.parse(raw)
      if (!snapshot || typeof snapshot !== 'object') return
      const settingsVersion = Number(snapshot.settingsVersion || 1)
      if (typeof snapshot.market === 'string' && snapshot.market.trim()) market.value = snapshot.market
      if (typeof snapshot.query === 'string') query.value = snapshot.query
      if (typeof snapshot.kind === 'string') kind.value = snapshot.kind
      if (Number.isFinite(Number(snapshot.pageSize)) && Number(snapshot.pageSize) > 0) {
        pageSize.value = Number(snapshot.pageSize)
      }
      if (snapshot.updateForm && typeof snapshot.updateForm === 'object') Object.assign(updateForm, snapshot.updateForm)
      if (snapshot.backtestForm && typeof snapshot.backtestForm === 'object') Object.assign(backtestForm, snapshot.backtestForm)
      if (snapshot.gridForm && typeof snapshot.gridForm === 'object') Object.assign(gridForm, snapshot.gridForm)
      const restoredMaxRuns = Number(gridForm.max_runs)
      if (!Number.isFinite(restoredMaxRuns) || restoredMaxRuns <= 0) {
        gridForm.max_runs = 50
      } else if (settingsVersion < SETTINGS_SCHEMA_VERSION && restoredMaxRuns === 30) {
        // Migrate legacy cached default (30) to new default (50).
        gridForm.max_runs = 50
      } else {
        gridForm.max_runs = restoredMaxRuns
      }
      if (!gridForm.ranking_weights || typeof gridForm.ranking_weights !== 'object') {
        gridForm.ranking_weights = {}
      }
      gridForm.ranking_weights = {
        profit: Number(gridForm.ranking_weights.profit ?? 1),
        win_rate: Number(gridForm.ranking_weights.win_rate ?? 1),
        sharpe: Number(gridForm.ranking_weights.sharpe ?? 1),
        annual_return: Number(gridForm.ranking_weights.annual_return ?? 1),
        drawdown: Number(gridForm.ranking_weights.drawdown ?? 1)
      }
      if (snapshot.toolForm && typeof snapshot.toolForm === 'object') Object.assign(toolForm, snapshot.toolForm)
      if (typeof snapshot.buyStrategyId === 'string' && snapshot.buyStrategyId.trim()) {
        buyStrategyId.value = snapshot.buyStrategyId
      }
      if (typeof snapshot.sellStrategyId === 'string' && snapshot.sellStrategyId.trim()) {
        sellStrategyId.value = snapshot.sellStrategyId
      }
      if (snapshot.gridUseBacktestBase !== undefined) {
        gridUseBacktestBase.value = !!snapshot.gridUseBacktestBase
      }
      if (snapshot.gridExploreAllStrategies !== undefined) {
        gridExploreAllStrategies.value = !!snapshot.gridExploreAllStrategies
      }
      if (typeof snapshot.adviceProfile === 'string' && snapshot.adviceProfile.trim()) {
        adviceProfile.value = snapshot.adviceProfile
      }
      restoreAdviceTemplates(snapshot.adviceTemplates, adviceTemplates)
      await nextTick()
      if (snapshot.buyStrategyParams && typeof snapshot.buyStrategyParams === 'object') {
        Object.assign(buyStrategyParams, snapshot.buyStrategyParams)
      }
      if (snapshot.sellStrategyParams && typeof snapshot.sellStrategyParams === 'object') {
        Object.assign(sellStrategyParams, snapshot.sellStrategyParams)
      }
      if (snapshot.gridBuyParamLists && typeof snapshot.gridBuyParamLists === 'object') {
        Object.assign(gridBuyParamLists, snapshot.gridBuyParamLists)
      }
      if (snapshot.gridSellParamLists && typeof snapshot.gridSellParamLists === 'object') {
        Object.assign(gridSellParamLists, snapshot.gridSellParamLists)
      }
    } catch {
      // ignore malformed storage
    }
  }

  const clearSettingsSaveTimer = () => {
    if (settingsSaveTimer) {
      clearTimeout(settingsSaveTimer)
      settingsSaveTimer = null
    }
  }

  return {
    settingsReady,
    restoreQuantSettings,
    scheduleSaveQuantSettings,
    clearSettingsSaveTimer
  }
}
