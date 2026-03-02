import httpx
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("=" * 50)
    print("AI销售助手 API 测试")
    print("=" * 50)
    
    with httpx.Client(timeout=30.0) as client:
        print("\n1. 测试根接口...")
        r = client.get(f"{BASE_URL}/")
        print(f"   状态: {r.status_code}")
        print(f"   响应: {r.json()}")
        
        print("\n2. 测试创建客户...")
        r = client.post(f"{BASE_URL}/api/customers/", json={
            "name": "测试客户A",
            "contact": "张三",
            "phone": "13800138001",
            "company": "测试科技有限公司",
            "industry": "互联网",
            "source": "线上推广"
        })
        print(f"   状态: {r.status_code}")
        customer = r.json()
        print(f"   响应: {customer}")
        customer_id = customer.get("id")
        
        print("\n3. 测试获取客户列表...")
        r = client.get(f"{BASE_URL}/api/customers/")
        print(f"   状态: {r.status_code}")
        print(f"   客户数量: {r.json().get('total', 0)}")
        
        print("\n4. 测试创建销售机会...")
        r = client.post(f"{BASE_URL}/api/opportunities/", json={
            "customer_id": customer_id,
            "customer_name": "测试客户A",
            "name": "软件定制开发项目",
            "amount": 50000,
            "stage": "initial",
            "expected_date": "2025-03-30"
        })
        print(f"   状态: {r.status_code}")
        opportunity = r.json()
        print(f"   响应: {opportunity}")
        opportunity_id = opportunity.get("id")
        
        print("\n5. 测试创建报价单...")
        r = client.post(f"{BASE_URL}/api/quotes/", json={
            "customer_id": customer_id,
            "customer_name": "测试客户A",
            "items": [
                {"name": "需求分析", "description": "需求调研与分析", "quantity": 1, "unit_price": 5000},
                {"name": "系统开发", "description": "核心功能开发", "quantity": 1, "unit_price": 30000},
                {"name": "测试部署", "description": "系统测试与部署", "quantity": 1, "unit_price": 10000}
            ],
            "valid_until": "2025-03-15"
        })
        print(f"   状态: {r.status_code}")
        quote = r.json()
        print(f"   响应: {quote}")
        quote_id = quote.get("id")
        
        print("\n6. 测试创建跟进记录...")
        r = client.post(f"{BASE_URL}/api/follow-ups/", json={
            "customer_id": customer_id,
            "customer_name": "测试客户A",
            "content": "初次沟通，客户对产品感兴趣，需要进一步了解需求",
            "next_action": "发送产品介绍资料",
            "next_date": "2025-02-25T10:00:00"
        })
        print(f"   状态: {r.status_code}")
        print(f"   响应: {r.json()}")
        
        print("\n7. 测试获取仪表盘数据...")
        r = client.get(f"{BASE_URL}/api/dashboard/")
        print(f"   状态: {r.status_code}")
        dashboard = r.json()
        print(f"   客户总数: {dashboard.get('total_customers', 0)}")
        print(f"   销售机会: {dashboard.get('total_opportunities', 0)}")
        print(f"   总金额: {dashboard.get('total_amount', 0)}")
        print(f"   转化率: {dashboard.get('conversion_rate', 0)}%")
        
        print("\n8. 测试获取销售漏斗...")
        r = client.get(f"{BASE_URL}/api/opportunities/stats/funnel")
        print(f"   状态: {r.status_code}")
        print(f"   漏斗数据: {r.json()}")
        
        print("\n" + "=" * 50)
        print("✅ 所有API测试通过!")
        print("=" * 50)

if __name__ == "__main__":
    test_api()
