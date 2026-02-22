import { SYMBOL_SPLIT_REGEX } from './symbols'

export const applyStrategyDefaults = (strategy, target) => {
  if (!strategy || !Array.isArray(strategy.params)) return
  strategy.params.forEach((param) => {
    if (target[param.key] === undefined) {
      target[param.key] = param.default
    }
  })
}

export const resetStrategyParams = (strategy, target) => {
  Object.keys(target).forEach((key) => {
    delete target[key]
  })
  if (!strategy || !Array.isArray(strategy.params)) return
  strategy.params.forEach((param) => {
    target[param.key] = param.default
  })
}

export const gridFallbackValue = (param, fallbackLists = {}) => {
  if (param.key === 'xd' && fallbackLists.buy_xd_list) return String(fallbackLists.buy_xd_list)
  if (param.key === 'stop_loss_n' && fallbackLists.stop_loss_n_list) return String(fallbackLists.stop_loss_n_list)
  if (param.key === 'stop_win_n' && fallbackLists.stop_win_n_list) return String(fallbackLists.stop_win_n_list)
  if (param.default === undefined || param.default === null) return ''
  return String(param.default)
}

export const applyGridDefaults = (strategy, target, fallbackLists = {}) => {
  if (!strategy || !Array.isArray(strategy.params)) return
  strategy.params.forEach((param) => {
    if (target[param.key] === undefined) {
      target[param.key] = gridFallbackValue(param, fallbackLists)
    }
  })
}

export const resetGridParamLists = (strategy, target, fallbackLists = {}) => {
  Object.keys(target).forEach((key) => {
    delete target[key]
  })
  if (!strategy || !Array.isArray(strategy.params)) return
  strategy.params.forEach((param) => {
    target[param.key] = gridFallbackValue(param, fallbackLists)
  })
}

export const parseStringList = (raw) =>
  String(raw)
    .split(SYMBOL_SPLIT_REGEX)
    .map((item) => item.trim())
    .filter(Boolean)

export const parseNumberList = (raw) =>
  String(raw)
    .split(SYMBOL_SPLIT_REGEX)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item))

export const parseBooleanList = (raw) =>
  parseStringList(raw).map((item) => {
    const value = item.toLowerCase()
    return ['true', '1', 'yes', 'y'].includes(value)
  })

export const buildGridParamPayload = (strategy, source) => {
  if (!strategy || !Array.isArray(strategy.params)) return {}
  const payload = {}
  strategy.params.forEach((param) => {
    const raw = source[param.key]
    if (raw === undefined || raw === null || String(raw).trim() === '') return
    if (param.type === 'bool') {
      const list = parseBooleanList(raw)
      if (list.length) payload[param.key] = list
      return
    }
    if (param.type === 'int') {
      const list = parseNumberList(raw).map((item) => Math.round(item))
      if (list.length) payload[param.key] = list
      return
    }
    if (param.type === 'float') {
      const list = parseNumberList(raw)
      if (list.length) payload[param.key] = list
      return
    }
    const list = parseStringList(raw)
    if (list.length) payload[param.key] = list
  })
  return payload
}
