"""知识库工厂 - 根据配置自动选择 SQLite 或 MySQL 实现。"""

import logging
import os
from pathlib import Path

from video_to_action.base_knowledge_base import BaseKnowledgeBase

logger = logging.getLogger(__name__)


def create_knowledge_base(fallback: bool = True, **kwargs) -> BaseKnowledgeBase:
    """根据配置创建知识库实例。

    优先级：
    1. kwargs 中的 use_mysql 参数
    2. 环境变量 USE_MYSQL
    3. 默认使用 SQLite

    Args:
        fallback: 当 MySQL 连接失败时，是否降级到 SQLite（默认 True）
        use_mysql: 是否使用 MySQL（True/False/None）
        db_path: SQLite 数据库路径（仅 SQLite 模式）
        **kwargs: 传递给 MySQLKnowledgeBase 的额外参数（如 host, port, user, password, database）

    Returns:
        BaseKnowledgeBase 实例
    """
    use_mysql = kwargs.get("use_mysql")

    if use_mysql is None:
        use_mysql = os.getenv("USE_MYSQL", "false").lower() == "true"

    if use_mysql:
        from video_to_action.mysql_knowledge_base import MySQLKnowledgeBase

        try:
            # 移除 use_mysql 参数，不传给 MySQLKnowledgeBase
            mysql_kwargs = {k: v for k, v in kwargs.items() if k != "use_mysql"}
            kb = MySQLKnowledgeBase(**mysql_kwargs)
            logger.info(f"📦 使用 MySQL 知识库: {kb.mysql_config['host']}:{kb.mysql_config['port']}")
            return kb
        except Exception as e:
            if not fallback:
                raise
            logger.warning(f"⚠️ MySQL 连接失败，降级到 SQLite: {e}")

    # 使用 SQLite
    from video_to_action.knowledge_base import KnowledgeBase

    db_path = kwargs.get("db_path")
    # 确保 db_path 是 Path 对象
    if db_path is not None and not isinstance(db_path, Path):
        db_path = Path(db_path)
    logger.info("📦 使用 SQLite 知识库")
    return KnowledgeBase(db_path=db_path)
