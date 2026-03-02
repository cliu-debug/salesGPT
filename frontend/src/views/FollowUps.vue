<template>
  <div class="follow-ups">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>跟进任务</span>
              <el-button type="primary" @click="showAddDialog = true">
                <el-icon><Plus /></el-icon>
                新建跟进
              </el-button>
            </div>
          </template>
          
          <el-table :data="followUps" style="width: 100%" v-loading="loading">
            <el-table-column prop="customer_name" label="客户" width="120" />
            <el-table-column prop="content" label="跟进内容" min-width="200">
              <template #default="{ row }">
                <el-tooltip :content="row.content" placement="top" :show-after="500">
                  <span class="content-text">{{ row.content }}</span>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="next_action" label="下一步行动" width="150">
              <template #default="{ row }">
                <el-tag v-if="row.next_action" type="info">{{ row.next_action }}</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="next_date" label="下次跟进" width="150">
              <template #default="{ row }">
                <div class="next-date-cell" :class="{ 'is-overdue': isOverdue(row.next_date) }">
                  <el-icon v-if="isOverdue(row.next_date)"><Warning /></el-icon>
                  {{ formatDateTime(row.next_date) }}
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="120">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" type="primary" plain @click="generateScript(row)">
                  <el-icon><MagicStick /></el-icon>
                  AI话术
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.size"
            :total="pagination.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="loadFollowUps"
            @current-change="loadFollowUps"
            style="margin-top: 20px; justify-content: flex-end;"
          />
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="today-tasks-card">
          <template #header>
            <div class="card-header">
              <el-icon><Clock /></el-icon>
              <span>今日待办</span>
              <el-badge :value="todayTasks.length" type="primary" />
            </div>
          </template>
          <div v-if="todayTasks.length > 0" class="today-tasks">
            <div v-for="task in todayTasks" :key="task.id" class="task-item">
              <div class="task-header">
                <span class="customer-name">{{ task.customer_name }}</span>
                <el-tag size="small" type="warning">{{ formatTime(task.next_date) }}</el-tag>
              </div>
              <div class="task-action">{{ task.next_action }}</div>
            </div>
          </div>
          <el-empty v-else description="今日暂无待办" :image-size="80" />
        </el-card>
        
        <el-card class="quick-actions-card" style="margin-top: 20px;">
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="showAddDialog = true" style="width: 100%;">
              <el-icon><Plus /></el-icon>
              新建跟进
            </el-button>
            <el-button @click="loadTodayTasks" style="width: 100%; margin-top: 10px;">
              <el-icon><Refresh /></el-icon>
              刷新今日待办
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-dialog v-model="showAddDialog" title="新建跟进记录" width="550px">
      <el-form :model="followUpForm" label-width="80px">
        <el-form-item label="客户" required>
          <el-select v-model="followUpForm.customer_id" placeholder="请选择客户" style="width: 100%;" @change="onCustomerChange">
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="跟进内容" required>
          <el-input v-model="followUpForm.content" type="textarea" :rows="3" placeholder="请输入跟进内容" />
        </el-form-item>
        <el-form-item label="下一步行动">
          <el-input v-model="followUpForm.next_action" placeholder="请输入下一步行动" />
        </el-form-item>
        <el-form-item label="下次跟进">
          <el-date-picker v-model="followUpForm.next_date" type="datetime" placeholder="选择日期时间" style="width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="createFollowUp">确定</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="showAIDialog" title="AI跟进话术生成" width="650px">
      <div v-if="aiLoading" class="ai-loading">
        <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        <p>AI正在生成跟进话术...</p>
      </div>
      <div v-else-if="aiScript" class="ai-script-result">
        <div class="script-header">
          <div class="customer-info">
            <el-avatar :size="50" class="avatar">
              {{ aiFollowUp?.customer_name?.charAt(0) || '?' }}
            </el-avatar>
            <div class="info">
              <h3>{{ aiFollowUp?.customer_name }}</h3>
              <p>跟进目的：{{ aiPurpose }}</p>
            </div>
          </div>
          <el-select v-model="aiPurpose" placeholder="选择跟进目的" style="width: 150px;" @change="regenerateScript">
            <el-option label="日常跟进" value="日常跟进" />
            <el-option label="报价跟进" value="报价跟进" />
            <el-option label="合同跟进" value="合同跟进" />
            <el-option label="回款跟进" value="回款跟进" />
            <el-option label="售后跟进" value="售后跟进" />
          </el-select>
        </div>
        
        <el-divider />
        
        <div class="script-content">
          <div class="script-label">
            <el-icon><ChatLineSquare /></el-icon>
            生成的跟进话术
          </div>
          <div class="script-text">{{ aiScript }}</div>
        </div>
        
        <div class="script-actions">
          <el-button @click="copyScript">
            <el-icon><CopyDocument /></el-icon>
            复制话术
          </el-button>
          <el-button type="primary" @click="regenerateScript">
            <el-icon><Refresh /></el-icon>
            重新生成
          </el-button>
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
import { ElMessage } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const followUps = ref([])
const customers = ref([])
const todayTasks = ref([])
const showAddDialog = ref(false)
const showAIDialog = ref(false)
const aiLoading = ref(false)
const aiScript = ref('')
const aiFollowUp = ref(null)
const aiPurpose = ref('日常跟进')

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const followUpForm = reactive({
  customer_id: null,
  customer_name: '',
  content: '',
  next_action: '',
  next_date: null
})

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

const formatTime = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const formatDateTime = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN', { 
    month: '2-digit', 
    day: '2-digit',
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

const isOverdue = (date) => {
  if (!date) return false
  return new Date(date) < new Date()
}

const loadFollowUps = async () => {
  loading.value = true
  try {
    const result = await api.get('/follow-ups/', {
      params: {
        page: pagination.page,
        size: pagination.size
      }
    })
    followUps.value = result.items || []
    pagination.total = result.total || 0
  } catch (error) {
    console.error('加载跟进记录失败', error)
  } finally {
    loading.value = false
  }
}

const loadCustomers = async () => {
  try {
    const result = await api.get('/customers/', { params: { size: 100 } })
    customers.value = result.items || []
  } catch (error) {
    console.error('加载客户失败', error)
  }
}

const loadTodayTasks = async () => {
  try {
    const result = await api.get('/follow-ups/today')
    todayTasks.value = result.items || []
  } catch (error) {
    console.error('加载今日待办失败', error)
  }
}

const onCustomerChange = (customerId) => {
  const customer = customers.value.find(c => c.id === customerId)
  followUpForm.customer_name = customer?.name || ''
}

const createFollowUp = async () => {
  if (!followUpForm.customer_id || !followUpForm.content) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  try {
    await api.post('/follow-ups/', followUpForm)
    ElMessage.success('跟进记录创建成功')
    showAddDialog.value = false
    followUpForm.customer_id = null
    followUpForm.customer_name = ''
    followUpForm.content = ''
    followUpForm.next_action = ''
    followUpForm.next_date = null
    loadFollowUps()
    loadTodayTasks()
  } catch (error) {
    console.error('创建跟进记录失败', error)
  }
}

const generateScript = async (row) => {
  aiFollowUp.value = row
  aiScript.value = ''
  showAIDialog.value = true
  aiLoading.value = true
  
  try {
    const result = await api.post(`/ai/follow-up-script/${row.customer_id}`, null, {
      params: { purpose: aiPurpose.value }
    })
    aiScript.value = result.script
    ElMessage.success('AI话术生成完成')
  } catch (error) {
    console.error('AI话术生成失败', error)
    ElMessage.error('AI话术生成失败，请检查API配置')
  } finally {
    aiLoading.value = false
  }
}

const regenerateScript = async () => {
  if (!aiFollowUp.value) return
  
  aiLoading.value = true
  aiScript.value = ''
  
  try {
    const result = await api.post(`/ai/follow-up-script/${aiFollowUp.value.customer_id}`, null, {
      params: { purpose: aiPurpose.value }
    })
    aiScript.value = result.script
    ElMessage.success('AI话术重新生成完成')
  } catch (error) {
    console.error('AI话术生成失败', error)
    ElMessage.error('AI话术生成失败')
  } finally {
    aiLoading.value = false
  }
}

const copyScript = async () => {
  try {
    await navigator.clipboard.writeText(aiScript.value)
    ElMessage.success('话术已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

onMounted(() => {
  loadFollowUps()
  loadCustomers()
  loadTodayTasks()
})
</script>

<style lang="scss" scoped>
.follow-ups {
  .card-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  .content-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    display: block;
    max-width: 200px;
  }
  
  .next-date-cell {
    display: flex;
    align-items: center;
    gap: 4px;
    
    &.is-overdue {
      color: #f56c6c;
      
      .el-icon {
        color: #f56c6c;
      }
    }
  }
  
  .today-tasks-card {
    .today-tasks {
      .task-item {
        padding: 12px;
        border-bottom: 1px solid #ebeef5;
        
        &:last-child {
          border-bottom: none;
        }
        
        .task-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
          
          .customer-name {
            font-weight: 600;
            color: #303133;
          }
        }
        
        .task-action {
          font-size: 13px;
          color: #606266;
        }
      }
    }
  }
  
  .quick-actions-card {
    .quick-actions {
      display: flex;
      flex-direction: column;
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
  
  .ai-script-result {
    .script-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .customer-info {
        display: flex;
        align-items: center;
        gap: 12px;
        
        .avatar {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: #fff;
          font-size: 20px;
        }
        
        .info {
          h3 {
            margin: 0;
            font-size: 16px;
            color: #303133;
          }
          
          p {
            margin: 4px 0 0;
            font-size: 13px;
            color: #909399;
          }
        }
      }
    }
    
    .script-content {
      .script-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        color: #303133;
        margin-bottom: 12px;
        
        .el-icon {
          color: #667eea;
        }
      }
      
      .script-text {
        padding: 20px;
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
        border-radius: 12px;
        color: #303133;
        line-height: 1.8;
        font-size: 15px;
        white-space: pre-wrap;
      }
    }
    
    .script-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 20px;
    }
  }
}
</style>
