<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card" @click="$router.push('/customers')">
          <div class="stat-icon customer">
            <el-icon :size="32"><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.total_customers }}</div>
            <div class="stat-label">客户总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" @click="$router.push('/opportunities')">
          <div class="stat-icon opportunity">
            <el-icon :size="32"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.total_opportunities }}</div>
            <div class="stat-label">销售机会</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon amount">
            <el-icon :size="32"><Money /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ formatAmount(stats.total_amount) }}</div>
            <div class="stat-label">总金额</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon rate">
            <el-icon :size="32"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.conversion_rate }}%</div>
            <div class="stat-label">转化率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>销售漏斗</span>
            </div>
          </template>
          <div class="funnel-container">
            <div 
              v-for="(item, index) in funnelData" 
              :key="item.stage" 
              class="funnel-item"
              :style="{ width: getFunnelWidth(index) + '%' }"
            >
              <div class="funnel-bar" :style="{ backgroundColor: getFunnelColor(index) }">
                <span class="funnel-label">{{ item.name }}</span>
                <span class="funnel-count">{{ item.count }}个 / {{ formatAmount(item.amount) }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="ai-insights-card">
          <template #header>
            <div class="card-header">
              <el-icon><MagicStick /></el-icon>
              <span>AI 销售洞察</span>
            </div>
          </template>
          <div v-if="aiLoading" class="ai-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>AI正在分析...</span>
          </div>
          <div v-else-if="aiInsights" class="ai-insights">
            <div class="insight-summary">{{ aiInsights.summary }}</div>
            <div v-if="aiInsights.highlights?.length" class="insight-section">
              <div class="section-title">
                <el-icon><Star /></el-icon> 亮点
              </div>
              <ul>
                <li v-for="(item, i) in aiInsights.highlights" :key="i">{{ item }}</li>
              </ul>
            </div>
            <div v-if="aiInsights.recommendations?.length" class="insight-section">
              <div class="section-title">
                <el-icon><Opportunity /></el-icon> 建议
              </div>
              <ul>
                <li v-for="(item, i) in aiInsights.recommendations" :key="i">{{ item }}</li>
              </ul>
            </div>
          </div>
          <div v-else class="ai-empty">
            <el-button type="primary" @click="loadAIInsights" :loading="aiLoading">
              <el-icon><MagicStick /></el-icon>
              获取AI洞察
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>最近销售机会</span>
          </template>
          <el-table :data="stats.recent_opportunities" style="width: 100%">
            <el-table-column prop="name" label="机会名称" />
            <el-table-column prop="customer_name" label="客户" width="120" />
            <el-table-column prop="amount" label="金额" width="120">
              <template #default="{ row }">
                {{ formatAmount(row.amount) }}
              </template>
            </el-table-column>
            <el-table-column prop="stage" label="阶段" width="100">
              <template #default="{ row }">
                <el-tag :type="getStageType(row.stage)">{{ getStageName(row.stage) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近客户</span>
              <el-button text type="primary" @click="$router.push('/customers')">
                查看全部
              </el-button>
            </div>
          </template>
          <div class="recent-customers">
            <div v-for="customer in stats.recent_customers" :key="customer.id" class="customer-item">
              <div class="customer-avatar">{{ customer.name?.charAt(0) || '?' }}</div>
              <div class="customer-info">
                <div class="customer-name">{{ customer.name }}</div>
                <div class="customer-company">{{ customer.company || '-' }}</div>
              </div>
              <el-tag size="small" :type="getStatusType(customer.status)">{{ getStatusName(customer.status) }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

const stats = ref({
  total_customers: 0,
  total_opportunities: 0,
  total_amount: 0,
  conversion_rate: 0,
  recent_customers: [],
  recent_opportunities: [],
  stage_distribution: {}
})

const aiLoading = ref(false)
const aiInsights = ref(null)

const stageMap = {
  initial: { name: '初步接触', type: 'info' },
  need_confirm: { name: '需求确认', type: 'primary' },
  quoting: { name: '报价中', type: 'warning' },
  negotiating: { name: '谈判中', type: 'danger' },
  closed_won: { name: '成交', type: 'success' },
  closed_lost: { name: '失败', type: 'info' }
}

const statusMap = {
  potential: { name: '潜在客户', type: 'info' },
  interested: { name: '有意向', type: 'primary' },
  negotiating: { name: '谈判中', type: 'warning' },
  closed: { name: '已成交', type: 'success' },
  lost: { name: '已流失', type: 'danger' }
}

const funnelStages = ['initial', 'need_confirm', 'quoting', 'negotiating', 'closed_won']

const funnelData = computed(() => {
  const distribution = stats.value.stage_distribution || {}
  return funnelStages.map(stage => ({
    stage,
    name: stageMap[stage]?.name || stage,
    count: distribution[stage]?.count || 0,
    amount: distribution[stage]?.amount || 0
  }))
})

const funnelColors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#43e97b']

const getFunnelWidth = (index) => {
  const baseWidth = 100 - (index * 15)
  return Math.max(baseWidth, 40)
}

const getFunnelColor = (index) => funnelColors[index] || '#667eea'

const formatAmount = (amount) => {
  if (!amount) return '¥0'
  if (amount >= 10000) {
    return '¥' + (amount / 10000).toFixed(1) + '万'
  }
  return '¥' + amount.toLocaleString()
}

const getStageName = (stage) => stageMap[stage]?.name || stage
const getStageType = (stage) => stageMap[stage]?.type || 'info'
const getStatusName = (status) => statusMap[status]?.name || status
const getStatusType = (status) => statusMap[status]?.type || 'info'

const loadDashboard = async () => {
  try {
    const result = await api.get('/dashboard/')
    stats.value = result
  } catch (error) {
    console.error('加载仪表盘失败', error)
  }
}

const loadAIInsights = async () => {
  aiLoading.value = true
  try {
    const result = await api.get('/dashboard/ai-insights')
    aiInsights.value = result.insights
  } catch (error) {
    console.error('获取AI洞察失败', error)
  } finally {
    aiLoading.value = false
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style lang="scss" scoped>
.dashboard {
  .stat-card {
    display: flex;
    align-items: center;
    padding: 20px;
    cursor: pointer;
    transition: transform 0.2s;
    
    &:hover {
      transform: translateY(-2px);
    }
    
    .stat-icon {
      width: 64px;
      height: 64px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
      color: #fff;
      
      &.customer { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
      &.opportunity { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
      &.amount { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
      &.rate { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    }
    
    .stat-info {
      .stat-value {
        font-size: 28px;
        font-weight: bold;
        color: #303133;
      }
      .stat-label {
        font-size: 14px;
        color: #909399;
        margin-top: 4px;
      }
    }
  }
  
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    
    .el-icon {
      margin-right: 8px;
    }
  }
  
  .funnel-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 10px 0;
    
    .funnel-item {
      transition: all 0.3s;
      
      &:hover {
        transform: scale(1.02);
      }
      
      .funnel-bar {
        height: 50px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 20px;
        color: #fff;
        font-weight: 500;
        
        .funnel-label {
          font-size: 14px;
        }
        
        .funnel-count {
          font-size: 13px;
          opacity: 0.9;
        }
      }
    }
  }
  
  .ai-insights-card {
    height: 100%;
    min-height: 300px;
    
    .card-header {
      color: #667eea;
      font-weight: 600;
    }
    
    .ai-loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 200px;
      color: #909399;
      
      .el-icon {
        font-size: 32px;
        margin-bottom: 10px;
      }
    }
    
    .ai-insights {
      .insight-summary {
        font-size: 15px;
        color: #303133;
        line-height: 1.6;
        padding: 12px;
        background: #f5f7fa;
        border-radius: 8px;
        margin-bottom: 16px;
      }
      
      .insight-section {
        margin-bottom: 12px;
        
        .section-title {
          font-weight: 600;
          color: #303133;
          margin-bottom: 8px;
          display: flex;
          align-items: center;
          
          .el-icon {
            margin-right: 6px;
            color: #667eea;
          }
        }
        
        ul {
          margin: 0;
          padding-left: 20px;
          
          li {
            color: #606266;
            font-size: 13px;
            line-height: 1.8;
          }
        }
      }
    }
    
    .ai-empty {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 200px;
    }
  }
  
  .recent-customers {
    .customer-item {
      display: flex;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #eee;
      
      &:last-child {
        border-bottom: none;
      }
      
      .customer-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 12px;
      }
      
      .customer-info {
        flex: 1;
        
        .customer-name {
          font-weight: 500;
          color: #303133;
        }
        
        .customer-company {
          font-size: 12px;
          color: #909399;
          margin-top: 2px;
        }
      }
    }
  }
}
</style>
