"""
记忆服务 - 管理Agent的记忆系统
支持短期记忆、语义记忆和情节记忆
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from app.models.models import AgentMemory, MemoryType


class MemoryService:
    """
    记忆服务 - 管理Agent的记忆系统
    
    记忆类型:
    - short_term: 短期记忆，会话上下文，自动过期
    - semantic: 语义记忆，结构化知识，持久化
    - episodic: 情节记忆，事件记录，持久化
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def store(
        self,
        content: str,
        memory_type: str = MemoryType.SHORT_TERM.value,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        title: Optional[str] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_hours: Optional[int] = None
    ) -> AgentMemory:
        """
        存储记忆
        """
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        elif memory_type == MemoryType.SHORT_TERM.value:
            expires_at = datetime.now() + timedelta(hours=24)
        
        memory = AgentMemory(
            memory_type=memory_type,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            content=content,
            importance=importance,
            metadata=metadata or {},
            expires_at=expires_at
        )
        
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        
        return memory
    
    async def recall(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[AgentMemory]:
        """
        回忆记忆 - 检索相关记忆
        """
        query = select(AgentMemory).where(
            or_(
                AgentMemory.expires_at == None,
                AgentMemory.expires_at > datetime.now()
            )
        )
        
        if entity_type:
            query = query.where(AgentMemory.entity_type == entity_type)
        if entity_id:
            query = query.where(AgentMemory.entity_id == entity_id)
        if memory_type:
            query = query.where(AgentMemory.memory_type == memory_type)
        
        query = query.order_by(
            desc(AgentMemory.importance),
            desc(AgentMemory.last_accessed)
        ).limit(limit)
        
        result = await self.db.execute(query)
        memories = result.scalars().all()
        
        for memory in memories:
            memory.access_count += 1
            memory.last_accessed = datetime.now()
        
        await self.db.commit()
        
        return memories
    
    async def recall_customer_context(self, customer_id: int) -> Dict[str, Any]:
        """
        回忆客户上下文 - 获取客户相关的所有记忆
        """
        memories = await self.recall(
            entity_type="customer",
            entity_id=customer_id,
            limit=20
        )
        
        context = {
            "customer_id": customer_id,
            "interactions": [],
            "preferences": [],
            "key_events": [],
            "notes": []
        }
        
        for memory in memories:
            if memory.memory_type == MemoryType.EPISODIC.value:
                context["interactions"].append({
                    "title": memory.title,
                    "content": memory.content,
                    "created_at": memory.created_at
                })
            elif memory.memory_type == MemoryType.SEMANTIC.value:
                if "preference" in (memory.extra_data or {}).get("category", ""):
                    context["preferences"].append(memory.content)
                else:
                    context["notes"].append(memory.content)
            elif memory.memory_type == MemoryType.SHORT_TERM.value:
                context["key_events"].append({
                    "title": memory.title,
                    "content": memory.content,
                    "created_at": memory.created_at
                })
        
        return context
    
    async def store_interaction(
        self,
        entity_type: str,
        entity_id: int,
        interaction_type: str,
        content: str,
        outcome: Optional[str] = None
    ) -> AgentMemory:
        """
        存储交互记录（情节记忆）
        """
        title = f"{interaction_type} - {entity_type}#{entity_id}"
        metadata = {
            "interaction_type": interaction_type,
            "outcome": outcome
        }
        
        return await self.store(
            content=content,
            memory_type=MemoryType.EPISODIC.value,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            importance=0.7,
            metadata=metadata
        )
    
    async def store_knowledge(
        self,
        entity_type: str,
        entity_id: int,
        knowledge_type: str,
        content: str,
        importance: float = 0.8
    ) -> AgentMemory:
        """
        存储知识（语义记忆）
        """
        title = f"{knowledge_type} - {entity_type}#{entity_id}"
        metadata = {
            "knowledge_type": knowledge_type,
            "category": knowledge_type
        }
        
        return await self.store(
            content=content,
            memory_type=MemoryType.SEMANTIC.value,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            importance=importance,
            metadata=metadata
        )
    
    async def store_session_context(
        self,
        session_id: str,
        context: Dict[str, Any],
        expires_in_hours: int = 4
    ) -> AgentMemory:
        """
        存储会话上下文（短期记忆）
        """
        import json
        
        return await self.store(
            content=json.dumps(context, ensure_ascii=False),
            memory_type=MemoryType.SHORT_TERM.value,
            entity_type="session",
            entity_id=int(session_id[-8:], 16) % 10000000 if len(session_id) >= 8 else 0,
            title=f"Session {session_id}",
            importance=0.3,
            expires_in_hours=expires_in_hours,
            metadata={"session_id": session_id}
        )
    
    async def forget_expired(self) -> int:
        """
        遗忘过期记忆 - 清理过期的短期记忆
        """
        query = select(AgentMemory).where(
            and_(
                AgentMemory.expires_at != None,
                AgentMemory.expires_at <= datetime.now()
            )
        )
        
        result = await self.db.execute(query)
        expired_memories = result.scalars().all()
        
        count = len(expired_memories)
        for memory in expired_memories:
            await self.db.delete(memory)
        
        await self.db.commit()
        
        return count
    
    async def update_importance(
        self,
        memory_id: int,
        importance: float
    ) -> Optional[AgentMemory]:
        """
        更新记忆重要性
        """
        query = select(AgentMemory).where(AgentMemory.id == memory_id)
        result = await self.db.execute(query)
        memory = result.scalar_one_or_none()
        
        if memory:
            memory.importance = importance
            await self.db.commit()
            await self.db.refresh(memory)
        
        return memory
    
    async def get_important_memories(
        self,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[AgentMemory]:
        """
        获取重要记忆
        """
        query = select(AgentMemory).where(
            or_(
                AgentMemory.expires_at == None,
                AgentMemory.expires_at > datetime.now()
            )
        )
        
        if entity_type:
            query = query.where(AgentMemory.entity_type == entity_type)
        
        query = query.order_by(
            desc(AgentMemory.importance)
        ).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search_by_content(
        self,
        keyword: str,
        limit: int = 10
    ) -> List[AgentMemory]:
        """
        按内容搜索记忆
        """
        query = select(AgentMemory).where(
            and_(
                AgentMemory.content.contains(keyword),
                or_(
                    AgentMemory.expires_at == None,
                    AgentMemory.expires_at > datetime.now()
                )
            )
        ).order_by(
            desc(AgentMemory.importance)
        ).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计
        """
        from sqlalchemy import func
        
        total_query = select(func.count()).select_from(AgentMemory)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar()
        
        type_query = select(
            AgentMemory.memory_type,
            func.count().label('count')
        ).group_by(AgentMemory.memory_type)
        
        type_result = await self.db.execute(type_query)
        type_distribution = {row.memory_type: row.count for row in type_result}
        
        return {
            "total": total,
            "by_type": type_distribution
        }
