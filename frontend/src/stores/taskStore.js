import { defineStore } from 'pinia'
import { api } from '../services/api'

export const useTaskStore = defineStore('tasks', {
  state: () => ({
    items: [],
    loading: false,
    error: null
  }),
  actions: {
    async fetchTasks() {
      this.loading = true
      try {
        const { data } = await api.get('/tasks/')
        this.items = data.data
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
    async addTask(payload) {
      this.loading = true
      try {
        const { data } = await api.post('/tasks/', payload)
        this.items.push(data.data)
      } finally {
        this.loading = false
      }
    },
    async toggleTask(id, completed) {
      this.loading = true
      try {
        await api.put(`/tasks/${id}`, { completed })
        const item = this.items.find((task) => task.id === id)
        if (item) item.completed = completed
      } finally {
        this.loading = false
      }
    },
    async removeTask(id) {
      this.loading = true
      try {
        await api.delete(`/tasks/${id}`)
        this.items = this.items.filter((task) => task.id !== id)
      } finally {
        this.loading = false
      }
    }
  }
})
