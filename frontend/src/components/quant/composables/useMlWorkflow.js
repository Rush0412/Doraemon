import { computed, reactive, ref, watch } from 'vue'

export function useMlWorkflow({
  store,
  market,
  waitForJobDone,
  inferMarketBySymbols,
  normalizeSymbolsInputForUi,
  onUsePrediction
}) {
  const mlRunning = ref(false)

  const mlFeatureForm = reactive({
    market: market.value,
    symbols: '',
    feature_version: 'v1',
    min_rows: 120,
    symbol_limit: 300,
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

  const latestJobByType = (type) => {
    if (store.activeJob?.type === type) return store.activeJob
    const jobs = (store.jobs || []).filter((job) => job.type === type)
    if (!jobs.length) return null
    return jobs.reduce((latest, item) => (item.id > latest.id ? item : latest), jobs[0])
  }

  const mlFeatureResult = computed(() => latestJobByType('ml_feature')?.result || null)
  const mlTrainResult = computed(() => latestJobByType('ml_train')?.result || null)
  const mlPredictResult = computed(() => latestJobByType('ml_predict')?.result || null)

  const syncSymbols = (text) => {
    mlFeatureForm.symbols = text
    mlPredictForm.symbols = text
  }

  watch(market, (val) => {
    mlFeatureForm.market = val
    mlTrainForm.market = val
    mlPredictForm.market = val
  })

  const refreshMlData = async () => {
    await Promise.all([
      store.fetchMlModels({
        market: mlTrainForm.market,
        target: mlTrainForm.target,
        limit: 100
      }),
      store.fetchMlPredictions({
        market: mlPredictForm.market,
        modelId: mlPredictForm.model_id,
        limit: Math.max(20, Number(mlPredictForm.limit || 20))
      })
    ])
  }

  const buildMlFeaturePayload = () => {
    const effectiveMarket = inferMarketBySymbols(mlFeatureForm.symbols, mlFeatureForm.market)
    mlFeatureForm.market = effectiveMarket
    return {
      market: effectiveMarket,
      symbols: mlFeatureForm.symbols || undefined,
      feature_version: mlFeatureForm.feature_version || 'v1',
      min_rows: Number(mlFeatureForm.min_rows || 120),
      symbol_limit: Number(mlFeatureForm.symbol_limit || 300),
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
    const modelId = Number(mlPredictForm.model_id)
    return {
      market: effectiveMarket,
      target: mlPredictForm.target || 'y_up_5d',
      model_id: Number.isFinite(modelId) && modelId > 0 ? modelId : undefined,
      symbols: mlPredictForm.symbols || undefined,
      limit: Number(mlPredictForm.limit || 20)
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
      await waitForJobDone(job.id, 60 * 60 * 1000)
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

  const runMlPipeline = async () => {
    if (mlRunning.value) return
    mlRunning.value = true
    try {
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

  const promoteMlModel = async (modelId) => {
    if (!modelId) return
    await store.promoteMlModel(modelId)
    mlPredictForm.model_id = Number(modelId)
    await refreshMlData()
  }

  const applyPredictionToBacktest = (symbol) => {
    if (!symbol || typeof onUsePrediction !== 'function') return
    onUsePrediction(String(symbol).trim())
  }

  return {
    mlRunning,
    mlFeatureForm,
    mlTrainForm,
    mlPredictForm,
    mlFeatureResult,
    mlTrainResult,
    mlPredictResult,
    refreshMlData,
    runMlFeatureBuild,
    runMlTrain,
    runMlPredict,
    runMlPipeline,
    promoteMlModel,
    applyPredictionToBacktest,
    syncSymbols
  }
}

