"""
Async MySQL database operations for Video-to-Action.
Uses aiomysql for async MySQL operations with connection pooling.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiomysql
from aiomysql import Pool, Cursor

from config.settings import get_settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[Pool] = None


async def init_db() -> Pool:
    """Initialize database connection pool."""
    global _pool
    
    settings = get_settings()
    
    if _pool is not None:
        return _pool
    
    logger.info(f"Initializing MySQL connection pool: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")
    
    _pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=False,  # Manual transaction control
        minsize=1,
        maxsize=settings.MYSQL_POOL_SIZE,
        echo=settings.DEBUG,
    )
    
    # Test connection
    async with _pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT 1")
            result = await cursor.fetchone()
            if result and result[0] == 1:
                logger.info("MySQL connection test successful")
            else:
                raise Exception("MySQL connection test failed")
    
    return _pool


async def close_db() -> None:
    """Close database connection pool."""
    global _pool
    
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
        logger.info("MySQL connection pool closed")


@asynccontextmanager
async def get_connection():
    """Get database connection from pool."""
    if _pool is None:
        await init_db()
    
    async with _pool.acquire() as conn:
        try:
            yield conn
        except Exception as e:
            await conn.rollback()
            logger.error(f"Database error: {e}")
            raise


@asynccontextmanager
async def get_cursor():
    """Get database cursor from pool."""
    async with get_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            try:
                yield cursor
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f"Cursor error: {e}")
                raise


class Database:
    """Database operations wrapper."""
    
    # ==================================================
    # Video operations
    # ==================================================
    
    @staticmethod
    async def create_video(data: Dict[str, Any]) -> int:
        """Create video record."""
        async with get_cursor() as cursor:
            sql = """
                INSERT INTO videos 
                (url, platform, video_id, title, author_name, author_id, 
                 duration, theme, summary, transcription_text, analysis_result,
                 file_path, file_size, status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            await cursor.execute(sql, (
                data.get("url"),
                data.get("platform", "unknown"),
                data.get("video_id"),
                data.get("title"),
                data.get("author_name"),
                data.get("author_id"),
                data.get("duration"),
                data.get("theme"),
                data.get("summary"),
                data.get("transcription_text"),
                json.dumps(data.get("analysis_result"), ensure_ascii=False) if data.get("analysis_result") else None,
                data.get("file_path"),
                data.get("file_size"),
                data.get("status", "pending"),
                data.get("error_message"),
            ))
            return cursor.lastrowid
    
    @staticmethod
    async def get_video_by_id(video_id: int) -> Optional[Dict[str, Any]]:
        """Get video by ID."""
        async with get_cursor() as cursor:
            await cursor.execute("SELECT * FROM videos WHERE id = %s", (video_id,))
            return await cursor.fetchone()
    
    @staticmethod
    async def get_video_by_url(url: str) -> Optional[Dict[str, Any]]:
        """Get video by URL."""
        async with get_cursor() as cursor:
            await cursor.execute("SELECT * FROM videos WHERE url = %s", (url,))
            return await cursor.fetchone()
    
    @staticmethod
    async def update_video(video_id: int, data: Dict[str, Any]) -> bool:
        """Update video record."""
        async with get_cursor() as cursor:
            # Build dynamic update SQL
            fields = []
            values = []
            for key, value in data.items():
                if key in ["analysis_result"]:
                    value = json.dumps(value, ensure_ascii=False) if value else None
                fields.append(f"{key} = %s")
                values.append(value)
            
            if not fields:
                return False
            
            values.append(video_id)
            sql = f"UPDATE videos SET {', '.join(fields)} WHERE id = %s"
            await cursor.execute(sql, values)
            return cursor.rowcount > 0
    
    @staticmethod
    async def delete_video(video_id: int) -> bool:
        """Delete video record."""
        async with get_cursor() as cursor:
            await cursor.execute("DELETE FROM videos WHERE id = %s", (video_id,))
            return cursor.rowcount > 0
    
    @staticmethod
    async def list_videos(
        platform: Optional[str] = None,
        status: Optional[str] = None,
        theme: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List videos with pagination."""
        async with get_cursor() as cursor:
            # Build WHERE clause
            where_parts = []
            params = []
            
            if platform:
                where_parts.append("platform = %s")
                params.append(platform)
            
            if status:
                where_parts.append("status = %s")
                params.append(status)
            
            if theme:
                where_parts.append("theme = %s")
                params.append(theme)
            
            if keyword:
                where_parts.append("(title LIKE %s OR transcription_text LIKE %s)")
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            
            # Count total
            count_sql = f"SELECT COUNT(*) as total FROM videos {where_sql}"
            await cursor.execute(count_sql, params)
            total = (await cursor.fetchone())["total"]
            
            # Fetch page
            offset = (page - 1) * size
            list_sql = f"""
                SELECT * FROM videos {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            await cursor.execute(list_sql, params + [size, offset])
            items = await cursor.fetchall()
            
            return items, total
    
    # ==================================================
    # Tool operations
    # ==================================================
    
    @staticmethod
    async def create_tool(data: Dict[str, Any]) -> int:
        """Create tool record."""
        async with get_cursor() as cursor:
            sql = """
                INSERT INTO tools
                (name, category, purpose, description, install_commands, config_steps,
                 usage_examples, warnings, alternatives, homepage_url, documentation_url,
                 is_paid, needs_credential, license_type, programming_language,
                 github_url, version, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            await cursor.execute(sql, (
                data.get("name"),
                data.get("category"),
                data.get("purpose"),
                data.get("description"),
                json.dumps(data.get("install_commands"), ensure_ascii=False) if data.get("install_commands") else None,
                json.dumps(data.get("config_steps"), ensure_ascii=False) if data.get("config_steps") else None,
                json.dumps(data.get("usage_examples"), ensure_ascii=False) if data.get("usage_examples") else None,
                data.get("warnings"),
                json.dumps(data.get("alternatives"), ensure_ascii=False) if data.get("alternatives") else None,
                data.get("homepage_url"),
                data.get("documentation_url"),
                data.get("is_paid", False),
                data.get("needs_credential", False),
                data.get("license_type"),
                data.get("programming_language"),
                data.get("github_url"),
                data.get("version"),
                json.dumps(data.get("tags"), ensure_ascii=False) if data.get("tags") else None,
            ))
            return cursor.lastrowid
    
    @staticmethod
    async def get_tool_by_id(tool_id: int) -> Optional[Dict[str, Any]]:
        """Get tool by ID."""
        async with get_cursor() as cursor:
            await cursor.execute("SELECT * FROM tools WHERE id = %s", (tool_id,))
            return await cursor.fetchone()
    
    @staticmethod
    async def get_tool_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Get tool by name."""
        async with get_cursor() as cursor:
            await cursor.execute("SELECT * FROM tools WHERE name = %s", (name,))
            return await cursor.fetchone()
    
    @staticmethod
    async def update_tool(tool_id: int, data: Dict[str, Any]) -> bool:
        """Update tool record."""
        async with get_cursor() as cursor:
            fields = []
            values = []
            for key, value in data.items():
                if key in ["install_commands", "config_steps", "usage_examples", "alternatives", "tags"]:
                    value = json.dumps(value, ensure_ascii=False) if value else None
                fields.append(f"{key} = %s")
                values.append(value)
            
            if not fields:
                return False
            
            values.append(tool_id)
            sql = f"UPDATE tools SET {', '.join(fields)} WHERE id = %s"
            await cursor.execute(sql, values)
            return cursor.rowcount > 0
    
    @staticmethod
    async def delete_tool(tool_id: int) -> bool:
        """Delete tool record."""
        async with get_cursor() as cursor:
            await cursor.execute("DELETE FROM tools WHERE id = %s", (tool_id,))
            return cursor.rowcount > 0
    
    @staticmethod
    async def list_tools(
        category: Optional[str] = None,
        is_paid: Optional[bool] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List tools with pagination."""
        async with get_cursor() as cursor:
            where_parts = []
            params = []
            
            if category:
                where_parts.append("category = %s")
                params.append(category)
            
            if is_paid is not None:
                where_parts.append("is_paid = %s")
                params.append(is_paid)
            
            if keyword:
                where_parts.append("(name LIKE %s OR purpose LIKE %s)")
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            
            await cursor.execute(f"SELECT COUNT(*) as total FROM tools {where_sql}", params)
            total = (await cursor.fetchone())["total"]
            
            offset = (page - 1) * size
            await cursor.execute(f"""
                SELECT * FROM tools {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, params + [size, offset])
            items = await cursor.fetchall()
            
            return items, total
    
    # ==================================================
    # Video-Tool relationship operations
    # ==================================================
    
    @staticmethod
    async def link_video_tool(video_id: int, tool_id: int, relevance_score: float = 0.5) -> bool:
        """Link video and tool."""
        async with get_cursor() as cursor:
            sql = """
                INSERT INTO video_tools (video_id, tool_id, relevance_score)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE relevance_score = VALUES(relevance_score)
            """
            await cursor.execute(sql, (video_id, tool_id, relevance_score))
            return cursor.rowcount > 0
    
    @staticmethod
    async def unlink_video_tool(video_id: int, tool_id: int) -> bool:
        """Unlink video and tool."""
        async with get_cursor() as cursor:
            await cursor.execute(
                "DELETE FROM video_tools WHERE video_id = %s AND tool_id = %s",
                (video_id, tool_id)
            )
            return cursor.rowcount > 0
    
    @staticmethod
    async def get_tools_by_video(video_id: int) -> List[Dict[str, Any]]:
        """Get tools linked to a video."""
        async with get_cursor() as cursor:
            sql = """
                SELECT t.*, vt.relevance_score, vt.mention_count
                FROM tools t
                INNER JOIN video_tools vt ON t.id = vt.tool_id
                WHERE vt.video_id = %s
                ORDER BY vt.relevance_score DESC
            """
            await cursor.execute(sql, (video_id,))
            return await cursor.fetchall()
    
    @staticmethod
    async def get_videos_by_tool(tool_id: int, page: int = 1, size: int = 20) -> Tuple[List[Dict[str, Any]], int]:
        """Get videos linked to a tool."""
        async with get_cursor() as cursor:
            await cursor.execute(
                "SELECT COUNT(*) as total FROM video_tools WHERE tool_id = %s",
                (tool_id,)
            )
            total = (await cursor.fetchone())["total"]
            
            offset = (page - 1) * size
            sql = """
                SELECT v.*, vt.relevance_score
                FROM videos v
                INNER JOIN video_tools vt ON v.id = vt.video_id
                WHERE vt.tool_id = %s
                ORDER BY vt.relevance_score DESC
                LIMIT %s OFFSET %s
            """
            await cursor.execute(sql, (tool_id, size, offset))
            items = await cursor.fetchall()
            
            return items, total
    
    # ==================================================
    # Download Job operations
    # ==================================================
    
    @staticmethod
    async def create_download_job(data: Dict[str, Any]) -> str:
        """Create download job."""
        async with get_cursor() as cursor:
            sql = """
                INSERT INTO download_jobs
                (job_id, url, url_type, status, created_at, started_at, finished_at,
                 total_count, success_count, failed_count, skipped_count, error_message,
                 author_nickname, author_sec_uid, retry_count, last_retry_at,
                 last_retry_summary, retry_history, overrides)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            await cursor.execute(sql, (
                data.get("job_id"),
                data.get("url"),
                data.get("url_type"),
                data.get("status", "pending"),
                data.get("created_at"),
                data.get("started_at"),
                data.get("finished_at"),
                data.get("total_count", 0),
                data.get("success_count", 0),
                data.get("failed_count", 0),
                data.get("skipped_count", 0),
                data.get("error_message"),
                data.get("author_nickname"),
                data.get("author_sec_uid"),
                data.get("retry_count", 0),
                data.get("last_retry_at"),
                json.dumps(data.get("last_retry_summary"), ensure_ascii=False) if data.get("last_retry_summary") else None,
                json.dumps(data.get("retry_history"), ensure_ascii=False) if data.get("retry_history") else None,
                json.dumps(data.get("overrides"), ensure_ascii=False) if data.get("overrides") else None,
            ))
            return data.get("job_id")
    
    @staticmethod
    async def update_download_job(job_id: str, data: Dict[str, Any]) -> bool:
        """Update download job."""
        async with get_cursor() as cursor:
            fields = []
            values = []
            for key, value in data.items():
                if key in ["last_retry_summary", "retry_history", "overrides"]:
                    value = json.dumps(value, ensure_ascii=False) if value else None
                fields.append(f"{key} = %s")
                values.append(value)
            
            if not fields:
                return False
            
            values.append(job_id)
            sql = f"UPDATE download_jobs SET {', '.join(fields)} WHERE job_id = %s"
            await cursor.execute(sql, values)
            return cursor.rowcount > 0
    
    @staticmethod
    async def get_download_job(job_id: str) -> Optional[Dict[str, Any]]:
        """Get download job."""
        async with get_cursor() as cursor:
            await cursor.execute("SELECT * FROM download_jobs WHERE job_id = %s", (job_id,))
            return await cursor.fetchone()
    
    @staticmethod
    async def list_download_jobs(
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List download jobs with pagination."""
        async with get_cursor() as cursor:
            where_parts = []
            params = []
            
            if status:
                where_parts.append("status = %s")
                params.append(status)
            
            where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            
            await cursor.execute(f"SELECT COUNT(*) as total FROM download_jobs {where_sql}", params)
            total = (await cursor.fetchone())["total"]
            
            offset = (page - 1) * size
            await cursor.execute(f"""
                SELECT * FROM download_jobs {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, params + [size, offset])
            items = await cursor.fetchall()
            
            return items, total
    
    # ==================================================
    # System Config operations
    # ==================================================
    
    @staticmethod
    async def get_config(key: str) -> Optional[Any]:
        """Get system config value."""
        async with get_cursor() as cursor:
            await cursor.execute(
                "SELECT config_value, config_type FROM system_config WHERE config_key = %s",
                (key,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            
            value = row["config_value"]
            config_type = row["config_type"]
            
            # Type conversion
            if config_type == "integer":
                return int(value)
            elif config_type == "float":
                return float(value)
            elif config_type == "boolean":
                return value.lower() in ["true", "1", "yes"]
            elif config_type == "json":
                return json.loads(value)
            else:
                return value
    
    @staticmethod
    async def set_config(key: str, value: Any, config_type: str = "string", description: str = "") -> bool:
        """Set system config value."""
        async with get_cursor() as cursor:
            if config_type == "json":
                value = json.dumps(value, ensure_ascii=False)
            else:
                value = str(value)
            
            sql = """
                INSERT INTO system_config (config_key, config_value, config_type, description)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    config_value = VALUES(config_value),
                    config_type = VALUES(config_type),
                    description = VALUES(description)
            """
            await cursor.execute(sql, (key, value, config_type, description))
            return cursor.rowcount > 0
