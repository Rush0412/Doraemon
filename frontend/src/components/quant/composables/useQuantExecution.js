import { computed, nextTick } from 'vue'
import { buildGridParamPayload, parseStringList, resetStrategyParams } from '../utils/strategyGrid'

const toFiniteNumberOrNull = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

const pickGridMetric = (run, key, fallback = 0) => {
  if (!run) return fallback
  const validationValue = run[`validation_${key}`]
  if (validationValue !== undefined && validationValue !== null && Number.isFinite(Number(validationValue))) {
    return Number(validationValue)
  }
  const raw = run[key]
  if (raw !== undefined && raw !== null && Number.isFinite(Number(raw))) {
    return Number(raw)
  }
  return fallback
}

const normalizePredictionSignal = (symbol, signal) => {
  if (!signal || typeof signal !== 'object') return null
  return {
    symbol: String(symbol || signal.symbol || '').trim(),
    trade_date: signal.trade_date || null,
    action: String(signal.action || '').trim().toLowerCase() || null,
    score_up_5d: toFiniteNumberOrNull(signal.score_up_5d),
    expected_ret_5d: toFiniteNumberOrNull(signal.expected_ret_5d),
    stop_loss: toFiniteNumberOrNull(signal.stop_loss),
    take_profit: toFiniteNumberOrNull(signal.take_profit),
    entry_price: toFiniteNumberOrNull(signal.entry_price),
    position_min: toFiniteNumberOrNull(signal.position_min),
    position_max: toFiniteNumberOrNull(signal.position_max)
  }
}

export function useQuantExecution({
  store,
  market,
  activeTab,
  flowRunning,
  strategyError,
  chartSymbol,
  predictionSignal,
  klineError,
  backtestForm,
  gridForm,
  toolForm,
  toolOptions,
  buyStrategyId,
  sellStrategyId,
  buyStrategyParams,
  sellStrategyParams,
  activeBuyStrategy,
  activeSellStrategy,
  buyStrategies,
  sellStrategies,
  gridBuyParamLists,
  gridSellParamLists,
  gridUseBacktestBase,
  gridExploreAllStrategies,
  gridJob,
  waitForJobDone,
  runTrackedJob,
  loadKlineChart,
  inferMarketBySymbol,
  inferMarketBySymbols,
  normalizeSymbolsInputForUi
}) {
  const gridTopRuns = computed(() => {
    const runs = Array.isArray(gridJob.value?.result?.runs) ? gridJob.value.result.runs : []
    return runs.slice(0, 10).map((run, idx) => ({
      ...run,
      rank: idx + 1,
      score: Number(
        (
          Number.isFinite(Number(run?.custom_score))
            ? Number(run.custom_score)
            : pickGridMetric(run, 'profit_sum') * 0.55 +
              pickGridMetric(run, 'win_rate') * 0.25 +
              pickGridMetric(run, 'sharpe') * 10 -
              pickGridMetric(run, 'max_drawdown') * 100
        ).toFixed(2)
      )
    }))
  })

  const toolOptionMode = computed(() => {
    if (toolForm.tool === 'support_resistance') return 'support'
    if (toolForm.tool === 'jump_gap') return 'jump'
    if (toolForm.tool === 'trend_speed') return 'trend'
    if (toolForm.tool === 'shift_distance') return 'shift'
    if (toolForm.tool === 'regress' || toolForm.tool === 'price_channel') return 'regress'
    if (toolForm.tool === 'correlation') return 'corr'
    if (toolForm.tool === 'distance') return 'distance'
    return 'base'
  })

  const applyGridCandidateToBacktest = async (candidate) => {
    if (!candidate) return
    if (candidate.buy_strategy) {
      buyStrategyId.value = candidate.buy_strategy
    }
    if (candidate.sell_strategy) {
      sellStrategyId.value = candidate.sell_strategy
    }
    await nextTick()
    if (candidate.buy_params) {
      resetStrategyParams(activeBuyStrategy.value, buyStrategyParams)
      Object.assign(buyStrategyParams, candidate.buy_params)
      if (candidate.buy_params.xd !== undefined) {
        backtestForm.buy_xd = Number(candidate.buy_params.xd) || backtestForm.buy_xd
      }
    }
    if (candidate.sell_params) {
      resetStrategyParams(activeSellStrategy.value, sellStrategyParams)
      Object.assign(sellStrategyParams, candidate.sell_params)
      if (candidate.sell_params.stop_loss_n !== undefined) {
        const val = Number(candidate.sell_params.stop_loss_n)
        if (Number.isFinite(val)) backtestForm.stop_loss_n = val
      }
      if (candidate.sell_params.stop_win_n !== undefined) {
        const val = Number(candidate.sell_params.stop_win_n)
        if (Number.isFinite(val)) backtestForm.stop_win_n = val
      }
    }
    if (candidate.buy_xd !== undefined) {
      const val = Number(candidate.buy_xd)
      if (Number.isFinite(val) && val > 0) backtestForm.buy_xd = val
    }
    if (candidate.stop_loss_n !== undefined) {
      const val = Number(candidate.stop_loss_n)
      if (Number.isFinite(val)) backtestForm.stop_loss_n = val
    }
    if (candidate.stop_win_n !== undefined) {
      const val = Number(candidate.stop_win_n)
      if (Number.isFinite(val)) backtestForm.stop_win_n = val
    }
    if (Array.isArray(candidate.symbols) && candidate.symbols.length) {
      backtestForm.symbols = normalizeSymbolsInputForUi(candidate.symbols.join(', '))
    }
    if (typeof candidate.symbol === 'string' && candidate.symbol.trim()) {
      backtestForm.symbols = normalizeSymbolsInputForUi(candidate.symbol.trim())
      chartSymbol.value = candidate.symbol.trim()
    }
    if (candidate.market) backtestForm.market = candidate.market
    activeTab.value = 'strategy'
  }

  const applyGridToBacktest = async () => {
    await applyGridCandidateToBacktest(gridJob.value?.result?.best || null)
  }

  const applyGridRunToBacktest = async (run) => {
    await applyGridCandidateToBacktest(run)
  }

  const applyGridNextSuggestions = () => {
    const next = gridJob.value?.result?.next_param_suggestions
    if (!next || typeof next !== 'object') return
    if (next.buy_params_grid && typeof next.buy_params_grid === 'object') {
      Object.entries(next.buy_params_grid).forEach(([key, values]) => {
        if (!Array.isArray(values)) return
        gridBuyParamLists[key] = values.join(', ')
      })
    }
    if (next.sell_params_grid && typeof next.sell_params_grid === 'object') {
      Object.entries(next.sell_params_grid).forEach(([key, values]) => {
        if (!Array.isArray(values)) return
        gridSellParamLists[key] = values.join(', ')
      })
    }
  }

  const applySymbolToBacktest = (symbol, signal = null) => {
    if (!symbol) return
    const text = String(symbol).trim()
    if (!text) return
    backtestForm.symbols = normalizeSymbolsInputForUi(text)
    backtestForm.market = inferMarketBySymbol(text, market.value || 'SH')
    chartSymbol.value = text
    predictionSignal.value = normalizePredictionSignal(text, signal)
    activeTab.value = 'strategy'
  }

  const buildToolOptions = () => {
    const opts = {}
    if (toolForm.tool === 'support_resistance') opts.only_last = toolOptions.only_last
    if (toolForm.tool === 'jump_gap') {
      opts.mode = toolOptions.mode
      opts.jump_diff_factor = toolOptions.jump_diff_factor
      opts.power_threshold = toolOptions.power_threshold
      opts.weight = [toolOptions.weight_a, toolOptions.weight_b]
    }
    if (toolForm.tool === 'trend_speed') {
      opts.benchmark = toolOptions.benchmark
      opts.resample = toolOptions.resample
      opts.speed_key = toolOptions.speed_key
    }
    if (toolForm.tool === 'shift_distance') {
      opts.step_x = toolOptions.step_x
      opts.mode = toolOptions.shift_mode
    }
    if (toolForm.tool === 'regress' || toolForm.tool === 'price_channel') {
      opts.mode = toolOptions.regress_mode
    }
    if (toolForm.tool === 'correlation') {
      opts.corr_type = toolOptions.corr_type
      opts.field = toolOptions.field
    }
    if (toolForm.tool === 'distance') {
      opts.distance_type = toolOptions.distance_type
      opts.field = toolOptions.field
    }
    return opts
  }

  const applySymbolToAnalysis = async (symbol) => {
    if (!symbol) return
    const text = String(symbol).trim()
    if (!text) return
    toolForm.symbols = normalizeSymbolsInputForUi(text)
    toolForm.market = inferMarketBySymbol(text, market.value || 'SH')
    activeTab.value = 'tools'
    await runTool()
  }

  const buildMlStockSelectPayload = (form) => {
    const rawSymbols = String(form.symbols || '').trim()
    const isMarketWide = !rawSymbols
    const marketWideLimitBase = Math.max(3000, Number(form.symbol_eval_limit || 0), Number(form.candidate_limit || 0))
    const predictionLimit = isMarketWide
      ? Math.max(marketWideLimitBase, Number(form.prediction_limit || 3000))
      : Number(form.prediction_limit || 300)
    const candidateLimit = isMarketWide
      ? Math.max(marketWideLimitBase, Number(form.candidate_limit || 3000))
      : Number(form.candidate_limit || 120)
    const evalLimit = isMarketWide
      ? Math.max(marketWideLimitBase, Number(form.symbol_eval_limit || candidateLimit))
      : Number(form.symbol_eval_limit || 120)
    return {
      market: form.market,
      target: form.target || 'y_up_5d',
      model_id: form.model_id || undefined,
      symbols: rawSymbols || undefined,
      full_market_scan: isMarketWide,
      min_score: Number(form.min_score || 0.55),
      prediction_limit: predictionLimit,
      candidate_limit: candidateLimit,
      symbol_top_n: Number(form.symbol_top_n || 20),
      symbol_eval_limit: evalLimit,
      min_kline_rows: Number(form.min_kline_rows || 120),
      n_folds: backtestForm.n_folds,
      start: backtestForm.start || undefined,
      end: backtestForm.end || undefined,
      cash: backtestForm.cash,
      commission_rate: backtestForm.commission_rate,
      min_commission: backtestForm.min_commission,
      stamp_tax_rate: backtestForm.stamp_tax_rate,
      slippage_bp: backtestForm.slippage_bp,
      buy_xd: backtestForm.buy_xd,
      stop_loss_n: backtestForm.stop_loss_n,
      stop_win_n: backtestForm.stop_win_n,
      buy_strategy: buyStrategyId.value,
      buy_params: { ...buyStrategyParams },
      sell_strategy: sellStrategyId.value,
      sell_params: { ...sellStrategyParams }
    }
  }

  const buildBacktestPayload = () => {
    const effectiveMarket = inferMarketBySymbols(backtestForm.symbols, backtestForm.market)
    backtestForm.market = effectiveMarket
    return {
      market: effectiveMarket,
      symbols: backtestForm.symbols,
      n_folds: backtestForm.n_folds,
      start: backtestForm.start || undefined,
      end: backtestForm.end || undefined,
      cash: backtestForm.cash,
      commission_rate: backtestForm.commission_rate,
      min_commission: backtestForm.min_commission,
      stamp_tax_rate: backtestForm.stamp_tax_rate,
      slippage_bp: backtestForm.slippage_bp,
      buy_xd: backtestForm.buy_xd,
      stop_loss_n: backtestForm.stop_loss_n,
      stop_win_n: backtestForm.stop_win_n,
      buy_strategy: buyStrategyId.value,
      buy_params: { ...buyStrategyParams },
      sell_strategy: sellStrategyId.value,
      sell_params: { ...sellStrategyParams },
      orders_preview_limit: 8000,
      actions_preview_limit: 8000
    }
  }

  const buildStockSelectPayload = () => {
    const rawSymbols = String(backtestForm.symbols || '').trim()
    const isMarketWide = !rawSymbols
    const fallbackCandidateLimit = isMarketWide
      ? Math.max(Number(gridForm.symbol_eval_limit || 120), 3000)
      : Math.max(Number(gridForm.symbol_eval_limit || 120), Number(gridForm.symbol_top_n || 10) * 3)
    const evalLimit = isMarketWide
      ? Math.max(Number(gridForm.symbol_eval_limit || fallbackCandidateLimit), fallbackCandidateLimit)
      : Number(gridForm.symbol_eval_limit || 120)
    const effectiveMarket = inferMarketBySymbols(rawSymbols, backtestForm.market)
    backtestForm.market = effectiveMarket
    return {
      market: effectiveMarket,
      symbols: rawSymbols || undefined,
      all_symbols: isMarketWide,
      full_market_scan: isMarketWide,
      candidate_limit: fallbackCandidateLimit,
      symbol_eval_limit: evalLimit,
      symbol_top_n: Number(gridForm.symbol_top_n || 10),
      min_kline_rows: 120,
      n_folds: backtestForm.n_folds,
      start: backtestForm.start || undefined,
      end: backtestForm.end || undefined,
      cash: backtestForm.cash,
      commission_rate: backtestForm.commission_rate,
      min_commission: backtestForm.min_commission,
      stamp_tax_rate: backtestForm.stamp_tax_rate,
      slippage_bp: backtestForm.slippage_bp,
      buy_xd: backtestForm.buy_xd,
      stop_loss_n: backtestForm.stop_loss_n,
      stop_win_n: backtestForm.stop_win_n,
      buy_strategy: buyStrategyId.value,
      buy_params: { ...buyStrategyParams },
      sell_strategy: sellStrategyId.value,
      sell_params: { ...sellStrategyParams }
    }
  }

  const runVerify = async () => {
    const job = await store.startVerify()
    await store.fetchJob(job.id)
  }

  const runBacktest = async () => {
    strategyError.value = ''
    try {
      const done = await runTrackedJob({
        startJob: () => store.startBacktest(buildBacktestPayload()),
        timeoutMs: 90 * 60 * 1000,
        onDone: async () => {
          activeTab.value = 'strategy'
          await nextTick()
          if (chartSymbol.value) {
            await loadKlineChart()
          }
        },
        onError: (err) => {
          strategyError.value = err?.message || String(err)
        }
      })
      return done
    } catch {
      return null
    }
  }

  const runStockSelect = async () => {
    strategyError.value = ''
    try {
      const done = await runTrackedJob({
        startJob: () => store.startStockSelect(buildStockSelectPayload()),
        timeoutMs: 90 * 60 * 1000,
        onError: (err) => {
          strategyError.value = err?.message || String(err)
        }
      })
      return done
    } catch {
      return null
    }
  }

  const runClosedLoop = async () => {
    flowRunning.value = true
    klineError.value = ''
    try {
      const selectQueued = await store.startStockSelect(buildStockSelectPayload())
      const selectDone = await waitForJobDone(selectQueued.id, 90 * 60 * 1000)
      const selectResult = selectDone?.result || {}
      const topSymbols = Array.isArray(selectResult.top_symbols)
        ? selectResult.top_symbols.map((item) => String(item.symbol || '').trim()).filter(Boolean)
        : []
      if (!topSymbols.length) {
        throw new Error('独立选股未返回可回测标的，请调整范围后重试。')
      }
      const picked = topSymbols.slice(0, Math.max(1, Number(gridForm.symbol_top_n || 10)))
      backtestForm.symbols = normalizeSymbolsInputForUi(picked.join(', '))
      chartSymbol.value = picked[0]
      const firstActionable = Array.isArray(selectResult.actionable_candidates)
        ? selectResult.actionable_candidates.find((item) => String(item?.symbol || '').trim() === picked[0])
        : null
      predictionSignal.value = normalizePredictionSignal(picked[0], {
        symbol: picked[0],
        trade_date: selectResult?.summary?.end || null,
        action: firstActionable?.action || null,
        stop_loss: firstActionable?.stop_loss,
        take_profit: firstActionable?.take_profit,
        entry_price: firstActionable?.last_close
      })
      const backtestQueued = await store.startBacktest(buildBacktestPayload())
      await waitForJobDone(backtestQueued.id, 90 * 60 * 1000)
      toolForm.market = backtestForm.market
      toolForm.tool = 'support_resistance'
      toolForm.symbols = normalizeSymbolsInputForUi(picked[0])
      toolForm.start = backtestForm.start || ''
      toolForm.end = backtestForm.end || ''
      const analysisQueued = await store.startQuantTool({
        market: toolForm.market,
        tool: toolForm.tool,
        symbols: toolForm.symbols,
        n_folds: toolForm.n_folds,
        start: toolForm.start || undefined,
        end: toolForm.end || undefined,
        limit: toolForm.limit,
        options: buildToolOptions()
      })
      await waitForJobDone(analysisQueued.id, 20 * 60 * 1000)
      activeTab.value = 'strategy'
      await nextTick()
      await loadKlineChart()
    } catch (err) {
      klineError.value = err?.message || String(err)
    } finally {
      flowRunning.value = false
    }
  }

  const runGridSearch = async () => {
    const buyGrid = buildGridParamPayload(activeBuyStrategy.value, gridBuyParamLists)
    const sellGrid = buildGridParamPayload(activeSellStrategy.value, gridSellParamLists)
    const rankingWeights = {
      profit: Number(gridForm.ranking_weights?.profit ?? 1),
      win_rate: Number(gridForm.ranking_weights?.win_rate ?? 1),
      sharpe: Number(gridForm.ranking_weights?.sharpe ?? 1),
      annual_return: Number(gridForm.ranking_weights?.annual_return ?? 1),
      drawdown: Number(gridForm.ranking_weights?.drawdown ?? 1)
    }
    const customBuyList = parseStringList(gridForm.buy_strategies)
    const customSellList = parseStringList(gridForm.sell_strategies)
    const buyStrategyList = gridExploreAllStrategies.value
      ? buyStrategies.value.map((item) => item.id).filter(Boolean)
      : customBuyList
    const sellStrategyList = gridExploreAllStrategies.value
      ? sellStrategies.value.map((item) => item.id).filter(Boolean)
      : customSellList
    const baseSymbols = gridUseBacktestBase.value ? backtestForm.symbols : gridForm.symbols
    const baseMarketRaw = gridUseBacktestBase.value ? backtestForm.market : gridForm.market
    const baseMarket = inferMarketBySymbols(baseSymbols, baseMarketRaw)
    if (gridUseBacktestBase.value) backtestForm.market = baseMarket
    else gridForm.market = baseMarket
    const baseCash = gridUseBacktestBase.value ? backtestForm.cash : gridForm.cash
    const baseStart = gridUseBacktestBase.value ? backtestForm.start : gridForm.start
    const baseEnd = gridUseBacktestBase.value ? backtestForm.end : gridForm.end
    const baseNFolds = gridUseBacktestBase.value ? backtestForm.n_folds : gridForm.n_folds
    const normalizedMaxRuns = Math.max(1, Number(gridForm.max_runs || 150))
    gridForm.max_runs = normalizedMaxRuns
    strategyError.value = ''
    try {
      await runTrackedJob({
        startJob: () =>
          store.startGridSearch({
            market: baseMarket,
            symbols: baseSymbols,
            n_folds: baseNFolds,
            start: baseStart || undefined,
            end: baseEnd || undefined,
            cash: baseCash,
            commission_rate: backtestForm.commission_rate,
            min_commission: backtestForm.min_commission,
            stamp_tax_rate: backtestForm.stamp_tax_rate,
            slippage_bp: backtestForm.slippage_bp,
            buy_strategy: buyStrategyId.value,
            sell_strategy: sellStrategyId.value,
            buy_strategies: buyStrategyList.length ? buyStrategyList : undefined,
            sell_strategies: sellStrategyList.length ? sellStrategyList : undefined,
            buy_params_grid: buyGrid,
            sell_params_grid: sellGrid,
            validation_mode: gridForm.validation_mode,
            train_ratio: gridForm.train_ratio,
            walk_forward_days: gridForm.walk_forward_days,
            walk_forward_step_days: gridForm.walk_forward_step_days,
            ranking_metric: gridForm.ranking_metric,
            ranking_weights: rankingWeights,
            symbol_top_n: gridForm.symbol_top_n,
            symbol_eval_limit: gridForm.symbol_eval_limit,
            max_runs: normalizedMaxRuns
          }),
        timeoutMs: 90 * 60 * 1000,
        onError: (err) => {
          strategyError.value = err?.message || String(err)
        }
      })
    } catch {
      return null
    }
    return gridJob.value
  }

  const runTool = async () => {
    const effectiveMarket = inferMarketBySymbols(toolForm.symbols, toolForm.market)
    toolForm.market = effectiveMarket
    try {
      await runTrackedJob({
        startJob: () =>
          store.startQuantTool({
            market: effectiveMarket,
            tool: toolForm.tool,
            symbols: toolForm.symbols,
            n_folds: toolForm.n_folds,
            start: toolForm.start || undefined,
            end: toolForm.end || undefined,
            limit: toolForm.limit,
            options: buildToolOptions()
          }),
        timeoutMs: 20 * 60 * 1000
      })
    } catch {
      return null
    }
    return null
  }

  return {
    gridTopRuns,
    toolOptionMode,
    applyGridToBacktest,
    applyGridRunToBacktest,
    applyGridNextSuggestions,
    applySymbolToBacktest,
    applySymbolToAnalysis,
    buildMlStockSelectPayload,
    runVerify,
    runBacktest,
    runStockSelect,
    runClosedLoop,
    runGridSearch,
    runTool
  }
}
