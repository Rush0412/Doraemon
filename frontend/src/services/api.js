import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.message || error.message
    const normalized = new Error(message)
    normalized.response = error.response
    normalized.cause = error
    return Promise.reject(normalized)
  }
)
