<template>
  <div class="grid grid-2">
    <div class="info-card">
      <h3>1. 特征构建</h3>
      <div class="form-grid">
        <div>
          <label class="label">市场</label>
          <select v-model="mlFeatureForm.market" class="select">
            <option value="SH">SH</option>
            <option value="SZ">SZ</option>
            <option value="300">300</option>
            <option value="CN">CN</option>
          </select>
        </div>
        <div>
          <label class="label">标的列表</label>
          <input v-model="mlFeatureForm.symbols" placeholder="留空表示当前市场全量训练" />
        </div>
        <div>
          <label class="label">特征版本</label>
          <input v-model="mlFeatureForm.feature_version" />
        </div>
        <div>
          <label class="label">最少 K 线</label>
          <input v-model.number="mlFeatureForm.min_rows" type="number" min="60" />
        </div>
        <div>
          <label class="label">最大标的数</label>
          <input v-model.number="mlFeatureForm.symbol_limit" type="number" min="10" max="50000" />
        </div>
        <div>
          <label class="label">开始日期</label>
          <input v-model="mlFeatureForm.start" type="date" />
        </div>
        <div>
          <label class="label">结束日期</label>
          <input v-model="mlFeatureForm.end" type="date" />
        </div>
      </div>
      <div class="toolbar">
        <button class="btn-secondary" @click="runMlFeatureBuild" :disabled="actionsBusy || mlRunning">构建特征</button>
      </div>
      <div v-if="mlFeatureResult" class="code-wrap">
        <pre class="code">{{ JSON.stringify(mlFeatureResult, null, 2) }}</pre>
      </div>
    </div>

    <div class="info-card">
      <h3>2. 模型训练</h3>
      <div class="form-grid">
        <div>
          <label class="label">市场</label>
          <select v-model="mlTrainForm.market" class="select">
            <option value="SH">SH</option>
            <option value="SZ">SZ</option>
            <option value="300">300</option>
            <option value="CN">CN</option>
          </select>
        </div>
        <div>
          <label class="label">目标</label>
          <input v-model="mlTrainForm.target" />
        </div>
        <div>
          <label class="label">特征版本</label>
          <input v-model="mlTrainForm.feature_version" />
        </div>
        <div>
          <label class="label">训练比例</label>
          <input v-model.number="mlTrainForm.train_ratio" type="number" min="0.6" max="0.95" step="0.01" />
        </div>
        <div>
          <label class="label">最大样本</label>
          <input v-model.number="mlTrainForm.max_samples" type="number" min="1000" max="1000000" />
        </div>
        <div>
          <label class="label">模型名称</label>
          <input v-model="mlTrainForm.model_name" placeholder="market_hgb_300_y_up_5d_v1" />
        </div>
        <div>
          <label class="label">max_iter</label>
          <input v-model.number="mlTrainForm.max_iter" type="number" min="50" />
        </div>
        <div>
          <label class="label">learning_rate</label>
          <input v-model.number="mlTrainForm.learning_rate" type="number" min="0.001" step="0.001" />
        </div>
        <div>
          <label class="label">max_depth</label>
          <input v-model.number="mlTrainForm.max_depth" type="number" min="2" />
        </div>
        <div>
          <label class="label">min_samples_leaf</label>
          <input v-model.number="mlTrainForm.min_samples_leaf" type="number" min="5" />
        </div>
        <div>
          <label class="label">l2_regularization</label>
          <input v-model.number="mlTrainForm.l2_regularization" type="number" min="0" step="0.001" />
        </div>
      </div>
      <div class="toolbar">
        <button class="btn-secondary" @click="runMlTrain" :disabled="actionsBusy || mlRunning">训练模型</button>
      </div>
      <div v-if="mlTrainResult" class="code-wrap">
        <pre class="code">{{ JSON.stringify(mlTrainResult, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  actionsBusy: Boolean,
  mlRunning: Boolean,
  mlFeatureForm: Object,
  mlTrainForm: Object,
  mlFeatureResult: Object,
  mlTrainResult: Object,
  runMlFeatureBuild: Function,
  runMlTrain: Function
})
</script>
