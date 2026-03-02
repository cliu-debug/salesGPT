<template>
  <el-config-provider :locale="zhCn">
    <div v-if="!isLoggedIn" class="login-wrapper">
      <router-view />
    </div>
    <div v-else class="app-container">
      <el-container>
        <el-aside width="220px" class="sidebar">
          <div class="logo">
            <el-icon :size="28"><TrendCharts /></el-icon>
            <span>AI销售助手</span>
          </div>
          <el-menu
            :default-active="activeMenu"
            router
            background-color="#1d1e1f"
            text-color="#bfcbd9"
            active-text-color="#409EFF"
          >
            <el-menu-item 
              v-for="item in menuItems" 
              :key="item.index"
              :index="item.index"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.title }}</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        <el-container>
          <el-header class="header">
            <div class="header-left">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
                <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
              </el-breadcrumb>
            </div>
            <div class="header-right">
              <el-dropdown @command="handleUserCommand">
                <span class="user-info">
                  <el-avatar :size="32" class="user-avatar">
                    {{ currentUser?.full_name?.charAt(0) || currentUser?.username?.charAt(0) }}
                  </el-avatar>
                  <span class="username">{{ currentUser?.full_name || currentUser?.username }}</span>
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="profile">
                      <el-icon><User /></el-icon>
                      个人信息
                    </el-dropdown-item>
                    <el-dropdown-item command="password">
                      <el-icon><Lock /></el-icon>
                      修改密码
                    </el-dropdown-item>
                    <el-dropdown-item divided command="logout">
                      <el-icon><SwitchButton /></el-icon>
                      退出登录
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </el-header>
          <el-main class="main-content">
            <router-view />
          </el-main>
        </el-container>
      </el-container>
      
      <el-dialog v-model="showQuickAdd" title="快速添加" width="500px">
        <el-tabs v-model="quickAddType">
          <el-tab-pane label="客户" name="customer">
            <el-form :model="customerForm" label-width="80px">
              <el-form-item label="客户名称">
                <el-input v-model="customerForm.name" placeholder="请输入客户名称" />
              </el-form-item>
              <el-form-item label="联系人">
                <el-input v-model="customerForm.contact" placeholder="请输入联系人" />
              </el-form-item>
              <el-form-item label="电话">
                <el-input v-model="customerForm.phone" placeholder="请输入电话" />
              </el-form-item>
              <el-form-item label="公司">
                <el-input v-model="customerForm.company" placeholder="请输入公司名称" />
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
        <template #footer>
          <el-button @click="showQuickAdd = false">取消</el-button>
          <el-button type="primary" @click="handleQuickAdd">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </el-config-provider>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import api from '@/api'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const permissionStore = usePermissionStore()

const showQuickAdd = ref(false)
const quickAddType = ref('customer')
const customers = ref([])

const customerForm = reactive({
  name: '',
  contact: '',
  phone: '',
  company: '',
  industry: ''
})

const isLoggedIn = computed(() => userStore.isLoggedIn)
const currentUser = computed(() => userStore.currentUser)

const activeMenu = computed(() => route.path)

const currentPageTitle = computed(() => {
  const titles = {
    '/': '仪表盘',
    '/agent': '智能体工作台',
    '/customers': '客户管理',
    '/opportunities': '销售机会',
    '/quotes': '报价管理',
    '/follow-ups': '跟进任务'
  }
  return titles[route.path] || '仪表盘'
})

// 菜单项配置（带权限）
const menuItems = computed(() => {
  const items = [
    {
      index: '/',
      icon: 'HomeFilled',
      title: '仪表盘',
      permission: 'dashboard:read'
    },
    {
      index: '/agent',
      icon: 'Robot',
      title: '智能体工作台',
      permission: 'agent:read'
    },
    {
      index: '/customers',
      icon: 'User',
      title: '客户管理',
      permission: 'customer:read'
    },
    {
      index: '/opportunities',
      icon: 'TrendCharts',
      title: '销售机会',
      permission: 'opportunity:read'
    },
    {
      index: '/quotes',
      icon: 'Document',
      title: '报价管理',
      permission: 'quote:read'
    },
    {
      index: '/follow-ups',
      icon: 'Clock',
      title: '跟进任务',
      permission: 'followup:read'
    }
  ]
  
  // 过滤出有权限访问的菜单项
  return items.filter(item => permissionStore.can(item.permission))
})

const loadCustomers = async () => {
  try {
    const result = await api.get('/customers/', { params: { size: 100 } })
    customers.value = result.items || []
  } catch (error) {
    console.error('加载客户失败', error)
  }
}

const handleQuickAdd = async () => {
  try {
    if (!customerForm.name) {
      ElMessage.warning('请输入客户名称')
      return
    }
    await api.post('/customers/', customerForm)
    ElMessage.success('客户添加成功')
    showQuickAdd.value = false
    customerForm.name = ''
    customerForm.contact = ''
    customerForm.phone = ''
    customerForm.company = ''
    customerForm.industry = ''
    router.push('/customers')
  } catch (error) {
    console.error('添加失败', error)
  }
}

const handleUserCommand = async (command) => {
  switch (command) {
    case 'profile':
      ElMessage.info('个人信息功能开发中')
      break
    case 'password':
      ElMessage.info('修改密码功能开发中')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        await userStore.logout()
        ElMessage.success('已退出登录')
        router.push('/login')
      } catch (error) {
        // 用户取消
      }
      break
  }
}

// 初始化用户信息
const initUser = async () => {
  if (userStore.token && !userStore.userInfo) {
    // 有token但没有用户信息，尝试获取
    try {
      await userStore.fetchUserInfo()
    } catch (error) {
      console.error('初始化用户信息失败:', error)
    }
  }
}

// 监听登录状态变化
watch(isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    loadCustomers()
  }
})

onMounted(() => {
  initUser()
  if (isLoggedIn.value) {
    loadCustomers()
  }
})
</script>

<style lang="scss" scoped>
.login-wrapper {
  height: 100vh;
  width: 100vw;
}

.app-container {
  height: 100vh;
  
  .el-container {
    height: 100%;
  }
  
  .sidebar {
    background-color: #1d1e1f;
    
    .logo {
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      color: #fff;
      font-size: 16px;
      font-weight: bold;
      border-bottom: 1px solid #333;
    }
    
    .el-menu {
      border-right: none;
    }
  }
  
  .header {
    background: #fff;
    border-bottom: 1px solid #e6e6e6;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    
    .header-right {
      .user-info {
        display: flex;
        align-items: center;
        gap: 10px;
        cursor: pointer;
        padding: 5px 10px;
        border-radius: 4px;
        transition: background-color 0.3s;
        
        &:hover {
          background-color: #f5f7fa;
        }
        
        .user-avatar {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: #fff;
          font-weight: 500;
        }
        
        .username {
          font-size: 14px;
          color: #303133;
        }
      }
    }
  }
  
  .main-content {
    background: #f5f7fa;
    padding: 20px;
  }
}
</style>
