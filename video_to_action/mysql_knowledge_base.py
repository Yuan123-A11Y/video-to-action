"""
MySQL 知识库模块 - 使用 MySQL 替代 SQLite。

提供与 KnowledgeBase 相同的接口，但使用 MySQL 数据库。
可以通过环境变量或配置文件切换数据库类型。
"""

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import pymysql
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class MySQLKnowledgeBase:
    """视频知识库，基于 MySQL 存储分析结果。"""

    def __init__(self, use_mysql: Optional[bool] = None):
        """初始化知识库。
        
        Args:
            use_mysql: 是否使用 MySQL。如果为 None，则从环境变量读取。
                       环境变量 USE_MYSQL=true 时使用 MySQL，否则使用 SQLite。
        """
        self.use_mysql = use_mysql if use_mysql is not None else \
            os.getenv("USE_MYSQL", "false").lower() == "true"
        
        if self.use_mysql:
            self.mysql_config = {
                "host": os.getenv("MYSQL_HOST", "localhost"),
                "port": int(os.getenv("MYSQL_PORT", "3306")),
                "user": os.getenv("MYSQL_USER", "root"),
                "password": os.getenv("MYSQL_PASSWORD", ""),
                "database": os.getenv("MYSQL_DATABASE", "video_to_action"),
                "charset": "utf8mb4",
            }
            self._init_mysql_db()
        else:
            # 回退到 SQLite
            from video_to_action.knowledge_base import KnowledgeBase
            self.sqlite_kb = KnowledgeBase()
            logger.info("使用 SQLite 数据库")

    @contextmanager
    def _get_connection(self):
        """获取 MySQL 连接。"""
        conn = pymysql.connect(**self.mysql_config)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_mysql_db(self):
        """初始化 MySQL 数据库（表已通过 schema.sql 创建）。"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM videos LIMIT 1")
                cursor.close()
            logger.info("MySQL 数据库连接成功")
        except Exception as e:
            logger.error(f"MySQL 数据库连接失败: {e}")
            raise

    def add_video_analysis(
        self,
        url: str,
        platform: str,
        title: Optional[str],
        theme: str,
        summary: str,
        transcription_text: str,
        analysis_result: dict,
    ) -> int:
        """添加视频分析结果到知识库。"""
        if not self.use_mysql:
            return self.sqlite_kb.add_video_analysis(
                url, platform, title, theme, summary,
                transcription_text, analysis_result
            )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 插入视频记录
            cursor.execute(
                """INSERT INTO videos 
                   (url, platform, title, theme, summary, transcription_text, analysis_result)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   title = VALUES(title),
                   theme = VALUES(theme),
                   summary = VALUES(summary),
                   transcription_text = VALUES(transcription_text),
                   analysis_result = VALUES(analysis_result),
                   updated_at = CURRENT_TIMESTAMP""",
                (
                    url,
                    platform,
                    title,
                    theme,
                    summary,
                    transcription_text,
                    json.dumps(analysis_result, ensure_ascii=False),
                ),
            )
            video_id = cursor.lastrowid
            
            # 如果没有 lastrowid（因为是 ON DUPLICATE KEY UPDATE），则查询
            if video_id == 0:
                cursor.execute("SELECT id FROM videos WHERE url_hash = SHA2(%s, 256)", (url,))
                row = cursor.fetchone()
                video_id = row[0] if row else 0

            # 插入工具记录
            tools = analysis_result.get("tools", [])
            for tool in tools:
                tool_id = self._add_or_get_tool(conn, tool)
                cursor.execute(
                    """INSERT IGNORE INTO video_tools (video_id, tool_id) VALUES (%s, %s)""",
                    (video_id, tool_id),
                )

            return video_id

    def _add_or_get_tool(self, conn, tool: dict) -> int:
        """添加工具记录或获取已有工具ID。"""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM tools WHERE name_normalized = LOWER(%s)",
            (tool["name"].lower(),)
        )
        row = cursor.fetchone()

        if row:
            cursor.close()
            return row[0]

        cursor.execute(
            """INSERT INTO tools 
               (name, category, purpose, install_commands, config_steps, 
                usage_examples, warnings, alternatives, is_paid, needs_credential)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                tool["name"],
                tool.get("category", ""),
                tool.get("purpose", ""),
                json.dumps(tool.get("install_commands", []), ensure_ascii=False),
                json.dumps(tool.get("config_steps", []), ensure_ascii=False),
                json.dumps(tool.get("usage_examples", []), ensure_ascii=False),
                tool.get("warnings", ""),
                json.dumps(tool.get("alternatives", []), ensure_ascii=False),
                tool.get("is_paid", False),
                tool.get("needs_credential", False),
            ),
        )
        tool_id = cursor.lastrowid
        cursor.close()
        return tool_id

    def search_videos(self, query: str, limit: int = 10) -> list:
        """搜索视频。"""
        if not self.use_mysql:
            return self.sqlite_kb.search_videos(query, limit)

        with self._get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                """SELECT * FROM videos 
                   WHERE MATCH(title) AGAINST (%s IN NATURAL LANGUAGE MODE)
                      OR MATCH(transcription_text) AGAINST (%s IN NATURAL LANGUAGE MODE)
                   LIMIT %s""",
                (query, query, limit)
            )
            results = cursor.fetchall()
            cursor.close()
            return results

    def search_tools(self, query: str, limit: int = 10) -> list:
        """搜索工具。"""
        if not self.use_mysql:
            return self.sqlite_kb.search_tools(query, limit)

        with self._get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                """SELECT * FROM tools 
                   WHERE MATCH(name) AGAINST (%s IN NATURAL LANGUAGE MODE)
                      OR MATCH(purpose) AGAINST (%s IN NATURAL LANGUAGE MODE)
                   LIMIT %s""",
                (query, query, limit)
            )
            results = cursor.fetchall()
            cursor.close()
            return results

    def get_video_count(self) -> int:
        """获取视频总数。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_video_count()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM videos")
            count = cursor.fetchone()[0]
            cursor.close()
            return count

    def get_tool_count(self) -> int:
        """获取工具总数。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_tool_count()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tools")
            count = cursor.fetchone()[0]
            cursor.close()
            return count

    def get_all_videos(self, limit: int = 100, offset: int = 0) -> list:
        """获取所有视频。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_all_videos(limit, offset)

        with self._get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT * FROM videos ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset)
            )
            results = cursor.fetchall()
            cursor.close()
            return results

    def get_all_tools(self, limit: int = 100, offset: int = 0) -> list:
        """获取所有工具。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_all_tools(limit, offset)

        with self._get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT * FROM tools ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset)
            )
            results = cursor.fetchall()
            cursor.close()
            return results

    def close(self):
        """关闭数据库连接（兼容接口）。"""
        if not self.use_mysql:
            # SQLite 连接在每个操作后立即关闭，无需额外操作
            pass
