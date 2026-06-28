"""视频知识库模块 - 存储和检索历史分析结果。"""

import hashlib
import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 慢查询阈值（秒）
SLOW_QUERY_THRESHOLD = 0.1  # 100ms


class LoggingCursor(sqlite3.Cursor):
    """自定义 Cursor 类，自动记录慢查询。"""

    def execute(self, sql: str, parameters: tuple = ()):
        """执行 SQL 并记录慢查询。"""
        start = time.time()
        try:
            return super().execute(sql, parameters)
        finally:
            elapsed = time.time() - start
            if elapsed > SLOW_QUERY_THRESHOLD:
                logger.warning(f"慢查询 ({elapsed:.3f}s): {sql[:100]}... params={parameters[:10] if parameters else '()'}")


class LoggingConnection(sqlite3.Connection):
    """自定义 Connection 类，使用 LoggingCursor。"""

    def cursor(self, factory=None):
        """返回 LoggingCursor 实例。"""
        return super().cursor(LoggingCursor)


class KnowledgeBase:
    """视频知识库，基于 SQLite 存储分析结果。"""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE NOT NULL,
        url_hash TEXT NOT NULL DEFAULT '',
        platform TEXT NOT NULL,
        video_id TEXT,
        title TEXT,
        author_name TEXT,
        author_id TEXT,
        duration INTEGER,
        theme TEXT,
        summary TEXT,
        transcription_text TEXT,
        analysis_result TEXT,
        file_path TEXT,
        file_size INTEGER,
        status TEXT DEFAULT 'pending',
        error_message TEXT,
        view_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        name_normalized TEXT UNIQUE NOT NULL,
        category TEXT,
        purpose TEXT,
        description TEXT,
        install_commands TEXT,
        config_steps TEXT,
        usage_examples TEXT,
        warnings TEXT,
        alternatives TEXT,
        homepage_url TEXT,
        documentation_url TEXT,
        is_paid BOOLEAN DEFAULT 0,
        needs_credential BOOLEAN DEFAULT 0,
        license_type TEXT,
        programming_language TEXT,
        github_url TEXT,
        version TEXT,
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS video_tools (
        video_id INTEGER,
        tool_id INTEGER,
        relevance_score REAL DEFAULT 0.50,
        mention_count INTEGER DEFAULT 1,
        PRIMARY KEY (video_id, tool_id),
        FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
        FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_videos_platform ON videos(platform);
    CREATE INDEX IF NOT EXISTS idx_videos_video_id ON videos(video_id);
    CREATE INDEX IF NOT EXISTS idx_videos_author_id ON videos(author_id);
    CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
    CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at);
    CREATE INDEX IF NOT EXISTS idx_videos_theme ON videos(theme);
    CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
    CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category);
    CREATE INDEX IF NOT EXISTS idx_tools_is_paid ON tools(is_paid);
    CREATE INDEX IF NOT EXISTS idx_video_tools_tool_id ON video_tools(tool_id);
    CREATE INDEX IF NOT EXISTS idx_video_tools_relevance ON video_tools(relevance_score);

    CREATE TABLE IF NOT EXISTS download_jobs (
        job_id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        url_type TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        finished_at TIMESTAMP,
        total_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0,
        skipped_count INTEGER DEFAULT 0,
        error_message TEXT,
        author_nickname TEXT,
        author_sec_uid TEXT,
        retry_count INTEGER DEFAULT 0,
        last_retry_at TIMESTAMP,
        last_retry_summary TEXT,
        retry_history TEXT,
        overrides TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_download_jobs_status ON download_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_download_jobs_created_at ON download_jobs(created_at);

    CREATE TABLE IF NOT EXISTS downloaded_videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aweme_id TEXT NOT NULL,
        aweme_type TEXT NOT NULL,
        title TEXT,
        author_id TEXT,
        author_name TEXT,
        author_sec_uid TEXT,
        create_time TIMESTAMP,
        download_time TIMESTAMP NOT NULL,
        file_path TEXT,
        file_size INTEGER,
        metadata TEXT,
        UNIQUE(aweme_id)
    );

    CREATE INDEX IF NOT EXISTS idx_downloaded_videos_aweme_id ON downloaded_videos(aweme_id);
    CREATE INDEX IF NOT EXISTS idx_downloaded_videos_author_id ON downloaded_videos(author_id);
    CREATE INDEX IF NOT EXISTS idx_downloaded_videos_download_time ON downloaded_videos(download_time);

    CREATE TABLE IF NOT EXISTS transcript_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aweme_id TEXT NOT NULL,
        video_path TEXT NOT NULL,
        transcript_dir TEXT,
        text_path TEXT,
        json_path TEXT,
        model TEXT NOT NULL DEFAULT 'gpt-4o-mini-transcribe',
        status TEXT NOT NULL,
        skip_reason TEXT,
        error_message TEXT,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_transcript_jobs_aweme_id ON transcript_jobs(aweme_id);
    CREATE INDEX IF NOT EXISTS idx_transcript_jobs_status ON transcript_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_transcript_jobs_model ON transcript_jobs(model);

    CREATE TABLE IF NOT EXISTS download_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        url_type TEXT NOT NULL,
        download_time TIMESTAMP NOT NULL,
        total_count INTEGER,
        success_count INTEGER,
        config TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_download_history_download_time ON download_history(download_time);
    CREATE INDEX IF NOT EXISTS idx_download_history_url_type ON download_history(url_type);

    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        query TEXT NOT NULL,
        search_type TEXT DEFAULT 'all',
        result_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
    CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at);

    CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        preferred_platforms TEXT,
        preferred_categories TEXT,
        language TEXT DEFAULT 'zh-CN',
        theme TEXT DEFAULT 'dark',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user' CHECK(role IN ('admin', 'user')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP NULL,
        is_active BOOLEAN DEFAULT 1
    );

    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

    CREATE TABLE IF NOT EXISTS system_config (
        config_key TEXT PRIMARY KEY,
        config_value TEXT,
        config_type TEXT DEFAULT 'string',
        description TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE VIEW IF NOT EXISTS v_video_stats AS
    SELECT
        platform,
        COUNT(*) as total_videos,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_videos,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_videos,
        AVG(file_size) as avg_file_size,
        SUM(file_size) as total_storage
    FROM videos
    GROUP BY platform;

    CREATE VIEW IF NOT EXISTS v_tool_stats AS
    SELECT
        t.id,
        t.name,
        t.category,
        COUNT(vt.video_id) as referenced_count,
        AVG(vt.relevance_score) as avg_relevance
    FROM tools t
    LEFT JOIN video_tools vt ON t.id = vt.tool_id
    GROUP BY t.id, t.name, t.category;
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
        conn = sqlite3.connect(self.db_path, factory=LoggingConnection)
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

            # 迁移：为 user_preferences 表添加 user_id_int 字段（关联 users.id）
            self._migrate_user_preferences_user_id_int(conn)

            # 迁移：为 user_preferences 表添加 user_id_hash 字段（用于索引优化）
            self._migrate_user_preferences_user_id_hash(conn)

        # 初始化默认配置
        self.init_default_config()

    def _migrate_user_preferences_user_id_int(self, conn):
        """迁移：为 user_preferences 表添加 user_id_int 字段。"""
        cursor = conn.execute("PRAGMA table_info(user_preferences)")
        columns = [row[1] for row in cursor.fetchall()]

        if "user_id_int" not in columns:
            # 不再引用 users 表，避免外键约束失败（auth 表独立管理）
            conn.execute("ALTER TABLE user_preferences ADD COLUMN user_id_int INTEGER")
            conn.commit()
            logger.info("✅ 已为 user_preferences 表添加 user_id_int 字段")

    def _migrate_user_preferences_user_id_hash(self, conn):
        """迁移：为 user_preferences 表添加 user_id_hash 字段（用于索引优化）。"""
        cursor = conn.execute("PRAGMA table_info(user_preferences)")
        columns = [row[1] for row in cursor.fetchall()]

        if "user_id_hash" not in columns:
            conn.execute("ALTER TABLE user_preferences ADD COLUMN user_id_hash TEXT")
            # 为现有数据生成 hash
            cursor = conn.execute("SELECT id, user_id FROM user_preferences WHERE user_id_hash IS NULL")
            for row in cursor.fetchall():
                user_id_hash = hashlib.sha256(row[1].encode("utf-8")).hexdigest()
                conn.execute("UPDATE user_preferences SET user_id_hash = ? WHERE id = ?", (user_id_hash, row[0]))
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id_hash ON user_preferences(user_id_hash)")
            conn.commit()
            logger.info("✅ 已为 user_preferences 表添加 user_id_hash 字段")

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
            # 插入视频记录（status 默认 completed，因为分析已完成才调用此方法）
            cursor = conn.execute(
                """INSERT OR REPLACE INTO videos
                   (url, platform, title, theme, summary, transcription_text, analysis_result, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'completed')""",
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

        # 计算 name_normalized
        name_normalized = tool["name"].lower()

        cursor = conn.execute(
            """INSERT INTO tools
               (name, name_normalized, purpose, install_commands, config_steps, warnings, alternatives, is_paid, needs_credential)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tool["name"],
                name_normalized,
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

    def search_videos(self, query: str, limit: int = 10, use_prefix_search: bool = False) -> list[dict]:
        """搜索视频（基于 LIKE 模糊匹配）。

        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            use_prefix_search: 是否使用前缀搜索（更快，但匹配度较低）

        Returns:
            匹配的视频记录列表
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row

            if use_prefix_search:
                # 前缀搜索（可以使用索引，速度更快）
                pattern = f"{query}%"
                cursor = conn.execute(
                    """SELECT id, url, platform, title, theme, summary,
                              file_path, file_size, status, view_count,
                              created_at, updated_at
                       FROM videos
                       WHERE title LIKE ? OR theme LIKE ? OR summary LIKE ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (pattern, pattern, pattern, limit),
                )
            else:
                # 模糊搜索（无法使用索引，但匹配度更高）
                pattern = f"%{query}%"
                cursor = conn.execute(
                    """SELECT id, url, platform, title, theme, summary,
                              file_path, file_size, status, view_count,
                              created_at, updated_at
                       FROM videos
                       WHERE title LIKE ? OR theme LIKE ? OR summary LIKE ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (pattern, pattern, pattern, limit),
                )

            return [dict(row) for row in cursor.fetchall()]

    def search_tools(self, query: str, limit: int = 10, use_prefix_search: bool = False) -> list[dict]:
        """搜索工具。

        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            use_prefix_search: 是否使用前缀搜索（更快，但匹配度较低）

        Returns:
            匹配的工具记录列表
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row

            if use_prefix_search:
                # 前缀搜索（可以使用索引，速度更快）
                pattern = f"{query}%"
                cursor = conn.execute(
                    """SELECT id, name, category, purpose, description,
                              is_paid, needs_credential, homepage_url,
                              github_url, tags, created_at, updated_at
                       FROM tools
                       WHERE name LIKE ? OR purpose LIKE ?
                       LIMIT ?""",
                    (pattern, pattern, limit),
                )
            else:
                # 模糊搜索（无法使用索引，但匹配度更高）
                pattern = f"%{query}%"
                cursor = conn.execute(
                    """SELECT id, name, category, purpose, description,
                              is_paid, needs_credential, homepage_url,
                              github_url, tags, created_at, updated_at
                       FROM tools
                       WHERE name LIKE ? OR purpose LIKE ?
                       LIMIT ?""",
                    (pattern, pattern, limit),
                )

            results = []
            for row in cursor.fetchall():
                tool = dict(row)
                # 解析 JSON 字段（如果需要）
                for field in ["install_commands", "config_steps", "warnings", "alternatives"]:
                    if tool.get(field):
                        try:
                            tool[field] = json.loads(tool[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                results.append(tool)

            return results

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

    def get_tools_with_videos(self) -> list[dict]:
        """获取所有工具及其关联视频（用于导出操作手册）。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row

            # 一次性获取所有工具（按名称排序）
            tools = conn.execute("SELECT * FROM tools ORDER BY name").fetchall()

            # 一次性获取所有工具-视频关联关系（避免 N+1 查询）
            tool_videos_map = {}
            rows = conn.execute("""SELECT vt.tool_id, v.id, v.platform, v.title, v.theme
                   FROM video_tools vt
                   JOIN videos v ON v.id = vt.video_id""").fetchall()
            for row in rows:
                tool_id = row["tool_id"]
                if tool_id not in tool_videos_map:
                    tool_videos_map[tool_id] = []
                tool_videos_map[tool_id].append(dict(row))

            result = []
            for tool in tools:
                tool = dict(tool)
                videos = tool_videos_map.get(tool["id"], [])
                result.append({"tool": tool, "videos": videos})

            return result

    def export_handbook(self, output_path: Optional[Path] = None) -> Path:
        """导出操作手册（Markdown 格式）。"""
        from video_to_action.handbook_exporter import export_handbook as _export

        return _export(self, output_path)

    def get_statistics(self) -> dict:
        """获取知识库统计信息。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            video_count = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
            tool_count = conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
            platform_stats = conn.execute("SELECT platform, COUNT(*) as count FROM videos GROUP BY platform").fetchall()

            # 转换 Row 对象为 dict
            platform_stats_dict = []
            for row in platform_stats:
                platform_stats_dict.append({"platform": row["platform"], "count": row["count"]})

            return {
                "video_count": video_count,
                "tool_count": tool_count,
                "platform_stats": platform_stats_dict,
            }

    def get_videos(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        获取视频列表（分页）。

        Args:
            limit: 返回记录数限制
            offset: 偏移量

        Returns:
            视频列表
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM videos ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def get_video(self, video_id: int) -> Optional[dict]:
        """
        获取视频详情（包含关联工具）。

        Args:
            video_id: 视频 ID

        Returns:
            视频详情字典，如果不存在则返回 None
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
            row = cursor.fetchone()

            if not row:
                return None

            video = dict(row)

            # 获取关联的工具
            video["tools"] = self.get_video_tools(video_id)

            # 解析 analysis_result
            if video.get("analysis_result"):
                video["analysis_result"] = json.loads(video["analysis_result"])

            return video

    def get_tools(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        获取工具列表（分页）。

        Args:
            limit: 返回记录数限制
            offset: 偏移量

        Returns:
            工具列表
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tools ORDER BY name LIMIT ? OFFSET ?", (limit, offset))
            tools = []
            for row in cursor.fetchall():
                tool = dict(row)
                # 解析 JSON 字段
                for field in ["install_commands", "config_steps", "warnings", "alternatives"]:
                    if tool.get(field):
                        tool[field] = json.loads(tool[field])
                tools.append(tool)
            return tools

    def get_tool(self, tool_id: int) -> Optional[dict]:
        """
        获取工具详情（包含使用该工具的视频）。

        Args:
            tool_id: 工具 ID

        Returns:
            工具详情字典，如果不存在则返回 None
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,))
            row = cursor.fetchone()

            if not row:
                return None

            tool = dict(row)

            # 解析 JSON 字段
            for field in ["install_commands", "config_steps", "warnings", "alternatives"]:
                if tool.get(field):
                    tool[field] = json.loads(tool[field])

            # 获取使用此工具的视频
            cursor = conn.execute(
                """SELECT v.* FROM videos v
                   JOIN video_tools vt ON v.id = vt.video_id
                   WHERE vt.tool_id = ?""",
                (tool_id,),
            )
            tool["videos"] = [dict(row) for row in cursor.fetchall()]

            return tool

    def get_videos_count(self) -> int:
        """
        获取视频总数。

        Returns:
            视频总数
        """
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]

    def get_tools_count(self) -> int:
        """
        获取工具总数。

        Returns:
            工具总数
        """
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]

    def delete_video(self, video_id: int) -> bool:
        """
        删除视频（同时删除 video_tools 关联记录）。

        Args:
            video_id: 视频 ID

        Returns:
            是否删除成功
        """
        with self._connect() as conn:
            # 先删除关联记录
            conn.execute("DELETE FROM video_tools WHERE video_id = ?", (video_id,))
            # 再删除视频
            conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            return conn.total_changes > 0

    def update_video(self, video_id: int, **kwargs) -> bool:
        """
        更新视频信息。

        Args:
            video_id: 视频 ID
            **kwargs: 要更新的字段（title, theme, summary, transcription_text, analysis_result）

        Returns:
            是否更新成功
        """
        # 构建 UPDATE 语句
        allowed_fields = ["title", "theme", "summary", "transcription_text", "analysis_result", "platform"]
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                params.append(json.dumps(value, ensure_ascii=False) if key == "analysis_result" else value)

        if not updates:
            return False

        params.append(video_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE videos SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", params)
            return conn.total_changes > 0

    def delete_tool(self, tool_id: int) -> bool:
        """
        删除工具（同时删除 video_tools 关联记录）。

        Args:
            tool_id: 工具 ID

        Returns:
            是否删除成功
        """
        with self._connect() as conn:
            # 先删除关联记录
            conn.execute("DELETE FROM video_tools WHERE tool_id = ?", (tool_id,))
            # 再删除工具
            conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
            return conn.total_changes > 0

    def update_tool(self, tool_id: int, **kwargs) -> bool:
        """
        更新工具信息。

        Args:
            tool_id: 工具 ID
            **kwargs: 要更新的字段（name, category, purpose, install_commands, config_steps,
                      usage_examples, warnings, alternatives, is_paid, needs_credential）

        Returns:
            是否更新成功
        """
        # 构建 UPDATE 语句
        allowed_fields = [
            "name",
            "category",
            "purpose",
            "install_commands",
            "config_steps",
            "usage_examples",
            "warnings",
            "alternatives",
            "is_paid",
            "needs_credential",
        ]
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                if key in ["install_commands", "config_steps", "usage_examples", "alternatives"]:
                    params.append(json.dumps(value, ensure_ascii=False))
                else:
                    params.append(value)

        if not updates:
            return False

        params.append(tool_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE tools SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", params)
            return conn.total_changes > 0

    def close(self):
        """兼容接口：连接在每次操作后已自动关闭，无需手动调用。"""

    # =====================================================
    # Download Jobs Methods
    # =====================================================

    def create_download_job(self, job_id: str, url: str, url_type: Optional[str] = None,
                           author_nickname: Optional[str] = None,
                           author_sec_uid: Optional[str] = None) -> None:
        """创建下载任务。"""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO download_jobs
                   (job_id, url, url_type, author_nickname, author_sec_uid, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)""",
                (job_id, url, url_type, author_nickname, author_sec_uid)
            )

    def get_download_job(self, job_id: str) -> Optional[dict]:
        """获取下载任务。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM download_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_download_job_status(self, job_id: str, status: str,
                                  error_message: Optional[str] = None,
                                  started_at: Optional[str] = None,
                                  finished_at: Optional[str] = None) -> None:
        """更新下载任务状态。"""
        with self._connect() as conn:
            updates = ["status = ?"]
            params = [status]

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if started_at is not None:
                updates.append("started_at = ?")
                params.append(started_at)

            if finished_at is not None:
                updates.append("finished_at = ?")
                params.append(finished_at)

            params.append(job_id)
            conn.execute(
                f"UPDATE download_jobs SET {', '.join(updates)} WHERE job_id = ?",
                params
            )

    def update_download_job_counts(self, job_id: str, total_count: int = 0,
                                   success_count: int = 0, failed_count: int = 0,
                                   skipped_count: int = 0) -> None:
        """更新下载任务计数。"""
        with self._connect() as conn:
            conn.execute(
                """UPDATE download_jobs
                   SET total_count = ?, success_count = ?, failed_count = ?, skipped_count = ?
                   WHERE job_id = ?""",
                (total_count, success_count, failed_count, skipped_count, job_id)
            )

    def update_download_job_retry(self, job_id: str, retry_count: int,
                                  last_retry_at: str, last_retry_summary: Optional[dict] = None,
                                  retry_history: Optional[list] = None) -> None:
        """更新下载任务重试信息。"""
        with self._connect() as conn:
            conn.execute(
                """UPDATE download_jobs
                   SET retry_count = ?, last_retry_at = ?, last_retry_summary = ?, retry_history = ?
                   WHERE job_id = ?""",
                (
                    retry_count, last_retry_at,
                    json.dumps(last_retry_summary, ensure_ascii=False) if last_retry_summary else None,
                    json.dumps(retry_history, ensure_ascii=False) if retry_history else None,
                    job_id
                )
            )

    def list_download_jobs(self, status: Optional[str] = None, limit: int = 10) -> list[dict]:
        """列出下载任务。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if status:
                cursor = conn.execute(
                    "SELECT * FROM download_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM download_jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def delete_download_job(self, job_id: str) -> bool:
        """删除下载任务。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM download_jobs WHERE job_id = ?", (job_id,))
            return conn.total_changes > 0

    # =====================================================
    # Downloaded Videos Methods
    # =====================================================

    def add_downloaded_video(self, aweme_id: str, aweme_type: str,
                            title: Optional[str] = None,
                            author_id: Optional[str] = None,
                            author_name: Optional[str] = None,
                            author_sec_uid: Optional[str] = None,
                            create_time: Optional[str] = None,
                            file_path: Optional[str] = None,
                            file_size: Optional[int] = None,
                            metadata: Optional[dict] = None) -> int:
        """添加已下载视频记录。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO downloaded_videos
                   (aweme_id, aweme_type, title, author_id, author_name, author_sec_uid,
                    create_time, download_time, file_path, file_size, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)""",
                (
                    aweme_id, aweme_type, title, author_id, author_name, author_sec_uid,
                    create_time, file_path, file_size,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None
                )
            )
            return cursor.lastrowid

    def get_downloaded_video(self, aweme_id: str) -> Optional[dict]:
        """获取已下载视频记录。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM downloaded_videos WHERE aweme_id = ?", (aweme_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result.get("metadata"):
                    result["metadata"] = json.loads(result["metadata"])
                return result
            return None

    def list_downloaded_videos(self, limit: int = 50, offset: int = 0,
                               author_sec_uid: Optional[str] = None) -> list[dict]:
        """列出已下载视频。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if author_sec_uid:
                cursor = conn.execute(
                    "SELECT * FROM downloaded_videos WHERE author_sec_uid = ? ORDER BY download_time DESC LIMIT ? OFFSET ?",
                    (author_sec_uid, limit, offset)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM downloaded_videos ORDER BY download_time DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            return [dict(row) for row in cursor.fetchall()]

    def delete_downloaded_video(self, aweme_id: str) -> bool:
        """删除已下载视频记录。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM downloaded_videos WHERE aweme_id = ?", (aweme_id,))
            return conn.total_changes > 0

    # =====================================================
    # Transcript Jobs Methods
    # =====================================================

    def create_transcript_job(self, aweme_id: str, video_path: str,
                              model: str = 'gpt-4o-mini-transcribe',
                              transcript_dir: Optional[str] = None) -> int:
        """创建转录任务。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO transcript_jobs
                   (aweme_id, video_path, model, transcript_dir, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (aweme_id, video_path, model, transcript_dir)
            )
            return cursor.lastrowid

    def get_transcript_job(self, job_id: int) -> Optional[dict]:
        """获取转录任务。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM transcript_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_transcript_job_by_aweme(self, aweme_id: str, model: str = None) -> Optional[dict]:
        """根据视频ID获取转录任务。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if model:
                cursor = conn.execute(
                    "SELECT * FROM transcript_jobs WHERE aweme_id = ? AND model = ? ORDER BY created_at DESC LIMIT 1",
                    (aweme_id, model)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM transcript_jobs WHERE aweme_id = ? ORDER BY created_at DESC LIMIT 1",
                    (aweme_id,)
                )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_transcript_job_status(self, job_id: int, status: str,
                                     text_path: Optional[str] = None,
                                     json_path: Optional[str] = None,
                                     error_message: Optional[str] = None,
                                     skip_reason: Optional[str] = None) -> None:
        """更新转录任务状态。"""
        with self._connect() as conn:
            updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [status]

            if text_path is not None:
                updates.append("text_path = ?")
                params.append(text_path)

            if json_path is not None:
                updates.append("json_path = ?")
                params.append(json_path)

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if skip_reason is not None:
                updates.append("skip_reason = ?")
                params.append(skip_reason)

            params.append(job_id)
            conn.execute(
                f"UPDATE transcript_jobs SET {', '.join(updates)} WHERE id = ?",
                params
            )

    def list_transcript_jobs(self, status: Optional[str] = None, limit: int = 50) -> list[dict]:
        """列出转录任务。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if status:
                cursor = conn.execute(
                    "SELECT * FROM transcript_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM transcript_jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def delete_transcript_job(self, job_id: int) -> bool:
        """删除转录任务。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM transcript_jobs WHERE id = ?", (job_id,))
            return conn.total_changes > 0

    # =====================================================
    # Download History Methods
    # =====================================================

    def add_download_history(self, url: str, url_type: str,
                             total_count: Optional[int] = None,
                             success_count: Optional[int] = None,
                             config: Optional[dict] = None) -> int:
        """添加下载历史记录。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO download_history
                   (url, url_type, download_time, total_count, success_count, config)
                   VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)""",
                (
                    url, url_type, total_count, success_count,
                    json.dumps(config, ensure_ascii=False) if config else None
                )
            )
            return cursor.lastrowid

    def get_download_history(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """获取下载历史。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM download_history ORDER BY download_time DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete_download_history(self, history_id: int) -> bool:
        """删除下载历史记录。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM download_history WHERE id = ?", (history_id,))
            return conn.total_changes > 0

    # =====================================================
    # Search History Methods
    # =====================================================

    def add_search_history(self, query: str, user_id: Optional[str] = None,
                           search_type: str = 'all', result_count: int = 0) -> int:
        """添加搜索历史记录。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO search_history
                   (user_id, query, search_type, result_count)
                   VALUES (?, ?, ?, ?)""",
                (user_id, query, search_type, result_count)
            )
            return cursor.lastrowid

    def get_search_history(self, user_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        """获取搜索历史。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if user_id:
                cursor = conn.execute(
                    "SELECT * FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM search_history ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def clear_search_history(self, user_id: Optional[str] = None) -> int:
        """清除搜索历史。"""
        with self._connect() as conn:
            if user_id:
                conn.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
            else:
                conn.execute("DELETE FROM search_history")
            return conn.total_changes

    # =====================================================
    # User Preferences Methods
    # =====================================================

    def get_user_preferences(self, user_id: str) -> Optional[dict]:
        """获取用户偏好设置。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result.get("preferred_platforms"):
                    result["preferred_platforms"] = json.loads(result["preferred_platforms"])
                if result.get("preferred_categories"):
                    result["preferred_categories"] = json.loads(result["preferred_categories"])
                return result
            return None

    def set_user_preferences(self, user_id: str,
                             preferred_platforms: Optional[list] = None,
                             preferred_categories: Optional[list] = None,
                             language: Optional[str] = None,
                             theme: Optional[str] = None) -> None:
        """设置用户偏好。"""
        with self._connect() as conn:
            # 检查是否存在
            existing = conn.execute("SELECT id FROM user_preferences WHERE user_id = ?", (user_id,)).fetchone()

            if existing:
                # 更新
                updates = ["updated_at = CURRENT_TIMESTAMP"]
                params = []

                if preferred_platforms is not None:
                    updates.append("preferred_platforms = ?")
                    params.append(json.dumps(preferred_platforms, ensure_ascii=False))

                if preferred_categories is not None:
                    updates.append("preferred_categories = ?")
                    params.append(json.dumps(preferred_categories, ensure_ascii=False))

                if language is not None:
                    updates.append("language = ?")
                    params.append(language)

                if theme is not None:
                    updates.append("theme = ?")
                    params.append(theme)

                params.append(user_id)
                conn.execute(
                    f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = ?",
                    params
                )
            else:
                # 插入
                conn.execute(
                    """INSERT INTO user_preferences
                       (user_id, preferred_platforms, preferred_categories, language, theme)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        json.dumps(preferred_platforms, ensure_ascii=False) if preferred_platforms else None,
                        json.dumps(preferred_categories, ensure_ascii=False) if preferred_categories else None,
                        language or 'zh-CN',
                        theme or 'dark'
                    )
                )

    def delete_user_preferences(self, user_id: str) -> bool:
        """删除用户偏好设置。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
            return conn.total_changes > 0

    # =====================================================
    # System Config Methods
    # =====================================================

    def get_config(self, config_key: str) -> Optional[str]:
        """获取配置值。"""
        with self._connect() as conn:
            cursor = conn.execute("SELECT config_value, config_type FROM system_config WHERE config_key = ?", (config_key,))
            row = cursor.fetchone()
            if not row:
                return None

            value, config_type = row

            # 根据类型转换
            if config_type == 'integer':
                return int(value)
            elif config_type == 'float':
                return float(value)
            elif config_type == 'boolean':
                return value.lower() == 'true'
            elif config_type == 'json':
                return json.loads(value)
            else:
                return value

    def set_config(self, config_key: str, config_value: any,
                   config_type: str = 'string', description: Optional[str] = None) -> None:
        """设置配置值。"""
        with self._connect() as conn:
            # 转换值为字符串
            if config_type == 'json':
                str_value = json.dumps(config_value, ensure_ascii=False)
            else:
                str_value = str(config_value)

            # 检查是否存在
            existing = conn.execute("SELECT config_key FROM system_config WHERE config_key = ?", (config_key,)).fetchone()

            if existing:
                # 更新
                updates = ["config_value = ?", "config_type = ?", "updated_at = CURRENT_TIMESTAMP"]
                params = [str_value, config_type]

                if description is not None:
                    updates.append("description = ?")
                    params.append(description)

                params.append(config_key)
                conn.execute(
                    f"UPDATE system_config SET {', '.join(updates)} WHERE config_key = ?",
                    params
                )
            else:
                # 插入
                conn.execute(
                    """INSERT INTO system_config (config_key, config_value, config_type, description)
                       VALUES (?, ?, ?, ?)""",
                    (config_key, str_value, config_type, description)
                )

    def delete_config(self, config_key: str) -> bool:
        """删除配置。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM system_config WHERE config_key = ?", (config_key,))
            return conn.total_changes > 0

    def list_configs(self) -> list[dict]:
        """列出所有配置。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM system_config ORDER BY config_key")
            return [dict(row) for row in cursor.fetchall()]

    def init_default_config(self) -> None:
        """初始化默认配置数据。"""
        defaults = [
            ('db_version', '1.0.0', 'string', '数据库版本'),
            ('max_concurrent_downloads', '3', 'integer', '最大并发下载数'),
            ('max_concurrent_transcripts', '2', 'integer', '最大并发转录数'),
            ('default_platform', 'douyin', 'string', '默认平台'),
            ('enable_notifications', 'true', 'boolean', '启用通知'),
            ('storage_path', './data/videos', 'string', '存储路径'),
        ]

        for key, value, config_type, description in defaults:
            try:
                self.set_config(key, value, config_type, description)
            except Exception:
                # 配置已存在，跳过
                pass

    # =====================================================
    # User Management Methods
    # =====================================================

    def create_user(self, username: str, email: str, password_hash: str, role: str = 'user') -> int:
        """创建新用户。

        Args:
            username: 用户名（唯一）
            email: 邮箱（唯一）
            password_hash: 加密后的密码
            role: 角色（'admin' 或 'user'）

        Returns:
            新用户的 ID

        Raises:
            sqlite3.IntegrityError: 用户名或邮箱已存在
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO users (username, email, password_hash, role)
                   VALUES (?, ?, ?, ?)""",
                (username, email, password_hash, role)
            )
            return cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """根据用户名获取用户。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """根据邮箱获取用户。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """根据用户 ID 获取用户。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_user_password(self, user_id: int, password_hash: str) -> bool:
        """更新用户密码。"""
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (password_hash, user_id)
            )
            return conn.total_changes > 0

    def update_last_login(self, user_id: int) -> bool:
        """更新用户最后登录时间。"""
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET last_login_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,)
            )
            return conn.total_changes > 0

    def set_user_active(self, user_id: int, is_active: bool) -> bool:
        """激活或停用用户。"""
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (1 if is_active else 0, user_id)
            )
            return conn.total_changes > 0

    def list_users(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """列出用户（分页）。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, username, email, role, created_at, last_login_at, is_active FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_user(self, user_id: int, **kwargs) -> bool:
        """更新用户信息。

        Args:
            user_id: 用户 ID
            **kwargs: 可更新的字段（username, email, role, is_active）

        Returns:
            是否更新成功
        """
        allowed_fields = ['username', 'email', 'role', 'is_active']
        updates = []
        params = []

        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                params.append(value)

        if not updates:
            return False

        params.append(user_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                params
            )
            return conn.total_changes > 0

    def delete_user(self, user_id: int) -> bool:
        """删除用户（同时清除 user_preferences 中的关联）。"""
        with self._connect() as conn:
            # 清除 user_preferences 中的 user_id_int 关联
            conn.execute("UPDATE user_preferences SET user_id_int = NULL WHERE user_id_int = ?", (user_id,))
            # 删除用户
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return conn.total_changes > 0

    def get_user_count(self) -> int:
        """获取用户总数。"""
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
