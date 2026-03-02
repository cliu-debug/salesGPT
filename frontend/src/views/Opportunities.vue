<template>
  <div class="opportunities">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>销售机会</span>
            <el-tag v-if="stats.total > 0" type="info" style="margin-left: 10px;">
              共 {{ stats.total }} 个机会 / {{ formatAmount(stats.totalAmount) }}
            </el-tag>
          </div>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            新建机会
          </el-button>
        </div>
      </template>
      
      <el-table :data="opportunities" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="机会名称" min-width="150" />
        <el-table-column prop="customer_name" label="客户" width="120" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">
            {{ formatAmount(row.amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="stage" label="阶段" width="120">
          <template #default="{ row }">
            <el-select v-model="row.stage" size="small" @change="updateStage(row)">
              <el-option v-for="s in stages" :key="s.key" :label="s.name" :value="s.key" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="probability" label="成交概率" width="120">
          <template #default="{ row }">
            <div class="probability-cell">
              <el-progress 
                :percentage="(row.probability || 0) * 100" 
                :stroke-width="10"
                :color="getProbabilityColor(row.probability)"
              />
              <span class="probability-text">{{ Math.round((row.probability || 0) * 100) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="expected_date" label="预计成交" width="120">
          <template #default="{ row }">
            {{ formatDate(row.expected_date) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="viewOpportunity(row)">详情</el-button>
            <el-button size="small" type="primary" plain @click="predictProbability(row)">
              <el-icon><MagicStick /></el-icon>
              AI预测
            </el-button>
            <el-button size="small" type="danger" @click="deleteOpportunity(row)">
              <el-icon><Delete /></el-icon>
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
        @size-change="loadOpportunities"
        @current-change="loadOpportunities"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>
    
    <el-dialog v-model="showAddDialog" title="新建销售机会" width="500px">
      <el-form :model="opportunityForm" label-width="80px">
        <el-form-item label="机会名称" required>
          <el-input v-model="opportunityForm.name" placeholder="请输入机会名称" />
        </el-form-item>
        <el-form-item label="客户" required>
          <el-select v-model="opportunityForm.customer_id" placeholder="请选择客户" style="width: 100%;" @change="onCustomerChange">
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="opportunityForm.amount" :min="0" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="阶段">
          <el-select v-model="opportunityForm.stage" placeholder="请选择阶段" style="width: 100%;">
            <el-option v-for="s in stages" :key="s.key" :label="s.name" :value="s.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计成交">
          <el-date-picker v-model="opportunityForm.expected_date" type="date" placeholder="选择日期" style="width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="createOpportunity">确定</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="showDetailDialog" title="销售机会详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="机会名称">{{ currentOpportunity.name }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ currentOpportunity.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ formatAmount(currentOpportunity.amount) }}</el-descriptions-item>
        <el-descriptions-item label="阶段">
          <el-tag :type="getStageType(currentOpportunity.stage)">{{ getStageName(currentOpportunity.stage) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="成交概率">
          <el-progress 
            :percentage="(currentOpportunity.probability || 0) * 100" 
            :color="getProbabilityColor(currentOpportunity.probability)"
          />
        </el-descriptions-item>
        <el-descriptions-item label="预计成交">{{ formatDate(currentOpportunity.expected_date) }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentOpportunity.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
      
      <div v-if="currentOpportunity.ai_suggestion" class="ai-suggestion-section">
        <el-divider>
          <el-icon><MagicStick /></el-icon>
          AI建议
        </el-divider>
        <div class="suggestion-content">
          <div v-if="currentOpportunity.ai_suggestion.key_factors?.length" class="suggestion-item">
            <strong>关键因素：</strong>
            <el-tag v-for="factor in currentOpportunity.ai_suggestion.key_factors" :key="factor" size="small" style="margin-right: 5px;">{{ factor }}</el-tag>
          </div>
          <div v-if="currentOpportunity.ai_suggestion.risks?.length" class="suggestion-item">
            <strong>风险点：</strong>
            <ul>
              <li v-for="risk in currentOpportunity.ai_suggestion.risks" :key="risk">{{ risk }}</li>
            </ul>
          </div>
          <div v-if="currentOpportunity.ai_suggestion.suggestions?.length" class="suggestion-item">
            <strong>建议：</strong>
            <ul>
              <li v-for="suggestion in currentOpportunity.ai_suggestion.suggestions" :key="suggestion">{{ suggestion }}</li>
            </ul>
          </div>
        </div>
      </div>
    </el-dialog>
    
    <el-dialog v-model="showAIDialog" title="AI成交概率预测" width="600px">
      <div v-if="aiLoading" class="ai-loading">
        <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        <p>AI正在分析成交概率...</p>
      </div>
      <div v-else-if="aiPrediction" class="ai-prediction-result">
        <div class="prediction-header">
          <div class="probability-circle" :style="{ background: getProbabilityGradient(aiPrediction.probability) }">
            <span class="probability-value">{{ Math.round(aiPrediction.probability * 100) }}%</span>
            <span class="probability-label">成交概率</span>
          </div>
          <div class="prediction-info">
            <h3>{{ aiOpportunity?.name }}</h3>
            <p>{{ aiOpportunity?.customer_name }} · {{ formatAmount(aiOpportunity?.amount) }}</p>
            <el-tag :type="getConfidenceType(aiPrediction.confidence)">
              置信度：{{ aiPrediction.confidence || '中' }}
            </el-tag>
          </div>
        </div>
        
        <el-divider />
        
        <div v-if="aiPrediction.key_factors?.length" class="prediction-section">
          <h4><el-icon><Star /></el-icon> 关键因素</h4>
          <div class="factor-tags">
            <el-tag v-for="factor in aiPrediction.key_factors" :key="factor" effect="plain">{{ factor }}</el-tag>
          </div>
        </div>
        
        <div v-if="aiPrediction.risks?.length" class="prediction-section">
          <h4><el-icon><Warning /></el-icon> 风险点</h4>
          <ul class="risk-list">
            <li v-for="risk in aiPrediction.risks" :key="risk">{{ risk }}</li>
          </ul>
        </div>
        
        <div v-if="aiPrediction.suggestions?.length" class="prediction-section">
          <h4><el-icon><Opportunity /></el-icon> 推进建议</h4>
          <ul class="suggestion-list">
            <li v-for="suggestion in aiPrediction.suggestions" :key="suggestion">{{ suggestion }}</li>
          </ul>
        </div>
        
        <div v-if="aiPrediction.next_actions?.length" class="prediction-section">
          <h4><el-icon><List /></el-icon> 下一步行动</h4>
          <el-timeline>
            <el-timeline-item v-for="(action, index) in aiPrediction.next_actions" :key="index" :type="index === 0 ? 'primary' : 'info'">
              {{ action }}
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
      <template #footer v-if="!aiLoading">
        <el-button @click="showAIDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const opportunities = ref([])
const customers = ref([])
const showAddDialog = ref(false)
const showDetailDialog = ref(false)
const showAIDialog = ref(false)
const currentOpportunity = ref({})
const aiLoading = ref(false)
const aiPrediction = ref(null)
const aiOpportunity = ref(null)

const stats = computed(() => {
  const total = opportunities.value.length
  const totalAmount = opportunities.value.reduce((sum, o) => sum + (o.amount || 0), 0)
  return { total, totalAmount }
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const opportunityForm = reactive({
  name: '',
  customer_id: null,
  customer_name: '',
  amount: 0,
  stage: 'initial',
  expected_date: null
})

const stages = [
  { key: 'initial', name: '初步接触', type: 'info' },
  { key: 'need_confirm', name: '需求确认', type: 'primary' },
  { key: 'quoting', name: '报价中', type: 'warning' },
  { key: 'negotiating', name: '谈判中', type: 'danger' },
  { key: 'closed_won', name: '成交', type: 'success' },
  { key: 'closed_lost', name: '失败', type: 'info' }
]

const formatAmount = (amount) => {
  if (!amount) return '¥0'
  if (amount >= 10000) {
    return '¥' + (amount / 10000).toFixed(1) + '万'
  }
  return '¥' + amount.toLocaleString()
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

const getStageName = (stage) => stages.find(s => s.key === stage)?.name || stage
const getStageType = (stage) => stages.find(s => s.key === stage)?.type || 'info'

const getProbabilityColor = (probability) => {
  if (!probability) return '#909399'
  if (probability >= 0.7) return '#67c23a'
  if (probability >= 0.4) return '#e6a23c'
  return '#f56c6c'
}

const getProbabilityGradient = (probability) => {
  if (!probability) return 'conic-gradient(#909399 0deg, #909399 360deg)'
  const deg = probability * 360
  if (probability >= 0.7) return `conic-gradient(#67c23a 0deg, #67c23a ${deg}deg, #e4e7ed ${deg}deg, #e4e7ed 360deg)`
  if (probability >= 0.4) return `conic-gradient(#e6a23c 0deg, #e6a23c ${deg}deg, #e4e7ed ${deg}deg, #e4e7ed 360deg)`
  return `conic-gradient(#f56c6c 0deg, #f56c6c ${deg}deg, #e4e7ed ${deg}deg, #e4e7ed 360deg)`
}

const getConfidenceType = (confidence) => {
  if (confidence === '高') return 'success'
  if (confidence === '中') return 'warning'
  return 'info'
}

const loadOpportunities = async () => {
  loading.value = true
  try {
    const result = await api.get('/opportunities/', {
      params: {
        page: pagination.page,
        size: pagination.size
      }
    })
    opportunities.value = result.items || []
    pagination.total = result.total || 0
  } catch (error) {
    console.error('加载销售机会失败', error)
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

const onCustomerChange = (customerId) => {
  const customer = customers.value.find(c => c.id === customerId)
  opportunityForm.customer_name = customer?.name || ''
}

const createOpportunity = async () => {
  if (!opportunityForm.name || !opportunityForm.customer_id) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  try {
    await api.post('/opportunities/', opportunityForm)
    ElMessage.success('销售机会创建成功')
    showAddDialog.value = false
    opportunityForm.name = ''
    opportunityForm.customer_id = null
    opportunityForm.customer_name = ''
    opportunityForm.amount = 0
    opportunityForm.stage = 'initial'
    loadOpportunities()
  } catch (error) {
    console.error('创建销售机会失败', error)
  }
}

const updateStage = async (row) => {
  try {
    await api.put(`/opportunities/${row.id}`, { stage: row.stage })
    ElMessage.success('阶段更新成功')
  } catch (error) {
    console.error('更新阶段失败', error)
  }
}

const viewOpportunity = async (row) => {
  try {
    const result = await api.get(`/opportunities/${row.id}`)
    currentOpportunity.value = result
    showDetailDialog.value = true
  } catch (error) {
    console.error('获取销售机会详情失败', error)
  }
}

const predictProbability = async (row) => {
  aiOpportunity.value = row
  aiPrediction.value = null
  showAIDialog.value = true
  aiLoading.value = true
  
  try {
    const result = await api.post(`/ai/close-probability/${row.id}`)
    aiPrediction.value = result.prediction
    ElMessage.success('AI预测完成')
    loadOpportunities()
  } catch (error) {
    console.error('AI预测失败', error)
    ElMessage.error('AI预测失败，请检查API配置')
  } finally {
    aiLoading.value = false
  }
}

const deleteOpportunity = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该销售机会吗？', '提示', {
      type: 'warning'
    })
    await api.delete(`/opportunities/${row.id}`)
    ElMessage.success('删除成功')
    loadOpportunities()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败', error)
    }
  }
}

onMounted(() => {
  loadOpportunities()
  loadCustomers()
})
</script>

<style lang="scss" scoped>
.opportunities {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-left {
      display: flex;
      align-items: center;
    }
  }
  
  .probability-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    
    .probability-text {
      font-size: 12px;
      color: #606266;
      margin-top: 4px;
    }
  }
  
  .ai-suggestion-section {
    margin-top: 20px;
    
    .suggestion-content {
      .suggestion-item {
        margin-bottom: 12px;
        
        strong {
          color: #303133;
        }
        
        ul {
          margin: 8px 0 0 0;
          padding-left: 20px;
          
          li {
            color: #606266;
            line-height: 1.8;
          }
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
  
  .ai-prediction-result {
    .prediction-header {
      display: flex;
      align-items: center;
      gap: 24px;
      
      .probability-circle {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #fff;
        
        .probability-value {
          font-size: 28px;
          font-weight: bold;
        }
        
        .probability-label {
          font-size: 12px;
          opacity: 0.9;
        }
      }
      
      .prediction-info {
        h3 {
          margin: 0 0 8px;
          font-size: 18px;
          color: #303133;
        }
        
        p {
          margin: 0 0 12px;
          color: #909399;
        }
      }
    }
    
    .prediction-section {
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
      
      .factor-tags {
        .el-tag {
          margin-right: 8px;
          margin-bottom: 8px;
        }
      }
      
      .risk-list, .suggestion-list {
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
