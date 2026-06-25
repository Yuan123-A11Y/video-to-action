"""
MySQL 知识库模块 - 使用 MySQL 替代 SQLite。

提供与 KnowledgeBase 完全相同的接口，但使用 MySQL 数据库。
可以通过环境变量或构造函数参数切换数据库类型。
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
    """视频知识库，基于 MySQL 存储分析结果。
    
    提供与 KnowledgeBase (SQLite) 完全相同的接口。
    """

    def __init__(self, use_mysql: Optional[bool] = None, **kwargs):
        """初始化知识库。
        
        Args:
            use_mysql: 是否使用 MySQL。
                - None: 从环境变量 USE_MYSQL 读取
                - True/False: 强制使用/不使用 MySQL
            **kwargs: MySQL 连接参数（host, port, user, password, database）
        """
        self.use_mysql = use_mysql if use_mysql is not None else \
            os.getenv("USE_MYSQL", "false").lower() == "true"
        
        if self.use_mysql:
            self.mysql_config = {
                "host": kwargs.get("host") or os.getenv("MYSQL_HOST", "localhost"),
                "port": kwargs.get("port") or int(os.getenv("MYSQL_PORT", "3306")),
                "user": kwargs.get("user") or os.getenv("MYSQL_USER", "root"),
                "password": kwargs.get("password") or os.getenv("MYSQL_PASSWORD", ""),
                "database": kwargs.get("database") or os.getenv("MYSQL_DATABASE", "video_to_action"),
                "charset": "utf8mb4",
                "cursorclass": pymysql.cursors.DictCursor,
            }
            self._test_connection()
            logger.info(f"✅ MySQL 数据库连接成功: {self.mysql_config['host']}:{self.mysql_config['port']}")
        else:
            # 回退到 SQLite
            from video_to_action.knowledge_base import KnowledgeBase
            self.sqlite_kb = KnowledgeBase()
            logger.info("✅ 使用 SQLite 数据库")

    def _test_connection(self):
        """测试 MySQL 连接。"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
        except Exception as e:
            logger.error(f"❌ MySQL 数据库连接失败: {e}")
            raise

    @contextmanager
    def _get_connection(self):
        """获取 MySQL 连接（上下文管理器）。"""
        conn = pymysql.connect(**self.mysql_config)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

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
            
            # 插入视频记录（使用 ON DUPLICATE KEY UPDATE 处理重复）
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
            
            # 获取 video_id（可能是新插入的，也可能是已存在的）
            if cursor.lastrowid > 0:
                video_id = cursor.lastrowid
            else:
                # 查询已存在的记录
                cursor.execute("SELECT id FROM videos WHERE url_hash = SHA2(%s, 256)", (url,))
                row = cursor.fetchone()
                video_id = row["id"] if row else 0

            # 插入工具记录
            tools = analysis_result.get("tools", [])
            for tool in tools:
                tool_id = self._add_or_get_tool(conn, tool)
                cursor.execute(
                    """INSERT IGNORE INTO video_tools (video_id, tool_id) VALUES (%s, %s)""",
                    (video_id, tool_id),
                )

            cursor.close()
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
            return row["id"]

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
        """搜索视频（基于 LIKE 模糊匹配，与 SQLite 版本兼容）。"""
        if not self.use_mysql:
            return self.sqlite_kb.search_videos(query, limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query}%"
            cursor.execute(
                """SELECT * FROM videos 
                   WHERE title LIKE %s OR theme LIKE %s OR summary LIKE %s
                   ORDER BY created_at DESC LIMIT %s""",
                (pattern, pattern, pattern, limit)
            )
            results = cursor.fetchall()
            cursor.close()
            return results

    def search_tools(self, query: str, limit: int = 10) -> list:
        """搜索工具（基于 LIKE 模糊匹配）。"""
        if not self.use_mysql:
            return self.sqlite_kb.search_tools(query, limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query}%"
            cursor.execute(
                """SELECT * FROM tools 
                   WHERE name LIKE %s OR purpose LIKE %s
                   LIMIT %s""",
                (pattern, pattern, limit)
            )
            results = cursor.fetchall()
            # 解析 JSON 字段
            for tool in results:
                for field in ["install_commands", "config_steps", "usage_examples", "warnings", "alternatives"]:
                    if tool.get(field):
                        try:
                            tool[field] = json.loads(tool[field])
                        except:
                            pass
            cursor.close()
            return results

    def get_video_by_url(self, url: str) -> Optional[dict]:
        """根据URL获取视频分析结果。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_video_by_url(url)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos WHERE url_hash = SHA2(%s, 256)", (url,))
            row = cursor.fetchone()
            cursor.close()
            if row and row.get("analysis_result"):
                try:
                    row["analysis_result"] = json.loads(row["analysis_result"])
                except:
                    pass
            return row

    def get_tool_by_name(self, name: str) -> Optional[dict]:
        """根据工具名称获取工具信息。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_tool_by_name(name)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tools WHERE name_normalized = LOWER(%s)", (name.lower(),))
            row = cursor.fetchone()
            cursor.close()
            if row:
                for field in ["install_commands", "config_steps", "usage_examples", "warnings", "alternatives"]:
                    if row.get(field):
                        try:
                            row[field] = json.loads(row[field])
                        except:
                            pass
            return row

    def get_video_tools(self, video_id: int) -> list:
        """获取视频关联的工具列表。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_video_tools(video_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT t.* FROM tools t
                   JOIN video_tools vt ON t.id = vt.tool_id
                   WHERE vt.video_id = %s""",
                (video_id,)
            )
            results = cursor.fetchall()
            for tool in results:
                for field in ["install_commands", "config_steps", "usage_examples", "warnings", "alternatives"]:
                    if tool.get(field):
                        try:
                            tool[field] = json.loads(tool[field])
                        except:
                            pass
            cursor.close()
            return results

    def get_statistics(self) -> dict:
        """获取知识库统计信息。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_statistics()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM videos")
            video_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM tools")
            tool_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT platform, COUNT(*) as count FROM videos GROUP BY platform")
            platform_stats = cursor.fetchall()
            
            cursor.close()
            return {
                "video_count": video_count,
                "tool_count": tool_count,
                "platform_stats": platform_stats,
            }

    def get_videos(self, limit: int = 50, offset: int = 0) -> list:
        """获取视频列表（分页）。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_videos(limit, offset)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM videos ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset)
            )
            results = cursor.fetchall()
            cursor.close()
            return results

    def get_video(self, video_id: int) -> Optional[dict]:
        """获取视频详情（包含关联工具）。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_video(video_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos WHERE id = %s", (video_id,))
            row = cursor.fetchone()
            
            if not row:
                cursor.close()
                return None
            
            # 获取关联的工具
            cursor.execute(
                """SELECT t.* FROM tools t
                   JOIN video_tools vt ON t.id = vt.tool_id
                   WHERE vt.video_id = %s""",
                (video_id,)
            )
            row["tools"] = cursor.fetchall()
            
            # 解析 analysis_result
            if row.get("analysis_result"):
                try:
                    row["analysis_result"] = json.loads(row["analysis_result"])
                except:
                    pass
            
            cursor.close()
            return row

    def get_tools(self, limit: int = 50, offset: int = 0) -> list:
        """获取工具列表（分页）。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_tools(limit, offset)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tools ORDER BY name LIMIT %s OFFSET %s",
                (limit, offset)
            )
            results = cursor.fetchall()
            
            # 解析 JSON 字段
            for tool in results:
                for field in ["install_commands", "config_steps", "usage_examples", "warnings", "alternatives"]:
                    if tool.get(field):
                        try:
                            tool[field] = json.loads(tool[field])
                        except:
                            pass
            
            cursor.close()
            return results

    def get_tool(self, tool_id: int) -> Optional[dict]:
        """获取工具详情（包含使用该工具的视频）。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_tool(tool_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tools WHERE id = %s", (tool_id,))
            row = cursor.fetchone()
            
            if not row:
                cursor.close()
                return None
            
            # 解析 JSON 字段
            for field in ["install_commands", "config_steps", "usage_examples", "warnings", "alternatives"]:
                if row.get(field):
                    try:
                        row[field] = json.loads(row[field])
                    except:
                        pass
            
            # 获取使用此工具的视频
            cursor.execute(
                """SELECT v.* FROM videos v
                   JOIN video_tools vt ON v.id = vt.video_id
                   WHERE vt.tool_id = %s""",
                (tool_id,)
            )
            row["videos"] = cursor.fetchall()
            
            cursor.close()
            return row

    def get_videos_count(self) -> int:
        """获取视频总数。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_videos_count()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM videos")
            count = cursor.fetchone()["count"]
            cursor.close()
            return count

    def get_tools_count(self) -> int:
        """获取工具总数。"""
        if not self.use_mysql:
            return self.sqlite_kb.get_tools_count()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM tools")
            count = cursor.fetchone()["count"]
            cursor.close()
            return count

    def delete_video(self, video_id: int) -> bool:
        """删除视频（同时删除 video_tools 关联记录）。"""
        if not self.use_mysql:
            return self.sqlite_kb.delete_video(video_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 先删除关联记录
            cursor.execute("DELETE FROM video_tools WHERE video_id = %s", (video_id,))
            # 再删除视频
            cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted

    def update_video(self, video_id: int, **kwargs) -> bool:
        """更新视频信息。"""
        if not self.use_mysql:
            return self.sqlite_kb.update_video(video_id, **kwargs)

        # 构建 UPDATE 语句
        allowed_fields = ["title", "theme", "summary", "transcription_text", "analysis_result"]
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = %s")
                params.append(json.dumps(value, ensure_ascii=False) if key == "analysis_result" else value)
        
        if not updates:
            return False
        
        params.append(video_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE videos SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                params
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated

    def delete_tool(self, tool_id: int) -> bool:
        """删除工具（同时删除 video_tools 关联记录）。"""
        if not self.use_mysql:
            return self.sqlite_kb.delete_tool(tool_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 先删除关联记录
            cursor.execute("DELETE FROM video_tools WHERE tool_id = %s", (tool_id,))
            # 再删除工具
            cursor.execute("DELETE FROM tools WHERE id = %s", (tool_id,))
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted

    def update_tool(self, tool_id: int, **kwargs) -> bool:
        """更新工具信息。"""
        if not self.use_mysql:
            return self.sqlite_kb.update_tool(tool_id, **kwargs)

        # 构建 UPDATE 语句
        allowed_fields = ["name", "category", "purpose", "install_commands", "config_steps", 
                         "usage_examples", "warnings", "alternatives", "is_paid", "needs_credential"]
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = %s")
                if key in ["install_commands", "config_steps", "usage_examples", "alternatives"]:
                    params.append(json.dumps(value, ensure_ascii=False))
                else:
                    params.append(value)
        
        if not updates:
            return False
        
        params.append(tool_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE tools SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                params
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated

    def close(self):
        """关闭数据库连接（兼容接口）。"""
        if not self.use_mysql:
            pass  # SQLite 连接在每个操作后立即关闭
