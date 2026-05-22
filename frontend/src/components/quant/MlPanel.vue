<template>
  <section class="panel" v-show="active">
    <header class="panel-title">
      <div>
        <h2>ML 模型引擎</h2>
        <p class="muted">支持特征构建、训练、预测，以及 ML + 量化联动选股。</p>
      </div>
      <span class="pill">ML</span>
    </header>

    <p class="panel-note">SH、SZ、300 模型分别保留。CN 场景默认自动聚合这三个子市场模型，不再强制要求单一 CN 模型。</p>

    <div class="toolbar">
      <button class="btn-primary" @click="runMlPipeline" :disabled="actionsBusy || mlRunning">一键执行</button>
      <button class="btn-secondary" @click="runMarketModelPipeline('SH')" :disabled="actionsBusy || mlRunning">
        训练 SH 大模型
      </button>
      <button class="btn-secondary" @click="runMarketModelPipeline('SZ')" :disabled="actionsBusy || mlRunning">
        训练 SZ 大模型
      </button>
      <button class="btn-secondary" @click="runMarketModelPipeline('300')" :disabled="actionsBusy || mlRunning">
        训练 300 大模型
      </button>
      <button class="btn-secondary" @click="refreshMlData" :disabled="actionsBusy || mlRunning || mlLoading">
        刷新模型与预测
      </button>
      <span class="muted" v-if="mlRunning">ML 任务执行中...</span>
    </div>

    <p v-if="mlError" class="error">{{ mlError }}</p>
    <MlFeatureTrainSection
      :actions-busy="actionsBusy"
      :ml-running="mlRunning"
      :ml-feature-form="mlFeatureForm"
      :ml-train-form="mlTrainForm"
      :ml-feature-result="mlFeatureResult"
      :ml-train-result="mlTrainResult"
      :run-ml-feature-build="runMlFeatureBuild"
      :run-ml-train="runMlTrain"
    />
    <MlPredictionModelsSection
      :actions-busy="actionsBusy"
      :ml-running="mlRunning"
      :ml-predict-form="mlPredictForm"
      :ml-predict-result="mlPredictResult"
      :ml-models="mlModels"
      :run-ml-predict="runMlPredict"
      :use-ml-model="useMlModel"
      :promote-ml-model="promoteMlModel"
      :load-model-training-params="loadModelTrainingParams"
    />
    <MlStockSelectSection
      :actions-busy="actionsBusy"
      :ml-running="mlRunning"
      :ml-select-form="mlSelectForm"
      :ml-select-result="mlSelectResult"
      :run-ml-stock-select="runMlStockSelect"
      :apply-prediction-to-backtest="applyPredictionToBacktest"
      :apply-prediction-to-pool="applyPredictionToPool"
    />
    <MlPredictionsSection
      :ml-predictions="mlPredictions"
      :apply-prediction-to-backtest="applyPredictionToBacktest"
      :apply-prediction-to-pool="applyPredictionToPool"
    />
  </section>
</template>

<script setup>
import MlFeatureTrainSection from './ml/MlFeatureTrainSection.vue'
import MlPredictionModelsSection from './ml/MlPredictionModelsSection.vue'
import MlPredictionsSection from './ml/MlPredictionsSection.vue'
import MlStockSelectSection from './ml/MlStockSelectSection.vue'

defineProps({
  active: Boolean,
  actionsBusy: Boolean,
  mlRunning: Boolean,
  mlLoading: Boolean,
  mlError: String,
  mlFeatureForm: Object,
  mlTrainForm: Object,
  mlPredictForm: Object,
  mlSelectForm: Object,
  mlFeatureResult: Object,
  mlTrainResult: Object,
  mlPredictResult: Object,
  mlSelectResult: Object,
  mlModels: Array,
  mlPredictions: Array,
  runMlFeatureBuild: Function,
  runMlTrain: Function,
  runMlPredict: Function,
  runMlStockSelect: Function,
  runMlPipeline: Function,
  runMarketModelPipeline: Function,
  refreshMlData: Function,
  useMlModel: Function,
  promoteMlModel: Function,
  loadModelTrainingParams: Function,
  applyPredictionToBacktest: Function,
  applyPredictionToPool: Function
})
</script>
