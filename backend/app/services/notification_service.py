import httpx
from typing import Optional, List, Dict, Any
from app.core.config import settings


class NotificationService:
    """
    通知服务 - 支持钉钉和企业微信
    """
    
    def __init__(self):
        self.dingtalk_webhook = settings.DINGTALK_WEBHOOK
        self.wecom_webhook = None
    
    async def send_dingtalk_message(
        self,
        title: str,
        content: str,
        webhook_url: Optional[str] = None
    ) -> bool:
        """
        发送钉钉消息
        
        Args:
            title: 消息标题
            content: 消息内容
            webhook_url: 自定义webhook地址（可选）
        """
        webhook = webhook_url or self.dingtalk_webhook
        
        if not webhook or webhook == "https://oapi.dingtalk.com/robot/send?access_token=your-token":
            return False
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook, json=payload)
                return response.status_code == 200
        except Exception as e:
            print(f"钉钉消息发送失败: {e}")
            return False
    
    async def send_wecom_message(
        self,
        content: str,
        webhook_url: Optional[str] = None
    ) -> bool:
        """
        发送企业微信消息
        
        Args:
            content: 消息内容
            webhook_url: 自定义webhook地址（可选）
        """
        webhook = webhook_url or self.wecom_webhook
        
        if not webhook:
            return False
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook, json=payload)
                return response.status_code == 200
        except Exception as e:
            print(f"企业微信消息发送失败: {e}")
            return False
    
    async def notify_follow_up(
        self,
        customer_name: str,
        action: str,
        next_date: str,
        platform: str = "dingtalk"
    ) -> bool:
        """
        发送跟进提醒通知
        """
        title = "📅 跟进提醒"
        content = f"""
### 跟进提醒

**客户**: {customer_name}

**待办事项**: {action}

**计划时间**: {next_date}

---
*来自AI销售助手*
"""
        
        if platform == "dingtalk":
            return await self.send_dingtalk_message(title, content)
        elif platform == "wecom":
            return await self.send_wecom_message(content)
        
        return False
    
    async def notify_quote_sent(
        self,
        customer_name: str,
        amount: float,
        quote_id: int,
        platform: str = "dingtalk"
    ) -> bool:
        """
        发送报价单发送通知
        """
        title = "💰 报价单已发送"
        content = f"""
### 报价单已发送

**客户**: {customer_name}

**报价金额**: ¥{amount:,.2f}

**报价单号**: #{quote_id}

---
*来自AI销售助手*
"""
        
        if platform == "dingtalk":
            return await self.send_dingtalk_message(title, content)
        elif platform == "wecom":
            return await self.send_wecom_message(content)
        
        return False
    
    async def notify_opportunity_won(
        self,
        customer_name: str,
        opportunity_name: str,
        amount: float,
        platform: str = "dingtalk"
    ) -> bool:
        """
        发送成交通知
        """
        title = "🎉 成交喜报"
        content = f"""
### 🎉 成交喜报！

**客户**: {customer_name}

**机会名称**: {opportunity_name}

**成交金额**: ¥{amount:,.2f}

恭喜！又成功签下一单！

---
*来自AI销售助手*
"""
        
        if platform == "dingtalk":
            return await self.send_dingtalk_message(title, content)
        elif platform == "wecom":
            return await self.send_wecom_message(content)
        
        return False
    
    async def notify_daily_report(
        self,
        stats: Dict[str, Any],
        platform: str = "dingtalk"
    ) -> bool:
        """
        发送每日销售报告
        """
        title = "📊 每日销售报告"
        content = f"""
### 📊 每日销售报告

**客户数据**
- 总客户数: {stats.get('total_customers', 0)}
- 本月新增: {stats.get('new_customers', 0)}

**销售数据**
- 销售机会: {stats.get('total_opportunities', 0)}
- 总金额: ¥{stats.get('total_amount', 0):,.0f}
- 转化率: {stats.get('conversion_rate', 0)}%

**今日待办**
- 待跟进: {stats.get('today_tasks', 0)} 项

---
*{settings.DASHSCOPE_MODEL or 'AI销售助手'}*
"""
        
        if platform == "dingtalk":
            return await self.send_dingtalk_message(title, content)
        elif platform == "wecom":
            return await self.send_wecom_message(content)
        
        return False


notification_service = NotificationService()
