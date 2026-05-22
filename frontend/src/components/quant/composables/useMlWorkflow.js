import { computed, reactive, ref, watch } from 'vue'

export function useMlWorkflow({
  store,
  market,
  waitForJobDone,
  inferMarketBySymbols,
  normalizeSymbolsInputForUi,
  onUsePrediction,
  onAddPrediction,
  buildMlStockSelectPayload
}) {
  const mlRunning = ref(false)
  const modelSelectionByContext = reactive({})

  const mlFeatureForm = reactive({
    market: market.value,
    symbols: '',
    feature_version: 'v1',
    min_rows: 120,
    symbol_limit: 10000,
    start: '',
    end: ''
  })

  const mlTrainForm = reactive({
    market: market.value,
    feature_version: 'v1',
    target: 'y_up_5d',
    train_ratio: 0.8,
    max_samples: 300000,
    model_name: '',
    max_iter: 300,
    learning_rate: 0.05,
    max_depth: 6,
    min_samples_leaf: 30,
    l2_regularization: 0
  })

  const mlPredictForm = reactive({
    market: market.value,
    target: 'y_up_5d',
    model_id: null,
    symbols: '',
    limit: 20
  })

  const mlSelectForm = reactive({
    market: market.value,
    target: 'y_up_5d',
    model_id: null,
    symbols: '',
    min_score: 0.55,
    prediction_limit: 3000,
    candidate_limit: 3000,
    symbol_top_n: 20,
    symbol_eval_limit: 3000,
    min_kline_rows: 120
  })

  const latestJobByType = (type) => {
    if (store.activeJob?.type === type) return store.activeJob
    const jobs = (store.jobs || []).filter((job) => job.type === type)
    if (!jobs.length) return null
    return jobs.reduce((latest, item) => (item.id > latest.id ? item : latest), jobs[0])
  }

  const mlFeatureResult = computed(() => latestJobByType('ml_feature')?.result || null)
  const mlTrainResult = computed(() => latestJobByType('ml_train')?.result || null)
  const mlPredictResult = computed(() => latestJobByType('ml_predict')?.result || null)
  const mlSelectResult = computed(() => latestJobByType('ml_stock_select')?.result || null)

  const syncSymbols = (text) => {
    mlFeatureForm.symbols = text
    mlPredictForm.symbols = text
    mlSelectForm.symbols = text
  }

  watch(market, (val) => {
    mlFeatureForm.market = val
    mlTrainForm.market = val
    mlPredictForm.market = val
    mlSelectForm.market = val
  })

  const refreshMlData = async () => {
    await store.fetchMlModels({
      market: mlTrainForm.market,
      target: mlTrainForm.target,
      limit: 100
    })
    syncRecommendedModelSelection()
    await store.fetchMlPredictions({
      market: mlPredictForm.market,
      target: mlPredictForm.target,
      modelId: mlPredictForm.model_id,
      limit: Math.max(20, Number(mlPredictForm.limit || 20)),
      actions: 'buy,light_buy',
      recommendedOnly: true,
      uniqueSymbols: true
    })
  }

  const setMlMarket = (nextMarket) => {
    if (!nextMarket) return
    mlFeatureForm.market = nextMarket
    mlTrainForm.market = nextMarket
    mlPredictForm.market = nextMarket
    mlSelectForm.market = nextMarket
  }

  const modelContextKey = (marketValue, targetValue) => {
    const marketText = String(marketValue || '').trim().toUpperCase() || 'CN'
    const targetText = String(targetValue || 'y_up_5d').trim() || 'y_up_5d'
    return `${marketText}::${targetText}`
  }

  const findModelById = (modelId) => {
    const id = Number(modelId)
    if (!Number.isFinite(id) || id <= 0) return null
    return (store.mlModels || []).find((item) => Number(item?.id) === id) || null
  }

  const isModelCompatibleWithContext = (model, marketValue, targetValue) => {
    if (!model?.id) return false
    const requestMarket = String(marketValue || '').trim().toUpperCase() || 'CN'
    const requestTarget = String(targetValue || 'y_up_5d').trim() || 'y_up_5d'
    if (requestMarket === 'CN') return false
    return (
      String(model.market || '').trim().toUpperCase() === requestMarket &&
      String(model.target || '').trim() === requestTarget
    )
  }

  const rememberModelSelection = (modelId, marketValue, targetValue) => {
    const model = findModelById(modelId)
    if (!isModelCompatibleWithContext(model, marketValue, targetValue)) return
    modelSelectionByContext[modelContextKey(marketValue, targetValue)] = Number(model.id)
  }

  const restoreModelSelection = (form) => {
    const requestMarket = String(form?.market || '').trim().toUpperCase() || 'CN'
    if (requestMarket === 'CN') {
      form.model_id = null
      return
    }
    const key = modelContextKey(form?.market, form?.target)
    const rememberedId = Number(modelSelectionByContext[key])
    const rememberedModel = findModelById(rememberedId)
    if (isModelCompatibleWithContext(rememberedModel, form?.market, form?.target)) {
      form.model_id = rememberedId
      return
    }
    form.model_id = null
  }

  const sanitizeModelIdForRequest = ({ modelId, marketValue, targetValue, allowCompositeAuto = false }) => {
    const requestMarket = String(marketValue || '').trim().toUpperCase() || 'CN'
    if (allowCompositeAuto && requestMarket === 'CN') return undefined
    const numericId = Number(modelId)
    if (!Number.isFinite(numericId) || numericId <= 0) return undefined
    const model = findModelById(numericId)
    if (!isModelCompatibleWithContext(model, requestMarket, targetValue)) return undefined
    rememberModelSelection(numericId, requestMarket, targetValue)
    return numericId
  }

  watch([() => mlPredictForm.market, () => mlPredictForm.target], () => {
    restoreModelSelection(mlPredictForm)
  })

  watch([() => mlSelectForm.market, () => mlSelectForm.target], () => {
    restoreModelSelection(mlSelectForm)
  })

  const buildMlFeaturePayload = () => {
    const effectiveMarket = inferMarketBySymbols(mlFeatureForm.symbols, mlFeatureForm.market)
    mlFeatureForm.market = effectiveMarket
    return {
      market: effectiveMarket,
      symbols: mlFeatureForm.symbols || undefined,
      feature_version: mlFeatureForm.feature_version || 'v1',
      min_rows: Number(mlFeatureForm.min_rows || 120),
      symbol_limit: Number(mlFeatureForm.symbol_limit || 10000),
      start: mlFeatureForm.start || undefined,
      end: mlFeatureForm.end || undefined
    }
  }

  const buildMlTrainPayload = () => ({
    market: mlTrainForm.market,
    feature_version: mlTrainForm.feature_version || 'v1',
    target: mlTrainForm.target || 'y_up_5d',
    train_ratio: Number(mlTrainForm.train_ratio || 0.8),
    max_samples: Number(mlTrainForm.max_samples || 300000),
    model_name: mlTrainForm.model_name || undefined,
    max_iter: Number(mlTrainForm.max_iter || 300),
    learning_rate: Number(mlTrainForm.learning_rate || 0.05),
    max_depth: Number(mlTrainForm.max_depth || 6),
    min_samples_leaf: Number(mlTrainForm.min_samples_leaf || 30),
    l2_regularization: Number(mlTrainForm.l2_regularization || 0)
  })

  const buildMlPredictPayload = () => {
    const effectiveMarket = inferMarketBySymbols(mlPredictForm.symbols, mlPredictForm.market)
    mlPredictForm.market = effectiveMarket
    const modelId = sanitizeModelIdForRequest({
      modelId: mlPredictForm.model_id,
      marketValue: effectiveMarket,
      targetValue: mlPredictForm.target,
      allowCompositeAuto: true
    })
    if (!modelId) mlPredictForm.model_id = null
    return {
      market: effectiveMarket,
      target: mlPredictForm.target || 'y_up_5d',
      model_id: modelId,
      symbols: mlPredictForm.symbols || undefined,
      limit: Number(mlPredictForm.limit || 20)
    }
  }

  const buildSelectPayload = () => {
    const rawSymbols = String(mlSelectForm.symbols || '').trim()
    const isMarketWide = !rawSymbols
    const marketWideLimitBase = Math.max(
      3000,
      Number(mlSelectForm.prediction_limit || 0),
      Number(mlSelectForm.candidate_limit || 0),
      Number(mlSelectForm.symbol_eval_limit || 0)
    )
    const basePayload =
      typeof buildMlStockSelectPayload === 'function'
        ? buildMlStockSelectPayload(mlSelectForm)
        : {
            market: mlSelectForm.market,
            target: mlSelectForm.target,
            model_id: mlSelectForm.model_id || undefined,
            symbols: rawSymbols || undefined,
            full_market_scan: isMarketWide,
            min_score: Number(mlSelectForm.min_score || 0.55),
            prediction_limit: isMarketWide
              ? Math.max(marketWideLimitBase, Number(mlSelectForm.prediction_limit || 3000))
              : Number(mlSelectForm.prediction_limit || 300),
            candidate_limit: isMarketWide
              ? Math.max(marketWideLimitBase, Number(mlSelectForm.candidate_limit || 3000))
              : Number(mlSelectForm.candidate_limit || 120),
            symbol_top_n: Number(mlSelectForm.symbol_top_n || 20),
            symbol_eval_limit: isMarketWide
              ? Math.max(marketWideLimitBase, Number(mlSelectForm.symbol_eval_limit || 3000))
              : Number(mlSelectForm.symbol_eval_limit || 120),
            min_kline_rows: Number(mlSelectForm.min_kline_rows || 120)
          }
    const effectiveMarket = inferMarketBySymbols(basePayload.symbols, basePayload.market || mlSelectForm.market)
    mlSelectForm.market = effectiveMarket
    const modelId = sanitizeModelIdForRequest({
      modelId: basePayload.model_id,
      marketValue: effectiveMarket,
      targetValue: basePayload.target,
      allowCompositeAuto: true
    })
    if (!modelId) mlSelectForm.model_id = null
    return {
      ...basePayload,
      market: effectiveMarket,
      model_id: modelId
    }
  }

  const runMlFeatureBuild = async () => {
    mlRunning.value = true
    try {
      const job = await store.startMlFeatureBuild(buildMlFeaturePayload())
      await waitForJobDone(job.id, 40 * 60 * 1000)
      await refreshMlData()
    } finally {
      mlRunning.value = false
    }
  }

  const runMlTrain = async () => {
    mlRunning.value = true
    try {
      const job = await store.startMlTrain(buildMlTrainPayload())
      const current = await waitForJobDone(job.id, 60 * 60 * 1000)
      const trainedModelId = Number(current?.result?.model_id)
      if (Number.isFinite(trainedModelId) && trainedModelId > 0) {
        mlPredictForm.model_id = trainedModelId
        mlSelectForm.model_id = trainedModelId
        rememberModelSelection(trainedModelId, mlTrainForm.market, mlTrainForm.target)
      }
      await refreshMlData()
    } finally {
      mlRunning.value = false
    }
  }

  const runMlPredict = async () => {
    mlRunning.value = true
    try {
      const job = await store.startMlPredict(buildMlPredictPayload())
      await waitForJobDone(job.id, 20 * 60 * 1000)
      await refreshMlData()
    } finally {
      mlRunning.value = false
    }
  }

  const runMlStockSelect = async () => {
    mlRunning.value = true
    try {
      const job = await store.startMlStockSelect(buildSelectPayload())
      await waitForJobDone(job.id, 90 * 60 * 1000)
      await refreshMlData()
    } finally {
      mlRunning.value = false
    }
  }

  const runMlPipeline = async () => {
    if (mlRunning.value) return
    mlRunning.value = true
    try {
      if (!String(mlFeatureForm.symbols || '').trim()) {
        mlFeatureForm.symbol_limit = Math.max(5000, Number(mlFeatureForm.symbol_limit || 300))
        mlTrainForm.max_samples = Math.max(1000000, Number(mlTrainForm.max_samples || 300000))
      }
      const featureJob = await store.startMlFeatureBuild(buildMlFeaturePayload())
      await waitForJobDone(featureJob.id, 40 * 60 * 1000)
      const trainJob = await store.startMlTrain(buildMlTrainPayload())
      await waitForJobDone(trainJob.id, 60 * 60 * 1000)
      const predictJob = await store.startMlPredict(buildMlPredictPayload())
      await waitForJobDone(predictJob.id, 20 * 60 * 1000)
      await refreshMlData()
    } finally {
      mlRunning.value = false
    }
  }

  const isUsableMarketModel = (model) => {
    return Boolean(model?.is_qualified_market_model)
  }

  const pickRecommendedModel = () => {
    const rows = Array.isArray(store.mlModels) ? store.mlModels : []
    const exactMarket = String(mlSelectForm.market || mlTrainForm.market || '').trim().toUpperCase()
    const exactTarget = String(mlSelectForm.target || mlTrainForm.target || 'y_up_5d').trim()
    if (exactMarket === 'CN') return null
    const eligible = rows.filter((item) => {
      return (
        String(item?.market || '').trim().toUpperCase() === exactMarket &&
        String(item?.target || '').trim() === exactTarget &&
        isUsableMarketModel(item)
      )
    })
    if (!eligible.length) return null
    const recommended = eligible.find((item) => item?.is_recommended)
    if (recommended) return recommended
    return eligible
      .slice()
      .sort((a, b) => {
        const aucA = Number(a?.metrics?.auc ?? -1)
        const aucB = Number(b?.metrics?.auc ?? -1)
        const countA = Number(a?.symbol_count || 0)
        const countB = Number(b?.symbol_count || 0)
        return (
          (Number(b?.is_active || 0) - Number(a?.is_active || 0)) ||
          (countB - countA) ||
          (aucB - aucA) ||
          (Number(b?.id || 0) - Number(a?.id || 0))
        )
      })[0]
  }

  const syncRecommendedModelSelection = () => {
    const currentPredictId = Number(mlPredictForm.model_id)
    const currentSelectId = Number(mlSelectForm.model_id)
    const currentPredict = (store.mlModels || []).find((item) => Number(item?.id) === currentPredictId)
    const currentSelect = (store.mlModels || []).find((item) => Number(item?.id) === currentSelectId)
    if (!Number.isFinite(currentPredictId) || !isModelCompatibleWithContext(currentPredict, mlPredictForm.market, mlPredictForm.target)) {
      restoreModelSelection(mlPredictForm)
    }
    if (!Number.isFinite(currentSelectId) || !isModelCompatibleWithContext(currentSelect, mlSelectForm.market, mlSelectForm.target)) {
      restoreModelSelection(mlSelectForm)
    }
    const recommended = pickRecommendedModel()
    if (!recommended?.id) return
    if (!mlPredictForm.model_id) {
      mlPredictForm.model_id = Number(recommended.id)
      rememberModelSelection(recommended.id, mlPredictForm.market, mlPredictForm.target)
    }
    if (!mlSelectForm.model_id) {
      mlSelectForm.model_id = Number(recommended.id)
      rememberModelSelection(recommended.id, mlSelectForm.market, mlSelectForm.target)
    }
  }

  const useMlModel = (model) => {
    if (!model?.id || !isUsableMarketModel(model)) return
    const nextMarket = String(model.market || '').trim().toUpperCase()
    const nextTarget = String(model.target || '').trim() || 'y_up_5d'
    if (nextMarket) setMlMarket(nextMarket)
    mlTrainForm.target = nextTarget
    mlPredictForm.target = nextTarget
    mlSelectForm.target = nextTarget
    mlPredictForm.model_id = Number(model.id)
    mlSelectForm.model_id = Number(model.id)
    rememberModelSelection(model.id, nextMarket, nextTarget)
  }

  const runMarketModelPipeline = async (nextMarket = mlTrainForm.market) => {
    setMlMarket(nextMarket)
    mlFeatureForm.symbols = ''
    mlPredictForm.symbols = ''
    mlSelectForm.symbols = ''
    mlPredictForm.model_id = null
    mlSelectForm.model_id = null
    mlFeatureForm.symbol_limit = Math.max(5000, Number(mlFeatureForm.symbol_limit || 300))
    mlTrainForm.max_samples = Math.max(1000000, Number(mlTrainForm.max_samples || 300000))
    mlPredictForm.limit = Math.max(100, Number(mlPredictForm.limit || 20))
    const featureVersion = mlTrainForm.feature_version || 'v1'
    const target = mlTrainForm.target || 'y_up_5d'
    mlTrainForm.model_name = `market_hgb_${nextMarket}_${target}_${featureVersion}`
    await runMlPipeline()
  }

  const promoteMlModel = async (modelId) => {
    if (!modelId) return
    const promoted = await store.promoteMlModel(modelId)
    const nextMarket = String(promoted?.market || mlPredictForm.market || '').trim().toUpperCase()
    const nextTarget = String(promoted?.target || mlPredictForm.target || 'y_up_5d').trim()
    if (nextMarket) setMlMarket(nextMarket)
    mlPredictForm.target = nextTarget
    mlSelectForm.target = nextTarget
    mlPredictForm.model_id = Number(modelId)
    mlSelectForm.model_id = Number(modelId)
    rememberModelSelection(modelId, nextMarket, nextTarget)
    await refreshMlData()
  }

  const loadModelTrainingParams = (model) => {
    if (!model?.id) return
    const params = model.params || {}
    const nextMarket = String(model.market || '').trim().toUpperCase()
    const nextTarget = String(model.target || '').trim() || 'y_up_5d'
    if (nextMarket) setMlMarket(nextMarket)
    mlTrainForm.market = nextMarket || mlTrainForm.market
    mlTrainForm.target = nextTarget
    mlTrainForm.feature_version = model.feature_version || mlTrainForm.feature_version
    mlTrainForm.model_name = model.name || mlTrainForm.model_name
    if (params.train_ratio != null) mlTrainForm.train_ratio = Number(params.train_ratio)
    if (params.max_samples != null) mlTrainForm.max_samples = Number(params.max_samples)
    if (params.max_iter != null) mlTrainForm.max_iter = Number(params.max_iter)
    if (params.learning_rate != null) mlTrainForm.learning_rate = Number(params.learning_rate)
    if (params.max_depth != null) mlTrainForm.max_depth = Number(params.max_depth)
    if (params.min_samples_leaf != null) mlTrainForm.min_samples_leaf = Number(params.min_samples_leaf)
    if (params.l2_regularization != null) mlTrainForm.l2_regularization = Number(params.l2_regularization)
    rememberModelSelection(model.id, nextMarket, nextTarget)
  }

  const numberOrNull = (value) => {
    const num = Number(value)
    return Number.isFinite(num) ? num : null
  }

  const resolvePredictionSignal = (symbol) => {
    const text = String(symbol || '').trim()
    if (!text) return null
    const key = text.toLowerCase()
    const sameSymbol = (row) => String(row?.symbol || '').trim().toLowerCase() === key
    const mlSelect = mlSelectResult.value || {}
    const fromSelect = [
      ...(Array.isArray(mlSelect.buy_candidates) ? mlSelect.buy_candidates : []),
      ...(Array.isArray(mlSelect.top_symbols) ? mlSelect.top_symbols : []),
      ...(Array.isArray(mlSelect.ml_candidates) ? mlSelect.ml_candidates : [])
    ]
    const fromPredictionList = Array.isArray(store.mlPredictions) ? store.mlPredictions : []
    const row = fromSelect.find(sameSymbol) || fromPredictionList.find(sameSymbol)
    if (!row) return null
    const action = String(row.ml_action || row.action || '').trim().toLowerCase() || null
    return {
      symbol: text,
      trade_date: row.trade_date || null,
      action,
      score_up_5d: numberOrNull(row.score_up_5d),
      expected_ret_5d: numberOrNull(row.expected_ret_5d),
      stop_loss: numberOrNull(row.stop_loss),
      take_profit: numberOrNull(row.take_profit),
      entry_price: numberOrNull(row.last_close ?? row.entry_price ?? row.close),
      position_min: numberOrNull(row.position_min),
      position_max: numberOrNull(row.position_max)
    }
  }

  const applyPredictionToBacktest = (symbol) => {
    if (!symbol || typeof onUsePrediction !== 'function') return
    const text = String(symbol).trim()
    if (!text) return
    onUsePrediction(text, resolvePredictionSignal(text))
  }

  const applyPredictionToPool = (symbol) => {
    if (!symbol || typeof onAddPrediction !== 'function') return
    onAddPrediction(String(symbol).trim())
  }

  return {
    mlRunning,
    mlFeatureForm,
    mlTrainForm,
    mlPredictForm,
    mlSelectForm,
    mlFeatureResult,
    mlTrainResult,
    mlPredictResult,
    mlSelectResult,
    refreshMlData,
    setMlMarket,
    runMlFeatureBuild,
    runMlTrain,
    runMlPredict,
    runMlStockSelect,
    runMlPipeline,
    runMarketModelPipeline,
    useMlModel,
    promoteMlModel,
    loadModelTrainingParams,
    applyPredictionToBacktest,
    applyPredictionToPool,
    syncSymbols
  }
}
