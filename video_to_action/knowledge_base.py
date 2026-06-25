"""视频知识库模块 - 存储和检索历史分析结果。"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """视频知识库，基于 SQLite 存储分析结果。"""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE NOT NULL,
        platform TEXT NOT NULL,
        title TEXT,
        theme TEXT,
        summary TEXT,
        transcription_text TEXT,
        analysis_result TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        purpose TEXT,
        install_commands TEXT,
        config_steps TEXT,
        warnings TEXT,
        alternatives TEXT,
        is_paid BOOLEAN DEFAULT 0,
        needs_credential BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS video_tools (
        video_id INTEGER,
        tool_id INTEGER,
        FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
        FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE,
        PRIMARY KEY (video_id, tool_id)
    );

    CREATE INDEX IF NOT EXISTS idx_videos_platform ON videos(platform);
    CREATE INDEX IF NOT EXISTS idx_videos_theme ON videos(theme);
    CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
    """

    def __init__(self, db_path: Optional[Path] = None):
        """初始化知识库，创建数据库连接和表结构。"""
        if db_path is None:
            # 默认使用项目目录下的 data/ 子目录
            _root = Path(__file__).resolve().parent.parent
            db_path = _root / "data" / "knowledge_base.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self):
        """获取数据库连接，自动提交/回滚并关闭。

        sqlite3 的 ``with conn`` 仅管理事务（commit/rollback），
        不会关闭连接，需手动 close 否则触发 ResourceWarning。
        """
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表结构。"""
        with self._connect() as conn:
            conn.executescript(self.SCHEMA)

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
        """添加视频分析结果到知识库。

        Args:
            url: 视频URL
            platform: 平台名称
            title: 视频标题
            theme: 视频主题
            summary: 视频摘要
            transcription_text: 转录文本
            analysis_result: 分析结果字典

        Returns:
            插入的视频ID
        """
        with self._connect() as conn:
            # 插入视频记录
            cursor = conn.execute(
                """INSERT OR REPLACE INTO videos
                   (url, platform, title, theme, summary, transcription_text, analysis_result)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
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

            # 插入工具记录
            tools = analysis_result.get("tools", [])
            for tool in tools:
                tool_id = self._add_or_get_tool(conn, tool)
                conn.execute(
                    "INSERT OR IGNORE INTO video_tools (video_id, tool_id) VALUES (?, ?)",
                    (video_id, tool_id),
                )

            return video_id

    def _add_or_get_tool(self, conn: sqlite3.Connection, tool: dict) -> int:
        """添加工具记录或获取已有工具ID。"""
        cursor = conn.execute("SELECT id FROM tools WHERE name = ?", (tool["name"],))
        row = cursor.fetchone()

        if row:
            return row[0]

        cursor = conn.execute(
            """INSERT INTO tools
               (name, purpose, install_commands, config_steps, warnings, alternatives, is_paid, needs_credential)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tool["name"],
                tool.get("purpose", ""),
                json.dumps(tool.get("install_commands", []), ensure_ascii=False),
                json.dumps(tool.get("config_steps", []), ensure_ascii=False),
                json.dumps(tool.get("warnings", []), ensure_ascii=False),
                json.dumps(tool.get("alternative_tools", []), ensure_ascii=False),
                tool.get("is_paid", False),
                tool.get("needs_credential", False),
            ),
        )
        return cursor.lastrowid

    def search_videos(self, query: str, limit: int = 10) -> list[dict]:
        """搜索视频（基于 LIKE 模糊匹配）。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            pattern = f"%{query}%"
            cursor = conn.execute(
                """SELECT * FROM videos
                   WHERE title LIKE ? OR theme LIKE ? OR summary LIKE ?
                   ORDER BY created_at DESC LIMIT ?""",
                (pattern, pattern, pattern, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def search_tools(self, query: str, limit: int = 10) -> list[dict]:
        """搜索工具。

        Args:
            query: 搜索关键词
            limit: 返回结果数量限制

        Returns:
            匹配的工具记录列表
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM tools
                   WHERE name LIKE ? OR purpose LIKE ?
                   LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_video_by_url(self, url: str) -> Optional[dict]:
        """根据URL获取视频分析结果。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM videos WHERE url = ?", (url,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_tool_by_name(self, name: str) -> Optional[dict]:
        """根据工具名称获取工具信息。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tools WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_video_tools(self, video_id: int) -> list[dict]:
        """获取视频关联的工具列表。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT t.* FROM tools t
                   JOIN video_tools vt ON t.id = vt.tool_id
                   WHERE vt.video_id = ?""",
                (video_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def export_handbook(self, output_path: Optional[Path] = None) -> Path:
        """导出操作手册（Markdown格式）。

        Args:
            output_path: 输出文件路径，默认为 outputs/handbook.md

        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = Path("outputs") / "handbook.md"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row

            # 获取所有工具
            tools = conn.execute("SELECT * FROM tools ORDER BY name").fetchall()

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# 视频知识库操作手册\n\n")
                f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")

                for tool in tools:
                    tool = dict(tool)
                    f.write(f"## {tool['name']}\n\n")
                    f.write(f"**用途**：{tool['purpose']}\n\n")

                    if tool["install_commands"]:
                        install_cmds = json.loads(tool["install_commands"])
                        if install_cmds:
                            f.write("**安装命令**：\n")
                            for cmd in install_cmds:
                                f.write(f"- `{cmd}`\n")
                            f.write("\n")

                    if tool["config_steps"]:
                        config_steps = json.loads(tool["config_steps"])
                        if config_steps:
                            f.write("**配置步骤**：\n")
                            for step in config_steps:
                                f.write(f"- {step}\n")
                            f.write("\n")

                    if tool["warnings"]:
                        warnings = json.loads(tool["warnings"])
                        if warnings:
                            f.write("**注意事项**：\n")
                            for warning in warnings:
                                f.write(f"- ⚠️ {warning}\n")
                            f.write("\n")

                    if tool["alternatives"]:
                        alternatives = json.loads(tool["alternatives"])
                        if alternatives:
                            f.write(f"**替代工具**：{', '.join(alternatives)}\n\n")

                    # 查找使用此工具的视频
                    videos = conn.execute(
                        """SELECT v.* FROM videos v
                           JOIN video_tools vt ON v.id = vt.video_id
                           WHERE vt.tool_id = ?""",
                        (tool["id"],),
                    ).fetchall()

                    if videos:
                        f.write("**相关视频**：\n")
                        for video in videos:
                            video = dict(video)
                            f.write(f"- [{video['platform']}] {video['title'] or video['theme']}\n")
                        f.write("\n")

                    f.write("---\n\n")

        return output_path

    def get_statistics(self) -> dict:
        """获取知识库统计信息。"""
        with self._connect() as conn:
            video_count = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
            tool_count = conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
            platform_stats = conn.execute("SELECT platform, COUNT(*) as count FROM videos GROUP BY platform").fetchall()

            return {
                "video_count": video_count,
                "tool_count": tool_count,
                "platform_stats": [dict(row) for row in platform_stats],
            }

    def close(self):
        """兼容接口：连接在每次操作后已自动关闭，无需手动调用。"""
