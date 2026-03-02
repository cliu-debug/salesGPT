import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))
  
  const isLoggedIn = computed(() => !!token.value)
  const currentUser = computed(() => userInfo.value)
  const userRole = computed(() => userInfo.value?.role_name || 'viewer')
  const organizationId = computed(() => userInfo.value?.organization_id)
  
  async function login(username, password) {
    try {
      const response = await api.post('/auth/login', { username, password })
      
      token.value = response.access_token
      userInfo.value = response.user
      
      localStorage.setItem('token', response.access_token)
      localStorage.setItem('userInfo', JSON.stringify(response.user))
      
      return { success: true }
    } catch (error) {
      console.error('登录失败:', error)
      return { 
        success: false, 
        message: error.response?.data?.detail || '登录失败，请重试' 
      }
    }
  }
  
  async function register(userData) {
    try {
      const response = await api.post('/auth/register', userData)
      
      token.value = response.access_token
      userInfo.value = response.user
      
      localStorage.setItem('token', response.access_token)
      localStorage.setItem('userInfo', JSON.stringify(response.user))
      
      return { success: true }
    } catch (error) {
      console.error('注册失败:', error)
      return { 
        success: false, 
        message: error.response?.data?.detail || '注册失败，请重试' 
      }
    }
  }
  
  async function logout() {
    try {
      await api.post('/auth/logout')
    } catch (error) {
      console.error('登出失败:', error)
    } finally {
      token.value = ''
      userInfo.value = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    }
  }
  
  async function fetchUserInfo() {
    try {
      const response = await api.get('/auth/me')
      userInfo.value = response
      localStorage.setItem('userInfo', JSON.stringify(response))
      return response
    } catch (error) {
      console.error('获取用户信息失败:', error)
      logout()
      return null
    }
  }
  
  async function updateUserInfo(data) {
    try {
      const response = await api.put('/auth/me', data)
      userInfo.value = response
      localStorage.setItem('userInfo', JSON.stringify(response))
      return { success: true }
    } catch (error) {
      console.error('更新用户信息失败:', error)
      return { 
        success: false, 
        message: error.response?.data?.detail || '更新失败' 
      }
    }
  }
  
  async function changePassword(oldPassword, newPassword) {
    try {
      await api.post('/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword
      })
      return { success: true, message: '密码修改成功' }
    } catch (error) {
      console.error('修改密码失败:', error)
      return { 
        success: false, 
        message: error.response?.data?.detail || '密码修改失败' 
      }
    }
  }
  
  function hasPermission(permission) {
    if (!userInfo.value) return false
    
    // 超级管理员拥有所有权限
    if (userInfo.value.is_superuser) return true
    
    const roleName = userInfo.value.role_name
    if (!roleName) return false
    
    // 简单的权限检查逻辑（可根据需要扩展）
    const rolePermissions = {
      'admin': ['*'],
      'manager': ['customer:read', 'customer:write', 'opportunity:read', 'opportunity:write', 'quote:read', 'quote:write'],
      'sales': ['customer:read', 'customer:write', 'opportunity:read', 'opportunity:write'],
      'viewer': ['customer:read', 'opportunity:read']
    }
    
    const permissions = rolePermissions[roleName] || []
    return permissions.includes('*') || permissions.includes(permission)
  }
  
  return {
    token,
    userInfo,
    isLoggedIn,
    currentUser,
    userRole,
    organizationId,
    login,
    register,
    logout,
    fetchUserInfo,
    updateUserInfo,
    changePassword,
    hasPermission
  }
})
