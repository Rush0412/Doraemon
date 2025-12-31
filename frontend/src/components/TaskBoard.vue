<template>
  <div class="grid">
    <section class="panel">
      <header class="panel-title">
        <div>
          <h2>任务录入</h2>
          <p class="muted">快速记录与跟踪待办事项。</p>
        </div>
        <span class="pill">Tasks</span>
      </header>
      <div class="form-grid">
        <div>
          <label class="label">标题</label>
          <input v-model="form.title" placeholder="What needs to be done?" />
        </div>
        <div>
          <label class="label">描述</label>
          <textarea v-model="form.description" rows="3" placeholder="Optional details" />
        </div>
      </div>
      <div class="toolbar">
        <button class="btn-primary" @click="createTask" :disabled="isSubmitDisabled">
          + Add Task
        </button>
        <button class="btn-secondary" @click="resetForm">Reset</button>
      </div>
    </section>

    <section class="panel">
      <header class="panel-title">
        <div>
          <h2>任务列表</h2>
          <p class="muted">状态更新与快速清理。</p>
        </div>
      </header>
      <div v-if="store.loading" class="muted">Loading…</div>
      <div v-else>
        <div v-for="task in store.items" :key="task.id" class="task-item">
          <div class="task-meta">
            <input type="checkbox" :checked="task.completed" @change="toggle(task)" />
            <div>
              <div style="display: flex; gap: 10px; align-items: center;">
                <strong>{{ task.title }}</strong>
                <span class="status-badge" :class="task.completed ? 'status-done' : 'status-open'">
                  {{ task.completed ? 'Done' : 'Open' }}
                </span>
              </div>
              <p style="margin: 4px 0 0;" class="muted" v-if="task.description">{{ task.description }}</p>
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn-secondary" @click="remove(task.id)">Delete</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, computed } from 'vue'
import { useTaskStore } from '../stores/taskStore'

const store = useTaskStore()

const form = reactive({
  title: '',
  description: ''
})

const isSubmitDisabled = computed(() => !form.title.trim())

const resetForm = () => {
  form.title = ''
  form.description = ''
}

const createTask = async () => {
  if (isSubmitDisabled.value) return
  await store.addTask({ ...form, completed: false })
  resetForm()
}

const toggle = async (task) => {
  await store.toggleTask(task.id, !task.completed)
}

const remove = async (id) => {
  await store.removeTask(id)
}

onMounted(() => {
  store.fetchTasks()
})
</script>
