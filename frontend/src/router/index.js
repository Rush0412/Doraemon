import { createRouter, createWebHistory } from 'vue-router'
import TaskBoard from '../components/TaskBoard.vue'
import QuantDashboard from '../components/QuantDashboard.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: TaskBoard
  },
  {
    path: '/quant',
    name: 'quant',
    component: QuantDashboard
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
