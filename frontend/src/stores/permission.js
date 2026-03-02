import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'
import { useUserStore } from './user'

export const usePermissionStore = defineStore('permission', () => {
  const userStore = useUserStore()
  
  // 权限列表
  const permissions = ref([])
  const roles = ref([])
  const teams = ref([])
  
  // 计算属性
  const hasAnyPermission = computed(() => {
    return permissions.value.length > 0
  })
  
  const isAdmin = computed(() => {
    return userStore.userInfo?.role_name === 'admin' || userStore.userInfo?.is_superuser
  })
  
  const isManager = computed(() => {
    return userStore.userInfo?.role_name === 'manager'
  })
  
  /**
   * 检查是否有指定权限
   * @param {string} permission - 权限标识，如 'customer:read'
   * @returns {boolean}
   */
  function can(permission) {
    if (!userStore.userInfo) return false
    
    // 超级管理员拥有所有权限
    if (userStore.userInfo.is_superuser) return true
    
    // 管理员拥有所有权限
    if (userStore.userInfo.role_name === 'admin') return true
    
    // 检查角色权限
    const rolePermissions = {
      'admin': ['*'],
      'manager': [
        'customer:read', 'customer:write', 'customer:delete',
        'opportunity:read', 'opportunity:write', 'opportunity:delete',
        'quote:read', 'quote:write', 'quote:delete',
        'followup:read', 'followup:write', 'followup:delete',
        'dashboard:read',
        'agent:read', 'agent:write',
        'ai:analyze',
        'monitoring:read'
      ],
      'sales': [
        'customer:read', 'customer:write',
        'opportunity:read', 'opportunity:write',
        'quote:read', 'quote:write',
        'followup:read', 'followup:write',
        'dashboard:read',
        'agent:read',
        'ai:analyze'
      ],
      'viewer': [
        'customer:read',
        'opportunity:read',
        'quote:read',
        'followup:read',
        'dashboard:read'
      ]
    }
    
    const rolePerms = rolePermissions[userStore.userInfo.role_name] || []
    return rolePerms.includes('*') || rolePerms.includes(permission)
  }
  
  /**
   * 检查是否有任意一个权限
   * @param {string[]} permissionList - 权限列表
   * @returns {boolean}
   */
  function canAny(permissionList) {
    return permissionList.some(permission => can(permission))
  }
  
  /**
   * 检查是否有所有权限
   * @param {string[]} permissionList - 权限列表
   * @returns {boolean}
   */
  function canAll(permissionList) {
    return permissionList.every(permission => can(permission))
  }
  
  /**
   * 检查是否可以访问某个路由
   * @param {object} route - 路由对象
   * @returns {boolean}
   */
  function canAccessRoute(route) {
    // 不需要认证的路由
    if (route.meta?.requiresAuth === false) {
      return true
    }
    
    // 需要登录
    if (!userStore.isLoggedIn) {
      return false
    }
    
    // 检查路由权限
    const requiredPermissions = route.meta?.permissions || []
    if (requiredPermissions.length === 0) {
      return true
    }
    
    return canAny(requiredPermissions)
  }
  
  /**
   * 获取角色列表
   */
  async function fetchRoles() {
    try {
      const response = await api.get('/auth/roles')
      roles.value = response.roles || []
      return roles.value
    } catch (error) {
      console.error('获取角色列表失败:', error)
      return []
    }
  }
  
  /**
   * 获取团队列表
   */
  async function fetchTeams() {
    try {
      const response = await api.get('/auth/teams')
      teams.value = response.teams || []
      return teams.value
    } catch (error) {
      console.error('获取团队列表失败:', error)
      return []
    }
  }
  
  /**
   * 创建用户（管理员功能）
   */
  async function createUser(userData) {
    try {
      const response = await api.post('/auth/users', userData)
      return { success: true, user: response }
    } catch (error) {
      console.error('创建用户失败:', error)
      return {
        success: false,
        message: error.response?.data?.detail || '创建用户失败'
      }
    }
  }
  
  /**
   * 更新用户（管理员功能）
   */
  async function updateUser(userId, userData) {
    try {
      const response = await api.put(`/auth/users/${userId}`, userData)
      return { success: true, user: response }
    } catch (error) {
      console.error('更新用户失败:', error)
      return {
        success: false,
        message: error.response?.data?.detail || '更新用户失败'
      }
    }
  }
  
  /**
   * 删除用户（管理员功能）
   */
  async function deleteUser(userId) {
    try {
      await api.delete(`/auth/users/${userId}`)
      return { success: true }
    } catch (error) {
      console.error('删除用户失败:', error)
      return {
        success: false,
        message: error.response?.data?.detail || '删除用户失败'
      }
    }
  }
  
  /**
   * 获取组织用户列表（管理员功能）
   */
  async function fetchUsers(params = {}) {
    try {
      const response = await api.get('/auth/users', { params })
      return response
    } catch (error) {
      console.error('获取用户列表失败:', error)
      return { users: [], total: 0 }
    }
  }
  
  return {
    permissions,
    roles,
    teams,
    hasAnyPermission,
    isAdmin,
    isManager,
    can,
    canAny,
    canAll,
    canAccessRoute,
    fetchRoles,
    fetchTeams,
    createUser,
    updateUser,
    deleteUser,
    fetchUsers
  }
})
