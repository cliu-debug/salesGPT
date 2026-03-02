<template>
  <div class="agent-workspace">
    <div class="workspace-header">
      <div class="header-left">
        <h2>
          <el-icon class="robot-icon"><Robot /></el-icon>
          AI销售智能体工作台
        </h2>
        <p class="subtitle">让AI主动帮你发现机会、预警风险、推进销售</p>
      </div>
      <div class="header-right">
        <el-switch
          v-model="autoMode"
          active-text="自主模式"
          inactive-text="手动模式"
          style="margin-right: 16px;"
        />
        <el-button type="primary" @click="triggerScan" :loading="scanning">
          <el-icon><Refresh /></el-icon>
          执行扫描
        </el-button>
      </div>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="chat-card">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon><ChatDotRound /></el-icon>
                <span>智能对话</span>
              </div>
              <el-button text size="small" @click="clearChat">
                清空对话
              </el-button>
            </div>
          </template>
          
          <div class="chat-container" ref="chatContainer">
            <div class="chat-messages">
              <div 
                v-for="(msg, index) in chatMessages" 
                :key="index"
                :class="['message', msg.role]"
              >
                <div class="message-avatar">
                  <el-avatar v-if="msg.role === 'user'" :size="32">
                    <el-icon><User /></el-icon>
                  </el-avatar>
                  <el-avatar v-else :size="32" class="bot-avatar">
                    <el-icon><Robot /></el-icon>
                  </el-avatar>
                </div>
                <div class="message-content">
                  <div class="message-text">{{ msg.content }}</div>
                  <div v-if="msg.suggestions?.length" class="message-suggestions">
                    <el-tag 
                      v-for="s in msg.suggestions" 
                      :key="s" 
                      size="small"
                      class="suggestion-tag"
                    >
                      {{ s }}
                    </el-tag>
                  </div>
                </div>
              </div>
              
              <div v-if="chatLoading" class="message bot">
                <div class="message-avatar">
                  <el-avatar :size="32" class="bot-avatar">
                    <el-icon class="is-loading"><Loading /></el-icon>
                  </el-avatar>
                </div>
                <div class="message-content">
                  <div class="message-text typing">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="chat-input">
            <el-input
              v-model="chatInput"
              placeholder="输入您的问题或指令，如：分析今日销售数据、提醒我跟进客户..."
              @keyup.enter="sendMessage"
              clearable
            >
              <template #append>
                <el-button type="primary" @click="sendMessage" :loading="chatLoading">
                  发送
                </el-button>
              </template>
            </el-input>
          </div>
          
          <div class="quick-actions">
            <el-button size="small" @click="quickAction('今日待办')">今日待办</el-button>
            <el-button size="small" @click="quickAction('销售分析')">销售分析</el-button>
            <el-button size="small" @click="quickAction('预警扫描')">预警扫描</el-button>
            <el-button size="small" @click="quickAction('目标进度')">目标进度</el-button>
          </div>
        </el-card>
        
        <el-card class="alerts-card" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon><Bell /></el-icon>
                <span>智能预警</span>
                <el-badge :value="alertSummary.total" type="danger" v-if="alertSummary.total > 0" />
              </div>
              <el-radio-group v-model="alertFilter" size="small">
                <el-radio-button label="all">全部</el-radio-button>
                <el-radio-button label="high">高优先</el-radio-button>
                <el-radio-button label="medium">中优先</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          
          <div v-if="alerts.length === 0" class="empty-alerts">
            <el-icon :size="48"><CircleCheck /></el-icon>
            <p>暂无预警，系统运行良好</p>
          </div>
          
          <div v-else class="alerts-list">
            <div 
              v-for="alert in filteredAlerts" 
              :key="alert.id" 
              class="alert-item"
              :class="['severity-' + alert.severity]"
            >
              <div class="alert-icon">
                <el-icon v-if="alert.alert_type === 'customer_churn_risk'" :size="24"><User /></el-icon>
                <el-icon v-else-if="alert.alert_type === 'opportunity_stalled'" :size="24"><TrendCharts /></el-icon>
                <el-icon v-else-if="alert.alert_type === 'followup_overdue'" :size="24"><Clock /></el-icon>
                <el-icon v-else-if="alert.alert_type === 'quote_expiring'" :size="24"><Document /></el-icon>
                <el-icon v-else :size="24"><Warning /></el-icon>
              </div>
              <div class="alert-content">
                <div class="alert-title">{{ alert.title }}</div>
                <div class="alert-desc">{{ alert.description }}</div>
                <div class="alert-action" v-if="alert.suggested_action">
                  <el-icon><Opportunity /></el-icon>
                  {{ alert.suggested_action }}
                </div>
              </div>
              <div class="alert-actions">
                <el-button size="small" type="primary" @click="handleAlert(alert)">
                  处理
                </el-button>
                <el-button size="small" @click="resolveAlert(alert.id)">
                  忽略
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="status-card">
          <template #header>
            <div class="card-header">
              <el-icon><Monitor /></el-icon>
              <span>Agent状态</span>
            </div>
          </template>
          <div class="agent-status">
            <div v-for="agent in agentStatus.agents" :key="agent.name" class="status-item">
              <div class="status-dot" :class="agent.status"></div>
              <span class="status-name">{{ agent.name }}</span>
              <el-tag size="small" :type="agent.status === 'active' ? 'success' : 'info'">
                {{ agent.status }}
              </el-tag>
            </div>
          </div>
        </el-card>
        
        <el-card class="recommendations-card" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <el-icon><MagicStick /></el-icon>
              <span>智能推荐</span>
            </div>
          </template>
          <div v-if="recommendations.length === 0" class="empty-recs">
            <p>暂无推荐</p>
          </div>
          <div v-else class="recommendations-list">
            <div 
              v-for="(rec, index) in recommendations" 
              :key="index" 
              class="rec-item"
              @click="executeRecommendation(rec)"
            >
              <div class="rec-priority" :class="rec.priority"></div>
              <div class="rec-content">
                <div class="rec-action">{{ rec.action }}</div>
                <div class="rec-reason">{{ rec.reason }}</div>
              </div>
              <el-icon class="rec-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </el-card>
        
        <el-card class="goals-card" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon><Flag /></el-icon>
                <span>销售目标</span>
              </div>
              <el-button type="primary" size="small" @click="showGoalDialog = true">
                <el-icon><Plus /></el-icon>
                设置
              </el-button>
            </div>
          </template>
          
          <div v-if="goals.length === 0" class="empty-goals">
            <p>暂无销售目标</p>
          </div>
          
          <div v-else class="goals-list">
            <div v-for="goal in goals" :key="goal.id" class="goal-item">
              <div class="goal-info">
                <div class="goal-name">{{ goal.name }}</div>
                <el-progress 
                  :percentage="goal.progress" 
                  :stroke-width="8"
                  :color="getProgressColor(goal.progress)"
                />
              </div>
              <div class="goal-value">
                {{ formatAmount(goal.current_value) }} / {{ formatAmount(goal.target_value) }}
              </div>
            </div>
          </div>
        </el-card>
        
        <el-card class="briefing-card" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <el-icon><Sunny /></el-icon>
              <span>今日简报</span>
            </div>
          </template>
          <div class="briefing-stats" v-if="briefing">
            <div class="stat-item">
              <div class="stat-value">{{ briefing.summary?.high_priority || 0 }}</div>
              <div class="stat-label">高优先预警</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ briefing.summary?.today_followups || 0 }}</div>
              <div class="stat-label">今日跟进</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ briefing.summary?.active_opportunities || 0 }}</div>
              <div class="stat-label">活跃机会</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-dialog v-model="showGoalDialog" title="设置销售目标" width="500px">
      <el-form :model="goalForm" label-width="80px">
        <el-form-item label="目标名称" required>
          <el-input v-model="goalForm.name" placeholder="例如: 本月销售额" />
        </el-form-item>
        <el-form-item label="目标金额" required>
          <el-input-number v-model="goalForm.target_value" :min="0" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="goalForm.end_date" type="date" placeholder="选择日期" style="width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGoalDialog = false">取消</el-button>
        <el-button type="primary" @click="createGoal">确定</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="showAlertDialog" title="处理预警" width="600px">
      <div v-if="currentAlert" class="alert-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="预警类型">{{ getAlertTypeName(currentAlert.alert_type) }}</el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityType(currentAlert.severity)">{{ currentAlert.severity }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述">{{ currentAlert.description }}</el-descriptions-item>
          <el-descriptions-item label="建议行动">{{ currentAlert.suggested_action }}</el-descriptions-item>
        </el-descriptions>
        
        <div class="action-buttons">
          <el-button type="primary" @click="goToEntity(currentAlert)">
            前往处理
          </el-button>
          <el-button @click="resolveAlertWithNote(currentAlert.id)">
            标记已处理
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const router = useRouter()

const scanning = ref(false)
const autoMode = ref(false)
const alerts = ref([])
const goals = ref([])
const briefing = ref(null)
const alertSummary = ref({ total: 0, high_priority: 0 })
const alertFilter = ref('all')
const agentStatus = ref({ agents: [] })
const recommendations = ref([])

const showGoalDialog = ref(false)
const showAlertDialog = ref(false)
const currentAlert = ref(null)

const chatMessages = ref([
  {
    role: 'bot',
    content: '您好！我是AI销售智能体，我可以帮您：\n• 分析销售数据和趋势\n• 监控客户状态和预警\n• 生成跟进建议\n• 查看今日待办事项\n\n请问有什么可以帮您的？',
    suggestions: ['今日待办', '销售分析', '预警扫描']
  }
])
const chatInput = ref('')
const chatLoading = ref(false)
const chatContainer = ref(null)

const goalForm = ref({
  name: '',
  target_value: 100000,
  end_date: null
})

const filteredAlerts = computed(() => {
  if (alertFilter.value === 'all') return alerts.value
  return alerts.value.filter(a => a.severity === alertFilter.value)
})

const formatAmount = (amount) => {
  if (!amount) return '¥0'
  if (amount >= 10000) {
    return '¥' + (amount / 10000).toFixed(1) + '万'
  }
  return '¥' + amount.toLocaleString()
}

const getProgressColor = (progress) => {
  if (progress >= 80) return '#67c23a'
  if (progress >= 50) return '#e6a23c'
  return '#409eff'
}

const getAlertTypeName = (type) => {
  const names = {
    'customer_churn_risk': '客户流失风险',
    'opportunity_stalled': '机会停滞',
    'followup_overdue': '跟进逾期',
    'quote_expiring': '报价即将过期',
    'high_value_opportunity': '高价值机会'
  }
  return names[type] || type
}

const getSeverityType = (severity) => {
  if (severity === 'high') return 'danger'
  if (severity === 'medium') return 'warning'
  return 'info'
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const sendMessage = async () => {
  if (!chatInput.value.trim()) return
  
  const userMessage = chatInput.value.trim()
  chatMessages.value.push({ role: 'user', content: userMessage })
  chatInput.value = ''
  chatLoading.value = true
  
  await scrollToBottom()
  
  try {
    const result = await api.post('/agent/chat', null, {
      params: { message: userMessage }
    })
    
    let botContent = ''
    if (result.suggestions?.length) {
      botContent = result.suggestions.join('\n')
    } else if (result.results?.length) {
      botContent = '已为您处理请求，请查看右侧面板获取详细信息。'
    } else {
      botContent = '我已收到您的请求，请问还有什么可以帮您的？'
    }
    
    chatMessages.value.push({
      role: 'bot',
      content: botContent,
      suggestions: result.suggestions?.slice(0, 3) || []
    })
  } catch (error) {
    console.error('对话失败', error)
    chatMessages.value.push({
      role: 'bot',
      content: '抱歉，处理您的请求时出现错误，请稍后重试。'
    })
  } finally {
    chatLoading.value = false
    await scrollToBottom()
  }
}

const quickAction = (action) => {
  chatInput.value = action
  sendMessage()
}

const clearChat = () => {
  chatMessages.value = [
    {
      role: 'bot',
      content: '对话已清空。请问有什么可以帮您的？',
      suggestions: ['今日待办', '销售分析', '预警扫描']
    }
  ]
}

const loadDashboard = async () => {
  try {
    const result = await api.get('/agent/dashboard')
    alerts.value = result.recent_alerts || []
    goals.value = result.active_goals || []
    briefing.value = result.briefing
    alertSummary.value = result.alert_summary || { total: 0 }
  } catch (error) {
    console.error('加载智能体工作台失败', error)
  }
}

const loadAgentStatus = async () => {
  try {
    const result = await api.get('/agent/status')
    agentStatus.value = result
  } catch (error) {
    console.error('加载Agent状态失败', error)
  }
}

const loadRecommendations = async () => {
  try {
    const result = await api.get('/agent/recommendations')
    recommendations.value = result.recommendations || []
  } catch (error) {
    console.error('加载推荐失败', error)
  }
}

const triggerScan = async () => {
  scanning.value = true
  try {
    const result = await api.post('/agent/scan')
    ElMessage.success(`扫描完成，发现 ${result.new_alerts} 条新预警`)
    loadDashboard()
    loadRecommendations()
  } catch (error) {
    console.error('扫描失败', error)
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

const handleAlert = (alert) => {
  currentAlert.value = alert
  showAlertDialog.value = true
}

const resolveAlert = async (alertId) => {
  try {
    await api.post(`/agent/alerts/${alertId}/resolve`)
    ElMessage.success('预警已忽略')
    loadDashboard()
  } catch (error) {
    console.error('操作失败', error)
  }
}

const resolveAlertWithNote = async (alertId) => {
  try {
    await api.post(`/agent/alerts/${alertId}/resolve`, { action_taken: '用户确认已处理' })
    ElMessage.success('预警已标记为已处理')
    showAlertDialog.value = false
    loadDashboard()
  } catch (error) {
    console.error('操作失败', error)
  }
}

const goToEntity = (alert) => {
  showAlertDialog.value = false
  
  if (alert.entity_type === 'customer') {
    router.push('/customers')
  } else if (alert.entity_type === 'opportunity') {
    router.push('/opportunities')
  } else if (alert.entity_type === 'followup') {
    router.push('/follow-ups')
  } else if (alert.entity_type === 'quote') {
    router.push('/quotes')
  }
}

const createGoal = async () => {
  if (!goalForm.value.name || !goalForm.value.target_value) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  try {
    await api.post('/agent/goals', null, {
      params: {
        name: goalForm.value.name,
        target_value: goalForm.value.target_value,
        end_date: goalForm.value.end_date ? new Date(goalForm.value.end_date).toISOString().split('T')[0] : null
      }
    })
    ElMessage.success('目标创建成功')
    showGoalDialog.value = false
    goalForm.value = { name: '', target_value: 100000, end_date: null }
    loadDashboard()
  } catch (error) {
    console.error('创建目标失败', error)
  }
}

const executeRecommendation = async (rec) => {
  if (rec.auto_executable) {
    try {
      await api.post('/agent/autonomous/execute', rec)
      ElMessage.success('已执行推荐操作')
      loadDashboard()
      loadRecommendations()
    } catch (error) {
      console.error('执行失败', error)
      ElMessage.error('执行失败')
    }
  } else {
    ElMessage.info('此操作需要人工确认')
  }
}

onMounted(() => {
  loadDashboard()
  loadAgentStatus()
  loadRecommendations()
})
</script>

<style lang="scss" scoped>
.agent-workspace {
  .workspace-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    .header-left {
      h2 {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0;
        font-size: 24px;
        color: #303133;
        
        .robot-icon {
          color: #667eea;
        }
      }
      
      .subtitle {
        margin: 8px 0 0;
        color: #909399;
        font-size: 14px;
      }
    }
    
    .header-right {
      display: flex;
      align-items: center;
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      
      .el-icon {
        color: #667eea;
      }
    }
  }
  
  .chat-card {
    .chat-container {
      height: 300px;
      overflow-y: auto;
      padding: 16px;
      background: #f5f7fa;
      border-radius: 8px;
      margin-bottom: 16px;
      
      .chat-messages {
        .message {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
          
          &.user {
            flex-direction: row-reverse;
            
            .message-content {
              align-items: flex-end;
            }
            
            .message-text {
              background: #667eea;
              color: #fff;
            }
          }
          
          .message-avatar {
            flex-shrink: 0;
            
            .bot-avatar {
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
          }
          
          .message-content {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-width: 70%;
            
            .message-text {
              padding: 12px 16px;
              border-radius: 12px;
              background: #fff;
              line-height: 1.6;
              white-space: pre-wrap;
              
              &.typing {
                display: flex;
                gap: 4px;
                padding: 16px;
                
                span {
                  width: 8px;
                  height: 8px;
                  background: #667eea;
                  border-radius: 50%;
                  animation: typing 1.4s infinite ease-in-out;
                  
                  &:nth-child(1) { animation-delay: 0s; }
                  &:nth-child(2) { animation-delay: 0.2s; }
                  &:nth-child(3) { animation-delay: 0.4s; }
                }
              }
            }
            
            .message-suggestions {
              display: flex;
              flex-wrap: wrap;
              gap: 8px;
              
              .suggestion-tag {
                cursor: pointer;
                
                &:hover {
                  background: #667eea;
                  color: #fff;
                }
              }
            }
          }
        }
      }
    }
    
    .chat-input {
      margin-bottom: 12px;
    }
    
    .quick-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
  }
  
  @keyframes typing {
    0%, 80%, 100% {
      transform: scale(0.6);
      opacity: 0.5;
    }
    40% {
      transform: scale(1);
      opacity: 1;
    }
  }
  
  .status-card {
    .agent-status {
      .status-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 0;
        border-bottom: 1px solid #ebeef5;
        
        &:last-child {
          border-bottom: none;
        }
        
        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          
          &.active {
            background: #67c23a;
            box-shadow: 0 0 6px #67c23a;
          }
          
          &.inactive {
            background: #909399;
          }
        }
        
        .status-name {
          flex: 1;
          font-size: 13px;
        }
      }
    }
  }
  
  .recommendations-card {
    .empty-recs {
      text-align: center;
      padding: 20px;
      color: #909399;
    }
    
    .recommendations-list {
      .rec-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s;
        
        &:hover {
          background: #f5f7fa;
        }
        
        .rec-priority {
          width: 4px;
          height: 40px;
          border-radius: 2px;
          
          &.high { background: #f56c6c; }
          &.medium { background: #e6a23c; }
          &.low { background: #67c23a; }
        }
        
        .rec-content {
          flex: 1;
          
          .rec-action {
            font-weight: 500;
            color: #303133;
            font-size: 14px;
          }
          
          .rec-reason {
            font-size: 12px;
            color: #909399;
            margin-top: 4px;
          }
        }
        
        .rec-arrow {
          color: #c0c4cc;
        }
      }
    }
  }
  
  .alerts-card {
    .empty-alerts {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px 0;
      color: #67c23a;
      
      p {
        margin-top: 12px;
        color: #909399;
      }
    }
    
    .alerts-list {
      .alert-item {
        display: flex;
        align-items: flex-start;
        gap: 16px;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        background: #f5f7fa;
        transition: all 0.3s;
        
        &:hover {
          transform: translateX(4px);
        }
        
        &.severity-high {
          border-left: 4px solid #f56c6c;
          background: linear-gradient(90deg, #fef0f0 0%, #f5f7fa 100%);
        }
        
        &.severity-medium {
          border-left: 4px solid #e6a23c;
          background: linear-gradient(90deg, #fdf6ec 0%, #f5f7fa 100%);
        }
        
        .alert-icon {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          background: #fff;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #667eea;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .alert-content {
          flex: 1;
          
          .alert-title {
            font-weight: 600;
            color: #303133;
            margin-bottom: 4px;
          }
          
          .alert-desc {
            font-size: 13px;
            color: #606266;
            margin-bottom: 8px;
          }
          
          .alert-action {
            font-size: 12px;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 4px;
          }
        }
        
        .alert-actions {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
      }
    }
  }
  
  .goals-card {
    .empty-goals {
      text-align: center;
      padding: 20px;
      color: #909399;
    }
    
    .goals-list {
      .goal-item {
        padding: 12px 0;
        border-bottom: 1px solid #ebeef5;
        
        &:last-child {
          border-bottom: none;
        }
        
        .goal-info {
          margin-bottom: 8px;
          
          .goal-name {
            font-weight: 500;
            color: #303133;
            margin-bottom: 8px;
          }
        }
        
        .goal-value {
          font-size: 12px;
          color: #909399;
        }
      }
    }
  }
  
  .briefing-card {
    .briefing-stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      
      .stat-item {
        text-align: center;
        
        .stat-value {
          font-size: 24px;
          font-weight: bold;
          color: #303133;
        }
        
        .stat-label {
          font-size: 12px;
          color: #909399;
          margin-top: 4px;
        }
      }
    }
  }
  
  .alert-detail {
    .action-buttons {
      display: flex;
      justify-content: center;
      gap: 16px;
      margin-top: 24px;
    }
  }
}
</style>
