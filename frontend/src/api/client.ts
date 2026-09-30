import axios from 'axios'
import i18n from '../i18n'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (!config.params) config.params = {}
  config.params.lang = i18n.language
  return config
})

export default api
