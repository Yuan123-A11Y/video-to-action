"""
MySQL 知识库模块 - 使用 MySQL 替代 SQLite。

基于 MySQL 存储分析结果，提供与 KnowledgeBase (SQLite) 完全相同的接口。
注意：此类只处理 MySQL，不支持降级到 SQLite。
      降级逻辑由 `knowledge_base_factory.create_knowledge_base()` 统一处理。
"""

import json
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import pymysql
from dotenv import load_dotenv

from video_to_action.base_knowledge_base import BaseKnowledgeBase

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class MySQLKnowledgeBase(BaseKnowledgeBase):
    """视频知识库，基于 MySQL 存储分析结果。

    注意：此类只处理 MySQL，不支持降级到 SQLite。
         降级逻辑由工厂函数 `create_knowledge_base()` 统一处理。

    Raises:
        pymysql.Error: 当 MySQL 连接失败时抛出
    """

    def __init__(self, **kwargs):
        """初始化 MySQL 知识库。

        Args:
            **kwargs: MySQL 连接参数
                host: MySQL 主机地址（默认从 MYSQL_HOST 环境变量读取， fallback 到 localhost）
                port: MySQL 端口（默认 3306）
                user: MySQL 用户名（默认 root）
                password: MySQL 密码（默认空字符串）
                database: MySQL 数据库名（默认 video_to_action）
        """
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
        self._init_tables()
        logger.info(f"✅ MySQL 数据库连接成功: {self.mysql_config['host']}:{self.mysql_config['port']}")

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

    def _init_tables(self):
        """初始化 MySQL 表结构（与 database/schema.sql 完全一致）。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 创建 videos 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    url VARCHAR(500) NOT NULL,
                    url_hash CHAR(64) GENERATED ALWAYS AS (SHA2(url, 256)) STORED UNIQUE,
                    platform ENUM('douyin', 'bilibili', 'youtube', 'unknown') NOT NULL DEFAULT 'unknown',
                    video_id VARCHAR(255),
                    title VARCHAR(500),
                    author_name VARCHAR(255),
                    author_id VARCHAR(255),
                    duration INT UNSIGNED,
                    theme VARCHAR(200),
                    summary TEXT,
                    transcription_text LONGTEXT,
                    analysis_result JSON,
                    file_path VARCHAR(500),
                    file_size BIGINT UNSIGNED,
                    status ENUM('pending', 'downloading', 'downloaded', 'processing', 'completed', 'failed') DEFAULT 'pending',
                    error_message TEXT,
                    view_count INT UNSIGNED DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    downloaded_at DATETIME,
                    INDEX idx_platform (platform),
                    INDEX idx_video_id (video_id),
                    INDEX idx_author_id (author_id),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at),
                    INDEX idx_theme (theme(50)),
                    FULLTEXT INDEX ft_title (title),
                    FULLTEXT INDEX ft_transcription (transcription_text(1000))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建 tools 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    name_normalized VARCHAR(255) GENERATED ALWAYS AS (LOWER(name)) STORED UNIQUE,
                    category VARCHAR(100),
                    purpose TEXT,
                    description TEXT,
                    install_commands JSON,
                    config_steps JSON,
                    usage_examples JSON,
                    warnings TEXT,
                    alternatives JSON,
                    homepage_url VARCHAR(500),
                    documentation_url VARCHAR(500),
                    is_paid BOOLEAN DEFAULT FALSE,
                    needs_credential BOOLEAN DEFAULT FALSE,
                    license_type VARCHAR(100),
                    programming_language VARCHAR(100),
                    github_url VARCHAR(500),
                    version VARCHAR(100),
                    tags JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_category (category),
                    INDEX idx_is_paid (is_paid),
                    FULLTEXT INDEX ft_name (name),
                    FULLTEXT INDEX ft_purpose (purpose(500))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建 video_tools 关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video_tools (
                    video_id INT UNSIGNED NOT NULL,
                    tool_id INT UNSIGNED NOT NULL,
                    relevance_score DECIMAL(3,2) DEFAULT 0.50,
                    mention_count INT UNSIGNED DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (video_id, tool_id),
                    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                    FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE,
                    INDEX idx_tool_id (tool_id),
                    INDEX idx_relevance (relevance_score)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建 download_jobs 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS download_jobs (
                    job_id VARCHAR(64) PRIMARY KEY,
                    url TEXT NOT NULL,
                    url_type VARCHAR(50),
                    status ENUM('pending', 'running', 'success', 'failed', 'cancelled') NOT NULL DEFAULT 'pending',
                    created_at DATETIME NOT NULL,
                    started_at DATETIME,
                    finished_at DATETIME,
                    total_count INT UNSIGNED DEFAULT 0,
                    success_count INT UNSIGNED DEFAULT 0,
                    failed_count INT UNSIGNED DEFAULT 0,
                    skipped_count INT UNSIGNED DEFAULT 0,
                    error_message TEXT,
                    author_nickname VARCHAR(255),
                    author_sec_uid VARCHAR(255),
                    retry_count INT UNSIGNED DEFAULT 0,
                    last_retry_at DATETIME,
                    last_retry_summary JSON,
                    retry_history JSON,
                    overrides JSON,
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at),
                    INDEX idx_author_sec_uid (author_sec_uid(50))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建 downloaded_videos 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloaded_videos (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    aweme_id VARCHAR(255) NOT NULL,
                    aweme_id_hash CHAR(64) GENERATED ALWAYS AS (SHA2(aweme_id, 256)) STORED UNIQUE,
                    aweme_type VARCHAR(50) NOT NULL,
                    title VARCHAR(500),
                    author_id VARCHAR(255),
                    author_name VARCHAR(255),
                    author_sec_uid VARCHAR(255),
                    create_time DATETIME,
                    download_time DATETIME NOT NULL,
                    file_path VARCHAR(500),
                    file_size BIGINT UNSIGNED,
                    metadata JSON,
                    INDEX idx_aweme_id (aweme_id),
                    INDEX idx_author_id (author_id),
                    INDEX idx_author_sec_uid (author_sec_uid(50)),
                    INDEX idx_download_time (download_time),
                    INDEX idx_create_time (create_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建 transcript_jobs 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcript_jobs (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    aweme_id VARCHAR(255) NOT NULL,
                    video_path VARCHAR(500) NOT NULL,
                    transcript_dir VARCHAR(500),
                    text_path VARCHAR(500),
                    json_path VARCHAR(500),
                    model VARCHAR(100) NOT NULL DEFAULT 'gpt-4o-mini-transcribe',
                    status ENUM('pending', 'processing', 'completed', 'failed', 'skipped') NOT NULL,
                    skip_reason TEXT,
                    error_message TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE KEY uk_aweme_video_model (aweme_id, video_path(255), model),
                    INDEX idx_aweme_id (aweme_id),
                    INDEX idx_status (status),
                    INDEX idx_model (model)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建 download_history 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS download_history (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    url TEXT NOT NULL,
                    url_type VARCHAR(50) NOT NULL,
                    download_time DATETIME NOT NULL,
                    total_count INT UNSIGNED,
                    success_count INT UNSIGNED,
                    config JSON,
                    INDEX idx_download_time (download_time),
                    INDEX idx_url_type (url_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建 search_history 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255),
                    query TEXT NOT NULL,
                    search_type ENUM('video', 'tool', 'all') DEFAULT 'all',
                    result_count INT UNSIGNED DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_search_type (search_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建 user_preferences 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    user_id_hash CHAR(64) GENERATED ALWAYS AS (SHA2(user_id, 256)) STORED UNIQUE,
                    preferred_platforms JSON,
                    preferred_categories JSON,
                    language VARCHAR(10) DEFAULT 'zh-CN',
                    theme VARCHAR(20) DEFAULT 'dark',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 迁移：为 user_preferences 表添加 user_id_int 字段（关联 users.id）
            self._migrate_user_preferences_user_id_int(cursor)

            # 创建 users 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'user') DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_login_at DATETIME NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    INDEX idx_username (username),
                    INDEX idx_email (email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建 system_config 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    config_key VARCHAR(255) PRIMARY KEY,
                    config_value TEXT,
                    config_type ENUM('string', 'integer', 'float', 'boolean', 'json') DEFAULT 'string',
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建视图
            cursor.execute("DROP VIEW IF EXISTS v_video_stats")
            cursor.execute("""
                CREATE VIEW v_video_stats AS
                SELECT
                    platform,
                    COUNT(*) as total_videos,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_videos,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_videos,
                    AVG(file_size) as avg_file_size,
                    SUM(file_size) as total_storage
                FROM videos
                GROUP BY platform
            """)

            cursor.execute("DROP VIEW IF EXISTS v_tool_stats")
            cursor.execute("""
                CREATE VIEW v_tool_stats AS
                SELECT
                    t.id,
                    t.name,
                    t.category,
                    COUNT(vt.video_id) as referenced_count,
                    AVG(vt.relevance_score) as avg_relevance
                FROM tools t
                LEFT JOIN video_tools vt ON t.id = vt.tool_id
                GROUP BY t.id, t.name, t.category
            """)

            # 初始化默认配置
            self._init_default_config(cursor)

            cursor.close()

    def _init_default_config(self, cursor):
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
                cursor.execute(
                    """INSERT INTO system_config (config_key, config_value, config_type, description)
                       VALUES (%s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)""",
                    (key, value, config_type, description)
                )
            except Exception:
                # 配置已存在，跳过
                pass

    def _migrate_user_preferences_user_id_int(self, cursor):
        """迁移：为 user_preferences 表添加 user_id_int 字段。"""
        # 检查列是否存在
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'user_preferences'
              AND COLUMN_NAME = 'user_id_int'
        """, (self.mysql_config['database'],))

        if not cursor.fetchone():
            # 列不存在，先检查 users 表是否存在（auth 表可能未创建）
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'
            """, (self.mysql_config['database'],))
            row = cursor.fetchone()
            users_exists = (row and list(row.values())[0]) > 0 if row else False

            if users_exists:
                # users 表存在，可以加外键约束
                cursor.execute("""
                    ALTER TABLE user_preferences
                    ADD COLUMN user_id_int INT UNSIGNED,
                    ADD CONSTRAINT fk_user_preferences_user_id_int
                    FOREIGN KEY (user_id_int) REFERENCES users(id) ON DELETE SET NULL
                """)
                logger.info("✅ 已为 user_preferences 表添加 user_id_int 字段（含外键）")
            else:
                # users 表不存在（auth 未在 MySQL 建表），只加列不加外键
                try:
                    cursor.execute("""
                        ALTER TABLE user_preferences
                        ADD COLUMN user_id_int INT UNSIGNED
                    """)
                    logger.info("✅ 已为 user_preferences 表添加 user_id_int 字段（无外键，users 表不存在）")
                except Exception as e:
                    logger.warning(f"⚠️ 添加 user_id_int 失败（可忽略）: {e}")

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
        import hashlib
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"🔍 add_video_analysis called, url={url[:50]}...")

        # 计算 url_hash（与 MySQL 原 generated column 逻辑一致）
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 插入视频记录（使用 ON DUPLICATE KEY UPDATE 处理重复）
            try:
                logger.info(f"🔍 INSERT INTO videos, url_hash={url_hash[:16]}...")
                cursor.execute(
                    """INSERT INTO videos
                       (url, url_hash, platform, title, theme, summary, transcription_text, analysis_result)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                       title = VALUES(title),
                       theme = VALUES(theme),
                       summary = VALUES(summary),
                       transcription_text = VALUES(transcription_text),
                       analysis_result = VALUES(analysis_result),
                       updated_at = CURRENT_TIMESTAMP""",
                    (
                        url,
                        url_hash,
                        platform,
                        title,
                        theme,
                        summary,
                        transcription_text,
                        json.dumps(analysis_result, ensure_ascii=False),
                    ),
                )
                logger.info(f"✅ videos INSERT ok, lastrowid={cursor.lastrowid}")
            except Exception as e:
                logger.error(f"❌ videos INSERT failed: {e}")
                raise

            # 获取 video_id
            if cursor.lastrowid > 0:
                video_id = cursor.lastrowid
            else:
                # 记录已存在，用 url 查找
                cursor.execute("SELECT id FROM videos WHERE url = %s", (url,))
                row = cursor.fetchone()
                video_id = row["id"] if row else 0

            logger.info(f"✅ video_id={video_id}")

            # 插入工具记录
            tools = analysis_result.get("tools", [])
            for tool in tools:
                tool_id = self._add_or_get_tool(conn, tool)
                try:
                    logger.info(f"🔍 INSERT INTO video_tools ({video_id}, {tool_id})")
                    cursor.execute(
                        """INSERT IGNORE INTO video_tools (video_id, tool_id) VALUES (%s, %s)""",
                        (video_id, tool_id),
                    )
                    logger.info("✅ video_tools INSERT ok")
                except Exception as e:
                    logger.error(f"❌ video_tools INSERT failed: {e}")
                    raise

            cursor.close()
            return video_id

    def _add_or_get_tool(self, conn, tool: dict) -> int:
        """添加工具记录或获取已有工具ID。

        tool dict 格式（来自 LLM 分析结果）：
        {
            "name": str,
            "purpose": str,
            "links": list[str],         # -> homepage_url / alternatives
            "install_commands": list[str],
            "config_steps": list[str],
            "run_commands": list[str],  # -> usage_examples
            "warnings": list[str],       # -> 合并为字符串
        }
        """
        cursor = conn.cursor()
        # 用 name_normalized（小写标准化）查找，与 DB 索引一致
        try:
            logger.info(f"🔍 _add_or_get_tool: tool_name={tool.get('name', '?')}")
            cursor.execute("SELECT id FROM tools WHERE name_normalized = LOWER(%s)", (tool["name"],))
        except Exception as e:
            logger.error(f"❌ SELECT tools failed: {e}, tool={tool.get('name', '?')}")
            raise
        row = cursor.fetchone()

        if row:
            cursor.close()
            return row["id"]

        # 计算 name_normalized（与 MySQL 原 generated column 逻辑一致）
        name_normalized = tool["name"].lower()

        # 正确处理 LLM 返回的各种字段类型
        def _join(obj):
            """把 list 转成换行分隔的字符串；其他原样返回。"""
            if isinstance(obj, list):
                return "\n".join(str(x) for x in obj)
            return obj if obj is not None else ""

        try:
            logger.info(f"🔍 INSERT INTO tools: name={tool['name']}, name_normalized={name_normalized}")
            cursor.execute(
                """INSERT INTO tools
                   (name, name_normalized, category, purpose, description,
                    install_commands, config_steps, usage_examples,
                    warnings, alternatives, homepage_url,
                    is_paid, needs_credential)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    tool["name"],
                    name_normalized,
                    tool.get("category", ""),
                    tool.get("purpose", ""),
                    tool.get("description", ""),
                    json.dumps(tool.get("install_commands", []), ensure_ascii=False),
                    json.dumps(tool.get("config_steps", []), ensure_ascii=False),
                    json.dumps(tool.get("run_commands", tool.get("usage_examples", [])), ensure_ascii=False),
                    _join(tool.get("warnings", "")),
                    json.dumps(tool.get("links", tool.get("alternatives", [])), ensure_ascii=False),
                    tool.get("homepage_url", ""),
                    tool.get("is_paid", False),
                    tool.get("needs_credential", False),
                ),
            )
            logger.info(f"✅ tools INSERT ok, tool_id={cursor.lastrowid}")
        except Exception as e:
            logger.error(f"❌ tools INSERT failed: {e}, tool={tool}")
            raise
        tool_id = cursor.lastrowid
        cursor.close()
        return tool_id

    def search_videos(self, query: str, limit: int = 10) -> list:
        """搜索视频（基于 LIKE 模糊匹配）。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query}%"
            cursor.execute(
                """SELECT * FROM videos
                   WHERE title LIKE %s OR theme LIKE %s OR summary LIKE %s
                   ORDER BY created_at DESC LIMIT %s""",
                (pattern, pattern, pattern, limit),
            )
            results = cursor.fetchall()
            cursor.close()
            return results

    def search_tools(self, query: str, limit: int = 10) -> list:
        """搜索工具（基于 LIKE 模糊匹配）。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query}%"
            cursor.execute(
                """SELECT * FROM tools
                   WHERE name LIKE %s OR purpose LIKE %s
                   LIMIT %s""",
                (pattern, pattern, limit),
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
        import hashlib

        url_hash = hashlib.sha256(url.encode()).hexdigest()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos WHERE url_hash = %s", (url_hash,))
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT t.* FROM tools t
                   JOIN video_tools vt ON t.id = vt.tool_id
                   WHERE vt.video_id = %s""",
                (video_id,),
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos ORDER BY created_at DESC LIMIT %s OFFSET %s", (limit, offset))
            results = cursor.fetchall()
            cursor.close()
            return results

    def get_video(self, video_id: int) -> Optional[dict]:
        """获取视频详情（包含关联工具）。"""
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
                (video_id,),
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tools ORDER BY name LIMIT %s OFFSET %s", (limit, offset))
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
                (tool_id,),
            )
            row["videos"] = cursor.fetchall()

            cursor.close()
            return row

    def get_videos_count(self) -> int:
        """获取视频总数。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM videos")
            count = cursor.fetchone()["count"]
            cursor.close()
            return count

    def get_tools_with_videos(self) -> list[dict]:
        """获取所有工具及其关联视频（用于导出操作手册）。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 获取所有工具（按名称排序）
            cursor.execute("SELECT * FROM tools ORDER BY name")
            tools = cursor.fetchall()

            # 获取所有工具-视频关联关系
            cursor.execute("""SELECT vt.tool_id, v.id, v.platform, v.title, v.theme
                   FROM video_tools vt
                   JOIN videos v ON v.id = vt.video_id""")
            rows = cursor.fetchall()
            cursor.close()

            tool_videos_map = {}
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

    def get_tools_count(self) -> int:
        """获取工具总数。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM tools")
            count = cursor.fetchone()["count"]
            cursor.close()
            return count

    def delete_video(self, video_id: int) -> bool:
        """删除视频（同时删除 video_tools 关联记录）。"""
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
                f"UPDATE videos SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s", params
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated

    def delete_tool(self, tool_id: int) -> bool:
        """删除工具（同时删除 video_tools 关联记录）。"""
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
                f"UPDATE tools SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s", params
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated

    def close(self):
        """兼容接口：连接在每次操作后已自动关闭，无需手动调用。"""

    # =====================================================
    # Download Jobs Methods
    # =====================================================

    def create_download_job(self, job_id: str, url: str, url_type: Optional[str] = None,
                           author_nickname: Optional[str] = None,
                           author_sec_uid: Optional[str] = None) -> None:
        """创建下载任务。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO download_jobs
                   (job_id, url, url_type, author_nickname, author_sec_uid, status, created_at)
                   VALUES (%s, %s, %s, %s, %s, 'pending', NOW())""",
                (job_id, url, url_type, author_nickname, author_sec_uid)
            )
            cursor.close()

    def get_download_job(self, job_id: str) -> Optional[dict]:
        """获取下载任务。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM download_jobs WHERE job_id = %s", (job_id,))
            row = cursor.fetchone()
            cursor.close()
            return row

    def update_download_job_status(self, job_id: str, status: str,
                                  error_message: Optional[str] = None,
                                  started_at: Optional[str] = None,
                                  finished_at: Optional[str] = None) -> None:
        """更新下载任务状态。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = ["status = %s"]
            params = [status]

            if error_message is not None:
                updates.append("error_message = %s")
                params.append(error_message)

            if started_at is not None:
                updates.append("started_at = %s")
                params.append(started_at)

            if finished_at is not None:
                updates.append("finished_at = %s")
                params.append(finished_at)

            params.append(job_id)
            cursor.execute(
                f"UPDATE download_jobs SET {', '.join(updates)} WHERE job_id = %s",
                params
            )
            cursor.close()

    def update_download_job_counts(self, job_id: str, total_count: int = 0,
                                   success_count: int = 0, failed_count: int = 0,
                                   skipped_count: int = 0) -> None:
        """更新下载任务计数。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE download_jobs
                   SET total_count = %s, success_count = %s, failed_count = %s, skipped_count = %s
                   WHERE job_id = %s""",
                (total_count, success_count, failed_count, skipped_count, job_id)
            )
            cursor.close()

    def update_download_job_retry(self, job_id: str, retry_count: int,
                                  last_retry_at: str, last_retry_summary: Optional[dict] = None,
                                  retry_history: Optional[list] = None) -> None:
        """更新下载任务重试信息。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE download_jobs
                   SET retry_count = %s, last_retry_at = %s, last_retry_summary = %s, retry_history = %s
                   WHERE job_id = %s""",
                (
                    retry_count, last_retry_at,
                    json.dumps(last_retry_summary, ensure_ascii=False) if last_retry_summary else None,
                    json.dumps(retry_history, ensure_ascii=False) if retry_history else None,
                    job_id
                )
            )
            cursor.close()

    def list_download_jobs(self, status: Optional[str] = None, limit: int = 10) -> list:
        """列出下载任务。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM download_jobs WHERE status = %s ORDER BY created_at DESC LIMIT %s",
                    (status, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM download_jobs ORDER BY created_at DESC LIMIT %s",
                    (limit,)
                )
            results = cursor.fetchall()
            cursor.close()
            return results

    def delete_download_job(self, job_id: str) -> bool:
        """删除下载任务。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM download_jobs WHERE job_id = %s", (job_id,))
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted

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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO downloaded_videos
                   (aweme_id, aweme_type, title, author_id, author_name, author_sec_uid,
                    create_time, download_time, file_path, file_size, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   title = VALUES(title),
                   author_id = VALUES(author_id),
                   author_name = VALUES(author_name),
                   file_path = VALUES(file_path),
                   file_size = VALUES(file_size),
                   metadata = VALUES(metadata)""",
                (
                    aweme_id, aweme_type, title, author_id, author_name, author_sec_uid,
                    create_time, file_path, file_size,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None
                )
            )
            lastrowid = cursor.lastrowid
            cursor.close()
            return lastrowid

    def get_downloaded_video(self, aweme_id: str) -> Optional[dict]:
        """获取已下载视频记录。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM downloaded_videos WHERE aweme_id = %s", (aweme_id,))
            row = cursor.fetchone()
            if row and row.get("metadata"):
                try:
                    row["metadata"] = json.loads(row["metadata"])
                except:
                    pass
            cursor.close()
            return row

    def list_downloaded_videos(self, limit: int = 50, offset: int = 0,
                               author_sec_uid: Optional[str] = None) -> list:
        """列出已下载视频。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if author_sec_uid:
                cursor.execute(
                    "SELECT * FROM downloaded_videos WHERE author_sec_uid = %s ORDER BY download_time DESC LIMIT %s OFFSET %s",
                    (author_sec_uid, limit, offset)
                )
            else:
                cursor.execute(
                    "SELECT * FROM downloaded_videos ORDER BY download_time DESC LIMIT %s OFFSET %s",
                    (limit, offset)
                )
            results = cursor.fetchall()
            cursor.close()
            return results

    def delete_downloaded_video(self, aweme_id: str) -> bool:
        """删除已下载视频记录。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloaded_videos WHERE aweme_id = %s", (aweme_id,))
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted

    # =====================================================
    # Transcript Jobs Methods
    # =====================================================

    def create_transcript_job(self, aweme_id: str, video_path: str,
                              model: str = 'gpt-4o-mini-transcribe',
                              transcript_dir: Optional[str] = None) -> int:
        """创建转录任务。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT IGNORE INTO transcript_jobs
                   (aweme_id, video_path, model, transcript_dir, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, 'pending', NOW(), NOW())""",
                (aweme_id, video_path, model, transcript_dir)
            )
            lastrowid = cursor.lastrowid
            cursor.close()
            return lastrowid

    def get_transcript_job(self, job_id: int) -> Optional[dict]:
        """获取转录任务。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transcript_jobs WHERE id = %s", (job_id,))
            row = cursor.fetchone()
            cursor.close()
            return row

    def get_transcript_job_by_aweme(self, aweme_id: str, model: str = None) -> Optional[dict]:
        """根据视频ID获取转录任务。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if model:
                cursor.execute(
                    "SELECT * FROM transcript_jobs WHERE aweme_id = %s AND model = %s ORDER BY created_at DESC LIMIT 1",
                    (aweme_id, model)
                )
            else:
                cursor.execute(
                    "SELECT * FROM transcript_jobs WHERE aweme_id = %s ORDER BY created_at DESC LIMIT 1",
                    (aweme_id,)
                )
            row = cursor.fetchone()
            cursor.close()
            return row

    def update_transcript_job_status(self, job_id: int, status: str,
                                     text_path: Optional[str] = None,
                                     json_path: Optional[str] = None,
                                     error_message: Optional[str] = None,
                                     skip_reason: Optional[str] = None) -> None:
        """更新转录任务状态。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = ["status = %s", "updated_at = NOW()"]
            params = [status]

            if text_path is not None:
                updates.append("text_path = %s")
                params.append(text_path)

            if json_path is not None:
                updates.append("json_path = %s")
                params.append(json_path)

            if error_message is not None:
                updates.append("error_message = %s")
                params.append(error_message)

            if skip_reason is not None:
                updates.append("skip_reason = %s")
                params.append(skip_reason)

            params.append(job_id)
            cursor.execute(
                f"UPDATE transcript_jobs SET {', '.join(updates)} WHERE id = %s",
                params
            )
            cursor.close()

    def list_transcript_jobs(self, status: Optional[str] = None, limit: int = 50) -> list:
        """列出转录任务。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM transcript_jobs WHERE status = %s ORDER BY created_at DESC LIMIT %s",
                    (status, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM transcript_jobs ORDER BY created_at DESC LIMIT %s",
                    (limit,)
                )
            results = cursor.fetchall()
            cursor.close()
            return results

    def delete_transcript_job(self, job_id: int) -> bool:
        """删除转录任务。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transcript_jobs WHERE id = %s", (job_id,))
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted

    # =====================================================
    # Download History Methods
    # =====================================================

    def add_download_history(self, url: str, url_type: str,
                             total_count: Optional[int] = None,
                             success_count: Optional[int] = None,
                             config: Optional[dict] = None) -> int:
        """添加下载历史记录。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO download_history
                   (url, url_type, download_time, total_count, success_count, config)
                   VALUES (%s, %s, NOW(), %s, %s, %s)""",
                (
                    url, url_type, total_count, success_count,
                    json.dumps(config, ensure_ascii=False) if config else None
                )
            )
            lastrowid = cursor.lastrowid
            cursor.close()
            return lastrowid

    def get_download_history(self, limit: int = 50, offset: int = 0) -> list:
        """获取下载历史。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM download_history ORDER BY download_time DESC LIMIT %s OFFSET %s",
                (limit, offset)
            )
            results = cursor.fetchall()
            cursor.close()
            return results

    def delete_download_history(self, history_id: int) -> bool:
        """删除下载历史记录。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM download_history WHERE id = %s", (history_id,))
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted

    # =====================================================
    # Search History Methods
    # =====================================================

    def add_search_history(self, query: str, user_id: Optional[str] = None,
                           search_type: str = 'all', result_count: int = 0) -> int:
        """添加搜索历史记录。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO search_history
                   (user_id, query, search_type, result_count)
                   VALUES (%s, %s, %s, %s)""",
                (user_id, query, search_type, result_count)
            )
            lastrowid = cursor.lastrowid
            cursor.close()
            return lastrowid

    def get_search_history(self, user_id: Optional[str] = None, limit: int = 50) -> list:
        """获取搜索历史。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT * FROM search_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                    (user_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM search_history ORDER BY created_at DESC LIMIT %s",
                    (limit,)
                )
            results = cursor.fetchall()
            cursor.close()
            return results

    def clear_search_history(self, user_id: Optional[str] = None) -> int:
        """清除搜索历史。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("DELETE FROM search_history WHERE user_id = %s", (user_id,))
            else:
                cursor.execute("DELETE FROM search_history")
            deleted = cursor.rowcount
            cursor.close()
            return deleted

    # =====================================================
    # User Preferences Methods
    # =====================================================

    def get_user_preferences(self, user_id: str) -> Optional[dict]:
        """获取用户偏好设置。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
            if row:
                if row.get("preferred_platforms"):
                    try:
                        row["preferred_platforms"] = json.loads(row["preferred_platforms"])
                    except:
                        pass
                if row.get("preferred_categories"):
                    try:
                        row["preferred_categories"] = json.loads(row["preferred_categories"])
                    except:
                        pass
            cursor.close()
            return row

    def set_user_preferences(self, user_id: str,
                             preferred_platforms: Optional[list] = None,
                             preferred_categories: Optional[list] = None,
                             language: Optional[str] = None,
                             theme: Optional[str] = None) -> None:
        """设置用户偏好。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 检查是否存在
            cursor.execute("SELECT id FROM user_preferences WHERE user_id = %s", (user_id,))
            existing = cursor.fetchone()

            if existing:
                # 更新
                updates = ["updated_at = NOW()"]
                params = []

                if preferred_platforms is not None:
                    updates.append("preferred_platforms = %s")
                    params.append(json.dumps(preferred_platforms, ensure_ascii=False))

                if preferred_categories is not None:
                    updates.append("preferred_categories = %s")
                    params.append(json.dumps(preferred_categories, ensure_ascii=False))

                if language is not None:
                    updates.append("language = %s")
                    params.append(language)

                if theme is not None:
                    updates.append("theme = %s")
                    params.append(theme)

                params.append(user_id)
                cursor.execute(
                    f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = %s",
                    params
                )
            else:
                # 插入
                cursor.execute(
                    """INSERT INTO user_preferences
                       (user_id, preferred_platforms, preferred_categories, language, theme)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        user_id,
                        json.dumps(preferred_platforms, ensure_ascii=False) if preferred_platforms else None,
                        json.dumps(preferred_categories, ensure_ascii=False) if preferred_categories else None,
                        language or 'zh-CN',
                        theme or 'dark'
                    )
                )
            cursor.close()

    def delete_user_preferences(self, user_id: str) -> bool:
        """删除用户偏好设置。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_preferences WHERE user_id = %s", (user_id,))
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted

    # =====================================================
    # System Config Methods
    # =====================================================

    def get_config(self, config_key: str) -> Optional[any]:
        """获取配置值。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT config_value, config_type FROM system_config WHERE config_key = %s", (config_key,))
            row = cursor.fetchone()
            cursor.close()

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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 转换值为字符串
            if config_type == 'json':
                str_value = json.dumps(config_value, ensure_ascii=False)
            else:
                str_value = str(config_value)

            # 检查是否存在
            cursor.execute("SELECT config_key FROM system_config WHERE config_key = %s", (config_key,))
            existing = cursor.fetchone()

            if existing:
                # 更新
                updates = ["config_value = %s", "config_type = %s", "updated_at = NOW()"]
                params = [str_value, config_type]

                if description is not None:
                    updates.append("description = %s")
                    params.append(description)

                params.append(config_key)
                cursor.execute(
                    f"UPDATE system_config SET {', '.join(updates)} WHERE config_key = %s",
                    params
                )
            else:
                # 插入
                cursor.execute(
                    """INSERT INTO system_config (config_key, config_value, config_type, description)
                       VALUES (%s, %s, %s, %s)""",
                    (config_key, str_value, config_type, description)
                )
            cursor.close()

    def delete_config(self, config_key: str) -> bool:
        """删除配置。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_config WHERE config_key = %s", (config_key,))
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted

    def list_configs(self) -> list:
        """列出所有配置。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_config ORDER BY config_key")
            results = cursor.fetchall()
            cursor.close()
            return results

    def init_default_config(self) -> None:
        """初始化默认配置数据（在 _init_tables 中调用）。"""
        # 此方法在 _init_tables 中通过 cursor 直接调用
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
            pymysql.IntegrityError: 用户名或邮箱已存在
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, role)
                   VALUES (%s, %s, %s, %s)""",
                (username, email, password_hash, role)
            )
            lastrowid = cursor.lastrowid
            cursor.close()
            return lastrowid

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """根据用户名获取用户。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
            cursor.close()
            return row

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """根据邮箱获取用户。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            cursor.close()
            return row

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """根据用户 ID 获取用户。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            cursor.close()
            return row

    def update_user_password(self, user_id: int, password_hash: str) -> bool:
        """更新用户密码。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                (password_hash, user_id)
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated

    def update_last_login(self, user_id: int) -> bool:
        """更新用户最后登录时间。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login_at = NOW(), updated_at = NOW() WHERE id = %s",
                (user_id,)
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated

    def set_user_active(self, user_id: int, is_active: bool) -> bool:
        """激活或停用用户。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET is_active = %s, updated_at = NOW() WHERE id = %s",
                (is_active, user_id)
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated

    def list_users(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """列出用户（分页）。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, username, email, role, created_at, last_login_at, is_active
                   FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (limit, offset)
            )
            results = cursor.fetchall()
            cursor.close()
            return results

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
                updates.append(f"{key} = %s")
                params.append(value)

        if not updates:
            return False

        params.append(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE users SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s",
                params
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated

    def delete_user(self, user_id: int) -> bool:
        """删除用户（同时清除 user_preferences 中的关联）。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 清除 user_preferences 中的 user_id_int 关联
            cursor.execute("UPDATE user_preferences SET user_id_int = NULL WHERE user_id_int = %s", (user_id,))
            # 删除用户
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted

    def get_user_count(self) -> int:
        """获取用户总数。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            count = cursor.fetchone()["count"]
            cursor.close()
            return count
