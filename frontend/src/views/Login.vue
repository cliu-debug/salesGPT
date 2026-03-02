<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>AI销售助手</h1>
        <p>智能销售管理系统</p>
      </div>
      
      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form 
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="用户名"
                size="large"
                prefix-icon="User"
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="密码"
                size="large"
                prefix-icon="Lock"
                show-password
              />
            </el-form-item>
            
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
              style="width: 100%;"
            >
              登录
            </el-button>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="注册" name="register">
          <el-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            @submit.prevent="handleRegister"
          >
            <el-form-item prop="username">
              <el-input
                v-model="registerForm.username"
                placeholder="用户名（3-50字符）"
                size="large"
                prefix-icon="User"
              />
            </el-form-item>
            
            <el-form-item prop="email">
              <el-input
                v-model="registerForm.email"
                placeholder="邮箱地址"
                size="large"
                prefix-icon="Message"
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="密码（至少6字符）"
                size="large"
                prefix-icon="Lock"
                show-password
              />
            </el-form-item>
            
            <el-form-item prop="confirmPassword">
              <el-input
                v-model="registerForm.confirmPassword"
                type="password"
                placeholder="确认密码"
                size="large"
                prefix-icon="Lock"
                show-password
              />
            </el-form-item>
            
            <el-form-item prop="full_name">
              <el-input
                v-model="registerForm.full_name"
                placeholder="姓名（可选）"
                size="large"
                prefix-icon="UserFilled"
              />
            </el-form-item>
            
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleRegister"
              style="width: 100%;"
            >
              注册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      
      <div class="login-footer">
        <p>首次注册将自动创建组织，您将成为组织管理员</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref(null)
const registerFormRef = ref(null)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  full_name: ''
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 100, message: '密码长度在 6 到 100 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    const result = await userStore.login(loginForm.username, loginForm.password)
    loading.value = false
    
    if (result.success) {
      ElMessage.success('登录成功')
      router.push('/')
    } else {
      ElMessage.error(result.message)
    }
  })
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    const result = await userStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
      full_name: registerForm.full_name || undefined
    })
    loading.value = false
    
    if (result.success) {
      ElMessage.success('注册成功')
      router.push('/')
    } else {
      ElMessage.error(result.message)
    }
  })
}
</script>

<style lang="scss" scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  
  .login-card {
    width: 100%;
    max-width: 420px;
    background: #fff;
    border-radius: 16px;
    padding: 40px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
    
    .login-header {
      text-align: center;
      margin-bottom: 30px;
      
      h1 {
        margin: 0;
        font-size: 32px;
        font-weight: 700;
        color: #667eea;
      }
      
      p {
        margin: 10px 0 0;
        font-size: 14px;
        color: #909399;
      }
    }
    
    .login-tabs {
      :deep(.el-tabs__header) {
        margin-bottom: 30px;
      }
      
      :deep(.el-tabs__nav-wrap::after) {
        height: 1px;
      }
      
      :deep(.el-tabs__item) {
        font-size: 16px;
        font-weight: 500;
      }
      
      :deep(.el-tabs__item.is-active) {
        color: #667eea;
      }
      
      :deep(.el-tabs__active-bar) {
        background-color: #667eea;
      }
    }
    
    .el-form {
      .el-form-item {
        margin-bottom: 24px;
        
        &:last-of-type {
          margin-bottom: 0;
        }
      }
      
      .el-button {
        margin-top: 10px;
        height: 44px;
        font-size: 16px;
        font-weight: 500;
      }
    }
    
    .login-footer {
      margin-top: 20px;
      text-align: center;
      
      p {
        margin: 0;
        font-size: 12px;
        color: #909399;
      }
    }
  }
}
</style>
