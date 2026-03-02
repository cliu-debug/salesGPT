<template>
  <div class="customers">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索客户..."
            clearable
            @keyup.enter="loadCustomers"
            style="width: 300px;"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            添加客户
          </el-button>
        </div>
      </template>
      
      <el-table :data="customers" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="客户名称" min-width="120" />
        <el-table-column prop="contact" label="联系人" width="100" />
        <el-table-column prop="phone" label="电话" width="130" />
        <el-table-column prop="company" label="公司" min-width="150" />
        <el-table-column prop="industry" label="行业" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusName(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="120">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="viewCustomer(row)">详情</el-button>
            <el-button size="small" type="primary" plain @click="analyzeCustomer(row)">
              <el-icon><MagicStick /></el-icon>
              AI画像
            </el-button>
            <el-button size="small" type="danger" @click="deleteCustomer(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadCustomers"
        @current-change="loadCustomers"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>
    
    <el-dialog v-model="showAddDialog" title="添加客户" width="500px">
      <el-form :model="customerForm" label-width="80px">
        <el-form-item label="客户名称" required>
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
        <el-form-item label="行业">
          <el-select v-model="customerForm.industry" placeholder="请选择行业" style="width: 100%;">
            <el-option label="互联网" value="互联网" />
            <el-option label="制造业" value="制造业" />
            <el-option label="金融" value="金融" />
            <el-option label="教育" value="教育" />
            <el-option label="医疗" value="医疗" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="createCustomer">确定</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="showDetailDialog" title="客户详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="客户名称">{{ currentCustomer.name }}</el-descriptions-item>
        <el-descriptions-item label="联系人">{{ currentCustomer.contact }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ currentCustomer.phone }}</el-descriptions-item>
        <el-descriptions-item label="公司">{{ currentCustomer.company }}</el-descriptions-item>
        <el-descriptions-item label="行业">{{ currentCustomer.industry }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentCustomer.status)">{{ getStatusName(currentCustomer.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="来源">{{ currentCustomer.source || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ currentCustomer.email || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentCustomer.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
      
      <div v-if="currentCustomer.ai_profile" class="ai-profile-section">
        <el-divider>
          <el-icon><MagicStick /></el-icon>
          AI客户画像
        </el-divider>
        <div class="profile-content">
          <div class="profile-item" v-if="currentCustomer.ai_profile.customer_type">
            <span class="label">客户类型：</span>
            <span class="value">{{ currentCustomer.ai_profile.customer_type }}</span>
          </div>
          <div class="profile-item" v-if="currentCustomer.ai_profile.budget_level">
            <span class="label">预算等级：</span>
            <span class="value">{{ currentCustomer.ai_profile.budget_level }}</span>
          </div>
          <div class="profile-item" v-if="currentCustomer.ai_profile.decision_speed">
            <span class="label">决策周期：</span>
            <span class="value">{{ currentCustomer.ai_profile.decision_speed }}</span>
          </div>
          <div class="profile-item" v-if="currentCustomer.ai_profile.recommended_strategy">
            <span class="label">推荐策略：</span>
            <span class="value">{{ currentCustomer.ai_profile.recommended_strategy }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
    
    <el-dialog v-model="showAIDialog" title="AI客户画像分析" width="600px">
      <div v-if="aiLoading" class="ai-loading">
        <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        <p>AI正在分析客户画像...</p>
      </div>
      <div v-else-if="aiProfile" class="ai-profile-result">
        <div class="profile-header">
          <el-avatar :size="60" class="avatar">
            {{ aiCustomer?.name?.charAt(0) || '?' }}
          </el-avatar>
          <div class="info">
            <h3>{{ aiCustomer?.name }}</h3>
            <p>{{ aiCustomer?.company || '-' }}</p>
          </div>
        </div>
        
        <el-divider />
        
        <div class="profile-grid">
          <div class="profile-card">
            <el-icon><User /></el-icon>
            <div class="card-content">
              <div class="card-label">客户类型</div>
              <div class="card-value">{{ aiProfile.customer_type || '待分析' }}</div>
            </div>
          </div>
          <div class="profile-card">
            <el-icon><Money /></el-icon>
            <div class="card-content">
              <div class="card-label">预算等级</div>
              <div class="card-value">{{ aiProfile.budget_level || '待分析' }}</div>
            </div>
          </div>
          <div class="profile-card">
            <el-icon><Clock /></el-icon>
            <div class="card-content">
              <div class="card-label">决策周期</div>
              <div class="card-value">{{ aiProfile.decision_speed || '待分析' }}</div>
            </div>
          </div>
          <div class="profile-card">
            <el-icon><Warning /></el-icon>
            <div class="card-content">
              <div class="card-label">风险评估</div>
              <div class="card-value">{{ aiProfile.risk_assessment || '待分析' }}</div>
            </div>
          </div>
        </div>
        
        <div v-if="aiProfile.focus_points?.length" class="profile-section">
          <h4><el-icon><Star /></el-icon> 关注重点</h4>
          <el-tag v-for="point in aiProfile.focus_points" :key="point" class="focus-tag">{{ point }}</el-tag>
        </div>
        
        <div v-if="aiProfile.recommended_strategy" class="profile-section">
          <h4><el-icon><Opportunity /></el-icon> 推荐策略</h4>
          <p>{{ aiProfile.recommended_strategy }}</p>
        </div>
        
        <div v-if="aiProfile.next_steps?.length" class="profile-section">
          <h4><el-icon><List /></el-icon> 下一步建议</h4>
          <ul>
            <li v-for="step in aiProfile.next_steps" :key="step">{{ step }}</li>
          </ul>
        </div>
      </div>
      <template #footer v-if="!aiLoading">
        <el-button @click="showAIDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const customers = ref([])
const searchKeyword = ref('')
const showAddDialog = ref(false)
const showDetailDialog = ref(false)
const showAIDialog = ref(false)
const currentCustomer = ref({})
const aiLoading = ref(false)
const aiProfile = ref(null)
const aiCustomer = ref(null)

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const customerForm = reactive({
  name: '',
  contact: '',
  phone: '',
  company: '',
  industry: ''
})

const statusMap = {
  potential: { name: '潜在客户', type: 'info' },
  interested: { name: '有意向', type: 'primary' },
  negotiating: { name: '谈判中', type: 'warning' },
  closed: { name: '已成交', type: 'success' },
  lost: { name: '已流失', type: 'danger' }
}

const getStatusName = (status) => statusMap[status]?.name || status
const getStatusType = (status) => statusMap[status]?.type || 'info'

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

const loadCustomers = async () => {
  loading.value = true
  try {
    const result = await api.get('/customers/', {
      params: {
        page: pagination.page,
        size: pagination.size,
        keyword: searchKeyword.value
      }
    })
    customers.value = result.items || []
    pagination.total = result.total || 0
  } catch (error) {
    console.error('加载客户失败', error)
  } finally {
    loading.value = false
  }
}

const createCustomer = async () => {
  if (!customerForm.name) {
    ElMessage.warning('请输入客户名称')
    return
  }
  
  try {
    await api.post('/customers/', customerForm)
    ElMessage.success('客户添加成功')
    showAddDialog.value = false
    Object.keys(customerForm).forEach(key => customerForm[key] = '')
    loadCustomers()
  } catch (error) {
    console.error('添加客户失败', error)
  }
}

const viewCustomer = async (row) => {
  try {
    const result = await api.get(`/customers/${row.id}`)
    currentCustomer.value = result
    showDetailDialog.value = true
  } catch (error) {
    console.error('获取客户详情失败', error)
  }
}

const analyzeCustomer = async (row) => {
  aiCustomer.value = row
  aiProfile.value = null
  showAIDialog.value = true
  aiLoading.value = true
  
  try {
    const result = await api.post(`/ai/customer-profile/${row.id}`)
    aiProfile.value = result.profile
    ElMessage.success('AI画像分析完成')
    loadCustomers()
  } catch (error) {
    console.error('AI分析失败', error)
    ElMessage.error('AI分析失败，请检查API配置')
  } finally {
    aiLoading.value = false
  }
}

const deleteCustomer = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该客户吗？', '提示', {
      type: 'warning'
    })
    await api.delete(`/customers/${row.id}`)
    ElMessage.success('客户删除成功')
    loadCustomers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除客户失败', error)
    }
  }
}

onMounted(() => {
  loadCustomers()
})
</script>

<style lang="scss" scoped>
.customers {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .ai-profile-section {
    margin-top: 20px;
    
    .profile-content {
      .profile-item {
        margin-bottom: 12px;
        
        .label {
          font-weight: 600;
          color: #606266;
        }
        
        .value {
          color: #303133;
        }
      }
    }
  }
  
  .ai-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 0;
    color: #909399;
    
    p {
      margin-top: 16px;
      font-size: 14px;
    }
  }
  
  .ai-profile-result {
    .profile-header {
      display: flex;
      align-items: center;
      gap: 16px;
      
      .avatar {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        font-size: 24px;
      }
      
      .info {
        h3 {
          margin: 0;
          font-size: 18px;
          color: #303133;
        }
        
        p {
          margin: 4px 0 0;
          color: #909399;
          font-size: 14px;
        }
      }
    }
    
    .profile-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin-bottom: 20px;
      
      .profile-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
        background: #f5f7fa;
        border-radius: 8px;
        
        .el-icon {
          font-size: 24px;
          color: #667eea;
        }
        
        .card-content {
          .card-label {
            font-size: 12px;
            color: #909399;
          }
          
          .card-value {
            font-size: 16px;
            font-weight: 600;
            color: #303133;
            margin-top: 4px;
          }
        }
      }
    }
    
    .profile-section {
      margin-bottom: 20px;
      
      h4 {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
        color: #303133;
        
        .el-icon {
          color: #667eea;
        }
      }
      
      p {
        color: #606266;
        line-height: 1.6;
        margin: 0;
      }
      
      .focus-tag {
        margin-right: 8px;
        margin-bottom: 8px;
      }
      
      ul {
        margin: 0;
        padding-left: 20px;
        
        li {
          color: #606266;
          line-height: 2;
        }
      }
    }
  }
}
</style>
