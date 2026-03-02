from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import pandas as pd
import io
from urllib.parse import quote
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import require_permission
from app.models.models import Customer, Opportunity, Quote, User

router = APIRouter()


@router.post("/import/customers", response_model=dict)
async def import_customers(
    file: UploadFile = File(...),
    current_user: User = require_permission("import-export:write"),
    db: AsyncSession = Depends(get_db)
):
    """
    批量导入客户数据（Excel格式）
    
    Excel列名：客户名称、联系人、电话、邮箱、公司、行业、来源、备注
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传Excel文件（.xlsx或.xls）")
    
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
        
        column_mapping = {
            '客户名称': 'name',
            '联系人': 'contact',
            '电话': 'phone',
            '邮箱': 'email',
            '公司': 'company',
            '行业': 'industry',
            '来源': 'source',
            '备注': 'remark'
        }
        
        df = df.rename(columns=column_mapping)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                if pd.isna(row.get('name')) or str(row.get('name')).strip() == '':
                    errors.append(f"第{index + 2}行：客户名称不能为空")
                    error_count += 1
                    continue
                
                customer = Customer(
                    name=str(row.get('name', '')).strip(),
                    contact=str(row.get('contact', '')).strip() if pd.notna(row.get('contact')) else None,
                    phone=str(row.get('phone', '')).strip() if pd.notna(row.get('phone')) else None,
                    email=str(row.get('email', '')).strip() if pd.notna(row.get('email')) else None,
                    company=str(row.get('company', '')).strip() if pd.notna(row.get('company')) else None,
                    industry=str(row.get('industry', '')).strip() if pd.notna(row.get('industry')) else None,
                    source=str(row.get('source', '')).strip() if pd.notna(row.get('source')) else None,
                    remark=str(row.get('remark', '')).strip() if pd.notna(row.get('remark')) else None,
                    status='potential'
                )
                db.add(customer)
                success_count += 1
            except Exception as e:
                errors.append(f"第{index + 2}行：{str(e)}")
                error_count += 1
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"导入完成：成功{success_count}条，失败{error_count}条",
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors[:10] if errors else []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败：{str(e)}")


@router.get("/export/customers")
async def export_customers(
    status: Optional[str] = None,
    current_user: User = require_permission("import-export:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    导出客户数据为Excel
    """
    query = select(Customer)
    
    if status:
        query = query.where(Customer.status == status)
    
    query = query.order_by(Customer.created_at.desc())
    result = await db.execute(query)
    customers = result.scalars().all()
    
    data = []
    for c in customers:
        data.append({
            '客户名称': c.name,
            '联系人': c.contact or '',
            '电话': c.phone or '',
            '邮箱': c.email or '',
            '公司': c.company or '',
            '行业': c.industry or '',
            '来源': c.source or '',
            '状态': c.status,
            '备注': c.remark or '',
            '创建时间': c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else ''
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='客户数据')
    output.seek(0)
    
    filename = f"客户数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded_filename = quote(filename)
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"}
    )


@router.get("/export/opportunities")
async def export_opportunities(
    stage: Optional[str] = None,
    current_user: User = require_permission("import-export:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    导出销售机会数据为Excel
    """
    query = select(Opportunity)
    
    if stage:
        query = query.where(Opportunity.stage == stage)
    
    query = query.order_by(Opportunity.created_at.desc())
    result = await db.execute(query)
    opportunities = result.scalars().all()
    
    stage_names = {
        'initial': '初步接触',
        'need_confirm': '需求确认',
        'quoting': '报价中',
        'negotiating': '谈判中',
        'closed_won': '成交',
        'closed_lost': '失败'
    }
    
    data = []
    for o in opportunities:
        data.append({
            '机会名称': o.name,
            '客户': o.customer_name or '',
            '金额': o.amount or 0,
            '阶段': stage_names.get(o.stage, o.stage),
            '成交概率': f"{o.probability}%" if o.probability else '0%',
            '预计成交日期': o.expected_date.strftime('%Y-%m-%d') if o.expected_date else '',
            '备注': o.remark or '',
            '创建时间': o.created_at.strftime('%Y-%m-%d %H:%M:%S') if o.created_at else ''
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='销售机会')
    output.seek(0)
    
    filename = f"销售机会_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded_filename = quote(filename)
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"}
    )


@router.get("/export/quotes")
async def export_quotes(
    status: Optional[str] = None,
    current_user: User = require_permission("import-export:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    导出报价单数据为Excel
    """
    query = select(Quote)
    
    if status:
        query = query.where(Quote.status == status)
    
    query = query.order_by(Quote.created_at.desc())
    result = await db.execute(query)
    quotes = result.scalars().all()
    
    status_names = {
        'draft': '草稿',
        'sent': '已发送',
        'accepted': '已接受',
        'rejected': '已拒绝'
    }
    
    data = []
    for q in quotes:
        data.append({
            '报价单号': q.id,
            '客户': q.customer_name or '',
            '总金额': q.total_amount or 0,
            '状态': status_names.get(q.status, q.status),
            '有效期至': q.valid_until.strftime('%Y-%m-%d') if q.valid_until else '',
            '备注': q.remark or '',
            '创建时间': q.created_at.strftime('%Y-%m-%d %H:%M:%S') if q.created_at else ''
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='报价单')
    output.seek(0)
    
    filename = f"报价单_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded_filename = quote(filename)
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"}
    )


@router.get("/template/customers")
async def download_customer_template(
    current_user: User = require_permission("import-export:read"),
):
    """
    下载客户导入模板
    """
    data = [{
        '客户名称': '示例客户',
        '联系人': '张三',
        '电话': '13800138000',
        '邮箱': 'zhangsan@example.com',
        '公司': '示例科技有限公司',
        '行业': '互联网',
        '来源': '线上推广',
        '备注': '这是备注信息'
    }]
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='客户数据')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': "attachment; filename*=UTF-8''%E5%AE%A2%E6%88%B7%E5%AF%BC%E5%85%A5%E6%A8%A1%E6%9D%BF.xlsx"}
    )
