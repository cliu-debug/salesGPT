import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器 - 添加Token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  response => response.data,
  error => {
    const { response } = error
    
    if (response) {
      const { status, data } = response
      
      switch (status) {
        case 400:
          ElMessage.error(data?.detail || '请求参数错误')
          break
        case 401:
          ElMessage.error('未授权，请重新登录')
          // 清除Token并跳转到登录页
          localStorage.removeItem('token')
          localStorage.removeItem('userInfo')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error('权限不足')
          break
        case 404:
          ElMessage.error(data?.detail || '请求的资源不存在')
          break
        case 500:
          ElMessage.error(data?.detail || '服务器内部错误')
          break
        default:
          ElMessage.error(data?.detail || `请求失败 (${status})`)
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    
    return Promise.reject(error)
  }
)

export default api
