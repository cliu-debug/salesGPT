"""
数据库优化脚本
用于分析和优化数据库性能
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, engine
from app.core.config import settings
from app.core.logger import logger


async def analyze_table_sizes():
    """分析表大小"""
    async with AsyncSessionLocal() as db:
        if settings.DATABASE_URL.startswith("postgresql"):
            # PostgreSQL表大小分析
            result = await db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_total_relation_size(schemaname||'.'||tablename) as bytes,
                    pg_stat_get_tuples_returned(c.oid) as seq_scan,
                    pg_stat_get_tuples_fetched(c.oid) as idx_scan
                FROM pg_tables t
                LEFT JOIN pg_class c ON c.relname = t.tablename
                WHERE schemaname = 'public'
                ORDER BY bytes DESC
            """))
            
            print("\n========== 表大小统计 ==========")
            print(f"{'表名':<30} {'大小':<15} {'顺序扫描':<12} {'索引扫描':<12}")
            print("-" * 70)
            
            for row in result:
                print(f"{row.tablename:<30} {row.total_size:<15} {row.seq_scan or 0:<12} {row.idx_scan or 0:<12}")
        
        else:
            # SQLite表大小分析
            result = await db.execute(text("""
                SELECT name FROM sqlite_master WHERE type='table'
            """))
            tables = [r[0] for r in result]
            
            print("\n========== 表统计 ==========")
            for table in tables:
                count_result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.scalar()
                print(f"{table}: {count} 条记录")


async def analyze_index_usage():
    """分析索引使用情况"""
    async with AsyncSessionLocal() as db:
        if settings.DATABASE_URL.startswith("postgresql"):
            result = await db.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes
                ORDER BY idx_scan ASC
            """))
            
            print("\n========== 索引使用统计 ==========")
            print(f"{'表名':<20} {'索引名':<40} {'扫描次数':<12} {'大小':<10}")
            print("-" * 85)
            
            for row in result:
                print(f"{row.tablename:<20} {row.indexname:<40} {row.idx_scan:<12} {row.index_size:<10}")
            
            # 找出未使用的索引
            result = await db.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                AND indexname NOT LIKE '%_pkey'
            """))
            
            unused = list(result)
            if unused:
                print("\n========== 未使用的索引（建议删除） ==========")
                for row in unused:
                    print(f"  {row.tablename}.{row.indexname}")


async def analyze_slow_queries():
    """分析慢查询（PostgreSQL）"""
    async with AsyncSessionLocal() as db:
        if settings.DATABASE_URL.startswith("postgresql"):
            try:
                result = await db.execute(text("""
                    SELECT
                        query,
                        calls,
                        total_time / 1000 as total_time_sec,
                        mean_time / 1000 as mean_time_sec,
                        rows
                    FROM pg_stat_statements
                    ORDER BY mean_time DESC
                    LIMIT 20
                """))
                
                print("\n========== 慢查询TOP20 ==========")
                print(f"{'平均时间(s)':<15} {'调用次数':<12} {'返回行数':<12} {'查询'}")
                print("-" * 100)
                
                for row in result:
                    query = row.query[:50] + "..." if len(row.query) > 50 else row.query
                    print(f"{row.mean_time_sec:<15.3f} {row.calls:<12} {row.rows:<12} {query}")
            
            except Exception as e:
                print(f"\n无法获取慢查询统计（需要pg_stat_statements扩展）: {e}")


async def vacuum_analyze():
    """执行VACUUM ANALYZE优化"""
    async with AsyncSessionLocal() as db:
        if settings.DATABASE_URL.startswith("postgresql"):
            print("\n========== 执行VACUUM ANALYZE ==========")
            
            # 获取所有表
            result = await db.execute(text("""
                SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            """))
            tables = [r[0] for r in result]
            
            for table in tables:
                try:
                    await db.execute(text(f"VACUUM ANALYZE {table}"))
                    print(f"  ✓ {table}")
                except Exception as e:
                    print(f"  ✗ {table}: {e}")
            
            await db.commit()
            print("VACUUM ANALYZE 完成")


async def rebuild_indexes():
    """重建索引"""
    async with AsyncSessionLocal() as db:
        if settings.DATABASE_URL.startswith("postgresql"):
            print("\n========== 重建索引 ==========")
            
            try:
                await db.execute(text("REINDEX DATABASE postgres"))
                await db.commit()
                print("  ✓ 所有索引重建完成")
            except Exception as e:
                print(f"  ✗ 索引重建失败: {e}")


async def cleanup_old_data(days: int = 90):
    """清理旧数据"""
    async with AsyncSessionLocal() as db:
        print(f"\n========== 清理{days}天前的旧数据 ==========")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 清理旧的审计日志
        result = await db.execute(
            text("DELETE FROM audit_logs WHERE created_at < :cutoff"),
            {"cutoff": cutoff_date}
        )
        deleted_logs = result.rowcount
        await db.commit()
        print(f"  删除审计日志: {deleted_logs} 条")
        
        # 清理已完成的Agent任务
        result = await db.execute(
            text("DELETE FROM agent_tasks WHERE status = 'completed' AND created_at < :cutoff"),
            {"cutoff": cutoff_date}
        )
        deleted_tasks = result.rowcount
        await db.commit()
        print(f"  删除已完成任务: {deleted_tasks} 条")
        
        # 清理已解决的预警
        result = await db.execute(
            text("DELETE FROM agent_alerts WHERE is_resolved = true AND created_at < :cutoff"),
            {"cutoff": cutoff_date}
        )
        deleted_alerts = result.rowcount
        await db.commit()
        print(f"  删除已解决预警: {deleted_alerts} 条")
        
        print("数据清理完成")


async def generate_performance_report():
    """生成性能报告"""
    print("\n" + "=" * 60)
    print("数据库性能报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    await analyze_table_sizes()
    await analyze_index_usage()
    await analyze_slow_queries()
    
    print("\n" + "=" * 60)
    print("报告结束")
    print("=" * 60)


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("""
数据库优化脚本

用法:
    python optimize_db.py analyze      # 分析数据库性能
    python optimize_db.py vacuum       # 执行VACUUM ANALYZE
    python optimize_db.py reindex      # 重建索引
    python optimize_db.py cleanup [天] # 清理旧数据（默认90天）
    python optimize_db.py all          # 执行所有优化操作
        """)
        return
    
    command = sys.argv[1]
    
    if command == "analyze":
        await generate_performance_report()
    elif command == "vacuum":
        await vacuum_analyze()
    elif command == "reindex":
        await rebuild_indexes()
    elif command == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
        await cleanup_old_data(days)
    elif command == "all":
        await generate_performance_report()
        await vacuum_analyze()
        await cleanup_old_data()
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    asyncio.run(main())
