<template>
  <div class="quotes">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>报价管理</span>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            新建报价
          </el-button>
        </div>
      </template>
      
      <el-table :data="quotes" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="报价单号" width="100" />
        <el-table-column prop="customer_name" label="客户" width="120" />
        <el-table-column prop="total_amount" label="总金额" width="120">
          <template #default="{ row }">
            {{ formatAmount(row.total_amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusName(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="valid_until" label="有效期至" width="120">
          <template #default="{ row }">
            {{ formatDate(row.valid_until) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="120">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" @click="viewQuote(row)">详情</el-button>
            <el-button size="small" type="primary" plain @click="getAISuggestion(row)">
              <el-icon><MagicStick /></el-icon>
              AI建议
            </el-button>
            <el-button size="small" type="success" @click="sendQuote(row)" v-if="row.status === 'draft'">发送</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadQuotes"
        @current-change="loadQuotes"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>
    
    <el-dialog v-model="showAddDialog" title="新建报价单" width="700px">
      <el-form :model="quoteForm" label-width="80px">
        <el-form-item label="客户" required>
          <el-select v-model="quoteForm.customer_id" placeholder="请选择客户" style="width: 100%;" @change="onCustomerChange">
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="报价明细">
          <div class="quote-items">
            <div v-for="(item, index) in quoteForm.items" :key="index" class="quote-item">
              <el-input v-model="item.name" placeholder="产品名称" style="width: 150px;" />
              <el-input v-model="item.description" placeholder="描述" style="width: 150px;" />
              <el-input-number v-model="item.quantity" :min="1" placeholder="数量" style="width: 100px;" />
              <el-input-number v-model="item.unit_price" :min="0" placeholder="单价" style="width: 120px;" />
              <span class="item-amount">{{ formatAmount((item.quantity || 0) * (item.unit_price || 0)) }}</span>
              <el-button type="danger" size="small" @click="removeItem(index)" circle>
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button type="primary" size="small" @click="addItem">添加明细</el-button>
          </div>
        </el-form-item>
        <el-form-item label="有效期至">
          <el-date-picker v-model="quoteForm.valid_until" type="date" placeholder="选择日期" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="总金额">
          <span class="total-amount">{{ formatAmount(calculateTotal()) }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="createQuote">确定</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="showDetailDialog" title="报价单详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="报价单号">{{ currentQuote.id }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ currentQuote.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="总金额">
          <span class="total-amount">{{ formatAmount(currentQuote.total_amount) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentQuote.status)">{{ getStatusName(currentQuote.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="有效期至">{{ formatDate(currentQuote.valid_until) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(currentQuote.created_at) }}</el-descriptions-item>
      </el-descriptions>
      
      <h4 style="margin: 20px 0 10px;">报价明细</h4>
      <el-table :data="currentQuote.items" style="width: 100%">
        <el-table-column prop="name" label="产品名称" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="unit_price" label="单价" width="100">
          <template #default="{ row }">{{ formatAmount(row.unit_price) }}</template>
        </el-table-column>
        <el-table-column label="金额" width="100">
          <template #default="{ row }">{{ formatAmount(row.quantity * row.unit_price) }}</template>
        </el-table-column>
      </el-table>
      
      <div v-if="currentQuote.ai_price_suggestion" class="ai-suggestion-section">
        <el-divider>
          <el-icon><MagicStick /></el-icon>
          AI价格建议
        </el-divider>
        <div class="suggestion-content">
          <div v-if="currentQuote.ai_price_suggestion.recommended_discount" class="suggestion-item">
            <strong>建议折扣：</strong>
            <el-tag type="warning">{{ currentQuote.ai_price_suggestion.recommended_discount }}</el-tag>
          </div>
          <div v-if="currentQuote.ai_price_suggestion.strategy" class="suggestion-item">
            <strong>报价策略：</strong>
            <p>{{ currentQuote.ai_price_suggestion.strategy }}</p>
          </div>
          <div v-if="currentQuote.ai_price_suggestion.win_probability" class="suggestion-item">
            <strong>成交概率：</strong>
            <el-progress 
              :percentage="currentQuote.ai_price_suggestion.win_probability * 100" 
              :color="getProbabilityColor(currentQuote.ai_price_suggestion.win_probability)"
            />
          </div>
        </div>
      </div>
    </el-dialog>
    
    <el-dialog v-model="showAIDialog" title="AI报价建议" width="650px">
      <div v-if="aiLoading" class="ai-loading">
        <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        <p>AI正在分析报价策略...</p>
      </div>
      <div v-else-if="aiSuggestion" class="ai-suggestion-result">
        <div class="quote-summary">
          <div class="summary-item">
            <span class="label">客户</span>
            <span class="value">{{ aiQuote?.customer_name }}</span>
          </div>
          <div class="summary-item">
            <span class="label">报价金额</span>
            <span class="value total">{{ formatAmount(aiQuote?.total_amount) }}</span>
          </div>
        </div>
        
        <el-divider />
        
        <div class="suggestion-cards">
          <div class="suggestion-card">
            <el-icon class="card-icon"><Discount /></el-icon>
            <div class="card-content">
              <div class="card-label">建议折扣</div>
              <div class="card-value">{{ aiSuggestion.recommended_discount || '待分析' }}</div>
            </div>
          </div>
          <div class="suggestion-card">
            <el-icon class="card-icon"><TrendCharts /></el-icon>
            <div class="card-content">
              <div class="card-label">成交概率</div>
              <div class="card-value">
                {{ Math.round((aiSuggestion.win_probability || 0) * 100) }}%
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="aiSuggestion.strategy" class="suggestion-section">
          <h4><el-icon><Opportunity /></el-icon> 报价策略</h4>
          <div class="strategy-content">{{ aiSuggestion.strategy }}</div>
        </div>
        
        <div v-if="aiSuggestion.negotiation_tips?.length" class="suggestion-section">
          <h4><el-icon><ChatLineRound /></el-icon> 谈判要点</h4>
          <ul>
            <li v-for="tip in aiSuggestion.negotiation_tips" :key="tip">{{ tip }}</li>
          </ul>
        </div>
        
        <div v-if="aiSuggestion.risk_factors?.length" class="suggestion-section">
          <h4><el-icon><Warning /></el-icon> 风险因素</h4>
          <el-alert 
            v-for="risk in aiSuggestion.risk_factors" 
            :key="risk" 
            :title="risk" 
            type="warning" 
            :closable="false"
            style="margin-bottom: 8px;"
          />
        </div>
      </div>
      <template #footer v-if="!aiLoading">
        <el-button @click="showAIDialog = false">关闭</el-button>
        <el-button type="primary" @click="applySuggestion" v-if="aiSuggestion">
          应用建议
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const quotes = ref([])
const customers = ref([])
const showAddDialog = ref(false)
const showDetailDialog = ref(false)
const showAIDialog = ref(false)
const currentQuote = ref({})
const aiLoading = ref(false)
const aiSuggestion = ref(null)
const aiQuote = ref(null)

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const quoteForm = reactive({
  customer_id: null,
  customer_name: '',
  items: [{ name: '', description: '', quantity: 1, unit_price: 0 }],
  valid_until: null
})

const statusMap = {
  draft: { name: '草稿', type: 'info' },
  sent: { name: '已发送', type: 'warning' },
  accepted: { name: '已接受', type: 'success' },
  rejected: { name: '已拒绝', type: 'danger' }
}

const getStatusName = (status) => statusMap[status]?.name || status
const getStatusType = (status) => statusMap[status]?.type || 'info'

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

const getProbabilityColor = (probability) => {
  if (!probability) return '#909399'
  if (probability >= 0.7) return '#67c23a'
  if (probability >= 0.4) return '#e6a23c'
  return '#f56c6c'
}

const loadQuotes = async () => {
  loading.value = true
  try {
    const result = await api.get('/quotes/', {
      params: {
        page: pagination.page,
        size: pagination.size
      }
    })
    quotes.value = result.items || []
    pagination.total = result.total || 0
  } catch (error) {
    console.error('加载报价单失败', error)
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
  quoteForm.customer_name = customer?.name || ''
}

const addItem = () => {
  quoteForm.items.push({ name: '', description: '', quantity: 1, unit_price: 0 })
}

const removeItem = (index) => {
  quoteForm.items.splice(index, 1)
}

const calculateTotal = () => {
  return quoteForm.items.reduce((sum, item) => sum + (item.quantity || 0) * (item.unit_price || 0), 0)
}

const createQuote = async () => {
  if (!quoteForm.customer_id || quoteForm.items.length === 0) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  try {
    await api.post('/quotes/', quoteForm)
    ElMessage.success('报价单创建成功')
    showAddDialog.value = false
    quoteForm.customer_id = null
    quoteForm.customer_name = ''
    quoteForm.items = [{ name: '', description: '', quantity: 1, unit_price: 0 }]
    loadQuotes()
  } catch (error) {
    console.error('创建报价单失败', error)
  }
}

const viewQuote = async (row) => {
  try {
    const result = await api.get(`/quotes/${row.id}`)
    currentQuote.value = result
    showDetailDialog.value = true
  } catch (error) {
    console.error('获取报价单详情失败', error)
  }
}

const getAISuggestion = async (row) => {
  aiQuote.value = row
  aiSuggestion.value = null
  showAIDialog.value = true
  aiLoading.value = true
  
  try {
    const result = await api.post(`/ai/quote-suggestion/${row.id}`)
    aiSuggestion.value = result.suggestion
    ElMessage.success('AI建议生成完成')
    loadQuotes()
  } catch (error) {
    console.error('获取AI建议失败', error)
    ElMessage.error('AI建议生成失败，请检查API配置')
  } finally {
    aiLoading.value = false
  }
}

const applySuggestion = () => {
  ElMessage.success('建议已记录，请根据建议调整报价')
  showAIDialog.value = false
}

const sendQuote = async (row) => {
  try {
    await api.post(`/quotes/${row.id}/send`)
    ElMessage.success('报价单已发送')
    loadQuotes()
  } catch (error) {
    console.error('发送报价单失败', error)
  }
}

onMounted(() => {
  loadQuotes()
  loadCustomers()
})
</script>

<style lang="scss" scoped>
.quotes {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .quote-items {
    .quote-item {
      display: flex;
      gap: 10px;
      margin-bottom: 10px;
      align-items: center;
      
      .item-amount {
        min-width: 80px;
        text-align: right;
        font-weight: bold;
      }
    }
  }
  
  .total-amount {
    font-size: 20px;
    font-weight: bold;
    color: #f56c6c;
  }
  
  .ai-suggestion-section {
    margin-top: 20px;
    
    .suggestion-content {
      .suggestion-item {
        margin-bottom: 12px;
        
        strong {
          color: #303133;
        }
        
        p {
          margin: 8px 0 0 0;
          color: #606266;
          line-height: 1.6;
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
  
  .ai-suggestion-result {
    .quote-summary {
      display: flex;
      gap: 40px;
      
      .summary-item {
        .label {
          font-size: 12px;
          color: #909399;
        }
        
        .value {
          font-size: 18px;
          font-weight: 600;
          color: #303133;
          
          &.total {
            color: #f56c6c;
          }
        }
      }
    }
    
    .suggestion-cards {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
      margin-bottom: 20px;
      
      .suggestion-card {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 20px;
        background: #f5f7fa;
        border-radius: 12px;
        
        .card-icon {
          font-size: 32px;
          color: #667eea;
        }
        
        .card-content {
          .card-label {
            font-size: 12px;
            color: #909399;
          }
          
          .card-value {
            font-size: 24px;
            font-weight: bold;
            color: #303133;
            margin-top: 4px;
          }
        }
      }
    }
    
    .suggestion-section {
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
      
      .strategy-content {
        padding: 16px;
        background: #f5f7fa;
        border-radius: 8px;
        color: #606266;
        line-height: 1.8;
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
