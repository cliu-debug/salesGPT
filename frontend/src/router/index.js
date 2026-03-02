import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'
import { ElMessage } from 'element-plus'
import Dashboard from '@/views/Dashboard.vue'
import Customers from '@/views/Customers.vue'
import Opportunities from '@/views/Opportunities.vue'
import Quotes from '@/views/Quotes.vue'
import FollowUps from '@/views/FollowUps.vue'
import AgentWorkspace from '@/views/AgentWorkspace.vue'
import Login from '@/views/Login.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: { 
      requiresAuth: true,
      permissions: ['dashboard:read']
    }
  },
  {
    path: '/customers',
    name: 'Customers',
    component: Customers,
    meta: { 
      requiresAuth: true,
      permissions: ['customer:read']
    }
  },
  {
    path: '/opportunities',
    name: 'Opportunities',
    component: Opportunities,
    meta: { 
      requiresAuth: true,
      permissions: ['opportunity:read']
    }
  },
  {
    path: '/quotes',
    name: 'Quotes',
    component: Quotes,
    meta: { 
      requiresAuth: true,
      permissions: ['quote:read']
    }
  },
  {
    path: '/follow-ups',
    name: 'FollowUps',
    component: FollowUps,
    meta: { 
      requiresAuth: true,
      permissions: ['followup:read']
    }
  },
  {
    path: '/agent',
    name: 'AgentWorkspace',
    component: AgentWorkspace,
    meta: { 
      requiresAuth: true,
      permissions: ['agent:read']
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  const permissionStore = usePermissionStore()
  
  const isLoggedIn = userStore.isLoggedIn
  
  // 不需要认证的路由
  if (to.meta.requiresAuth === false) {
    // 已登录访问登录页，跳转到首页
    if (to.path === '/login' && isLoggedIn) {
      next('/')
    } else {
      next()
    }
    return
  }
  
  // 需要认证但未登录
  if (!isLoggedIn) {
    ElMessage.warning('请先登录')
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
    return
  }
  
  // 检查权限
  if (!permissionStore.canAccessRoute(to)) {
    ElMessage.error('您没有权限访问此页面')
    next(false) // 取消导航
    return
  }
  
  next()
})

export default router
