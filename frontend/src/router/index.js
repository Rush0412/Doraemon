import { createRouter, createWebHistory } from 'vue-router'
import TaskBoard from '../components/TaskBoard.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: TaskBoard
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
