import { createRouter, createWebHistory } from 'vue-router'
import QuantDashboard from '../components/QuantDashboard.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: QuantDashboard
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
