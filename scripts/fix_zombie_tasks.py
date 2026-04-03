"""
僵尸任务清理脚本
将卡住超过 30 分钟的 parsing/ingesting 任务标记为 failed

使用方法:
    uv run python scripts/fix_zombie_tasks.py

建议配合 Cron 定时执行（每 10 分钟一次）:
    */10 * * * * cd /path/to/SmartCS && uv run python scripts/fix_zombie_tasks.py
"""
import asyncio
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlalchemy import update
from app.core.database import async_session_factory
from app.models.admin import KnowledgeDocument


async def cleanup_zombies():
    """将卡住超过 30 分钟的任务标记为失败"""
    threshold_time = datetime.utcnow() - timedelta(minutes=30)

    async with async_session_factory() as db:
        stmt = (
            update(KnowledgeDocument)
            .where(KnowledgeDocument.status.in_(["parsing", "ingesting"]))
            .where(KnowledgeDocument.updated_at < threshold_time)
            .values(status="failed", error_message="系统重启或任务超时，请重试")
        )
        result = await db.execute(stmt)
        await db.commit()

        if result.rowcount > 0:
            print(f"[{datetime.utcnow().isoformat()}] 清理了 {result.rowcount} 个僵尸任务")
        else:
            print(f"[{datetime.utcnow().isoformat()}] 没有发现僵尸任务")


if __name__ == "__main__":
    asyncio.run(cleanup_zombies())
