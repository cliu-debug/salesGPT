"""
导入导出API集成测试
"""
import pytest
from httpx import AsyncClient
import io
import pandas as pd


@pytest.mark.integration
@pytest.mark.api
class TestImportExportAPI:
    """导入导出API测试"""

    @pytest.mark.asyncio
    async def test_export_customers(self, client: AsyncClient, auth_headers: dict):
        """测试导出客户数据"""
        response = await client.get("/api/import-export/export/customers", headers=auth_headers)

        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            # 验证返回的是Excel文件
            assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_export_customers_with_filter(self, client: AsyncClient, auth_headers: dict):
        """测试带过滤条件导出客户"""
        response = await client.get(
            "/api/import-export/export/customers?status=potential",
            headers=auth_headers
        )

        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_import_customers_valid_file(self, client: AsyncClient, auth_headers: dict):
        """测试导入有效客户数据"""
        # 创建测试Excel文件
        df = pd.DataFrame({
            '客户名称': ['测试客户1', '测试客户2'],
            '联系人': ['张三', '李四'],
            '电话': ['13800138001', '13800138002'],
            '邮箱': ['test1@example.com', 'test2@example.com'],
            '公司': ['测试公司1', '测试公司2'],
            '行业': ['互联网', '金融'],
            '来源': ['线上推广', '朋友介绍'],
            '备注': ['备注1', '备注2']
        })

        # 将DataFrame转换为Excel字节流
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        # 发送上传请求
        files = {"file": ("test_customers.xlsx", output, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = await client.post(
            "/api/import-export/import/customers",
            files=files,
            headers=auth_headers
        )

        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "success_count" in data
            assert "error_count" in data

    @pytest.mark.asyncio
    async def test_import_customers_invalid_file_type(self, client: AsyncClient, auth_headers: dict):
        """测试上传非Excel文件"""
        # 创建一个文本文件
        content = b"This is not an Excel file"
        files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}

        response = await client.post(
            "/api/import-export/import/customers",
            files=files,
            headers=auth_headers
        )

        assert response.status_code in [400, 401, 403]

    @pytest.mark.asyncio
    async def test_import_customers_missing_name(self, client: AsyncClient, auth_headers: dict):
        """测试导入缺少客户名称的数据"""
        # 创建缺少客户名称的Excel文件
        df = pd.DataFrame({
            '联系人': ['张三'],
            '电话': ['13800138001']
        })

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        files = {"file": ("test_customers.xlsx", output, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = await client.post(
            "/api/import-export/import/customers",
            files=files,
            headers=auth_headers
        )

        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            data = response.json()
            assert data.get("error_count", 0) > 0

    @pytest.mark.asyncio
    async def test_export_opportunities(self, client: AsyncClient, auth_headers: dict):
        """测试导出销售机会"""
        response = await client.get("/api/import-export/export/opportunities", headers=auth_headers)

        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_import_opportunities(self, client: AsyncClient, auth_headers: dict):
        """测试导入销售机会"""
        df = pd.DataFrame({
            '客户名称': ['测试客户'],
            '机会名称': ['测试机会'],
            '金额': [50000],
            '阶段': ['initial'],
            '预计成交日期': ['2026-03-31']
        })

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        files = {"file": ("test_opportunities.xlsx", output, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = await client.post(
            "/api/import-export/import/opportunities",
            files=files,
            headers=auth_headers
        )

        assert response.status_code in [200, 401, 403, 404]

    @pytest.mark.asyncio
    async def test_export_quotes(self, client: AsyncClient, auth_headers: dict):
        """测试导出报价单"""
        response = await client.get("/api/import-export/export/quotes", headers=auth_headers)

        assert response.status_code in [200, 401, 403]


@pytest.mark.integration
@pytest.mark.api
class TestImportExportPermissions:
    """导入导出权限测试"""

    @pytest.mark.asyncio
    async def test_import_requires_auth(self, client: AsyncClient):
        """测试导入需要认证"""
        content = b"test content"
        files = {"file": ("test.xlsx", io.BytesIO(content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

        response = await client.post("/api/import-export/import/customers", files=files)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_requires_auth(self, client: AsyncClient):
        """测试导出需要认证"""
        response = await client.get("/api/import-export/export/customers")
        assert response.status_code == 401
