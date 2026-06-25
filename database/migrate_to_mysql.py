#!/usr/bin/env python3
"""
SQLite to MySQL Migration Script.

Migrates data from existing SQLite databases to the new MySQL database.
"""

import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Paths to SQLite databases
SQLITE_DBS = [
    Path("data/knowledge_base.db"),
    Path("data/dy_downloader.db"),
]


async def migrate_knowledge_base(sqlite_path: Path, mysql_db):
    """Migrate knowledge base data (videos, tools, video_tools)."""
    logger.info(f"Migrating knowledge base: {sqlite_path}")
    
    if not sqlite_path.exists():
        logger.warning(f"Database not found: {sqlite_path}")
        return
    
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()
    
    try:
        # Migrate videos
        logger.info("Migrating videos...")
        cursor.execute("SELECT * FROM videos")
        videos = cursor.fetchall()
        
        for video in videos:
            video_dict = dict(video)
            # Check if already exists
            existing = await mysql_db.get_video_by_url(video_dict["url"])
            if not existing:
                await mysql_db.create_video({
                    "url": video_dict["url"],
                    "platform": video_dict.get("platform", "unknown"),
                    "title": video_dict.get("title"),
                    "theme": video_dict.get("theme"),
                    "summary": video_dict.get("summary"),
                    "transcription_text": video_dict.get("transcription_text"),
                    "analysis_result": video_dict.get("analysis_result"),
                    "status": "completed" if video_dict.get("transcription_text") else "pending",
                })
                logger.info(f"Migrated video: {video_dict.get('title', 'Unknown')}")
        
        # Migrate tools
        logger.info("Migrating tools...")
        cursor.execute("SELECT * FROM tools")
        tools = cursor.fetchall()
        
        for tool in tools:
            tool_dict = dict(tool)
            existing = await mysql_db.get_tool_by_name(tool_dict["name"])
            if not existing:
                await mysql_db.create_tool({
                    "name": tool_dict["name"],
                    "purpose": tool_dict.get("purpose"),
                    "description": tool_dict.get("warnings"),
                    "is_paid": bool(tool_dict.get("is_paid", 0)),
                    "needs_credential": bool(tool_dict.get("needs_credential", 0)),
                })
                logger.info(f"Migrated tool: {tool_dict['name']}")
        
        # Migrate video_tools
        logger.info("Migrating video-tool relationships...")
        cursor.execute("SELECT * FROM video_tools")
        video_tools = cursor.fetchall()
        
        for vt in video_tools:
            vt_dict = dict(vt)
            # Get MySQL IDs
            video = await mysql_db.get_video_by_url(
                (await _get_video_url_by_id(sqlite_path, vt_dict["video_id"])) or ""
            )
            if video:
                tool = await mysql_db.get_tool_by_name(
                    (await _get_tool_name_by_id(sqlite_path, vt_dict["tool_id"])) or ""
                )
                if tool:
                    await mysql_db.link_video_tool(video["id"], tool["id"])
                    logger.info(f"Linked video {video['id']} to tool {tool['id']}")
        
        logger.info(f"Knowledge base migration completed: {len(videos)} videos, {len(tools)} tools")
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise
    finally:
        sqlite_conn.close()


async def migrate_douyin_downloader(sqlite_path: Path, mysql_db):
    """Migrate Douyin downloader data."""
    logger.info(f"Migrating Douyin downloader: {sqlite_path}")
    
    if not sqlite_path.exists():
        logger.warning(f"Database not found: {sqlite_path}")
        return
    
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()
    
    try:
        # Migrate aweme to downloaded_videos
        logger.info("Migrating downloaded videos...")
        cursor.execute("SELECT * FROM aweme")
        awemes = cursor.fetchall()
        
        for aweme in awemes:
            aweme_dict = dict(aweme)
            async with mysql_db.get_cursor() as mysql_cursor:
                await mysql_cursor.execute(
                    """
                    INSERT IGNORE INTO downloaded_videos
                    (aweme_id, aweme_type, title, author_id, author_name, author_sec_uid,
                     create_time, download_time, file_path, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), FROM_UNIXTIME(%s), %s, %s)
                    """,
                    (
                        aweme_dict["aweme_id"],
                        aweme_dict.get("aweme_type"),
                        aweme_dict.get("title"),
                        aweme_dict.get("author_id"),
                        aweme_dict.get("author_name"),
                        aweme_dict.get("author_sec_uid"),
                        aweme_dict.get("create_time"),
                        aweme_dict.get("download_time"),
                        aweme_dict.get("file_path"),
                        aweme_dict.get("metadata"),
                    )
                )
                logger.info(f"Migrated aweme: {aweme_dict.get('title', 'Unknown')}")
        
        logger.info(f"Douyin downloader migration completed: {len(awemes)} videos")
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise
    finally:
        sqlite_conn.close()


async def _get_video_url_by_id(sqlite_path: Path, video_id: int) -> Optional[str]:
    """Helper to get video URL by ID from SQLite."""
    try:
        conn = sqlite3.connect(str(sqlite_path))
        cursor = conn.cursor()
        cursor.execute("SELECT url FROM videos WHERE id = ?", (video_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None


async def _get_tool_name_by_id(sqlite_path: Path, tool_id: int) -> Optional[str]:
    """Helper to get tool name by ID from SQLite."""
    try:
        conn = sqlite3.connect(str(sqlite_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM tools WHERE id = ?", (tool_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None


async def main():
    """Main migration function."""
    logger.info("Starting SQLite to MySQL migration...")
    
    # Import here to avoid circular imports
    from database.mysql_db import init_db, close_db, Database
    
    try:
        # Initialize MySQL connection
        await init_db()
        logger.info("MySQL connection established")
        
        # Migrate each SQLite database
        for sqlite_path in SQLITE_DBS:
            if "knowledge_base" in sqlite_path.name:
                await migrate_knowledge_base(sqlite_path, Database)
            elif "dy_downloader" in sqlite_path.name:
                await migrate_douyin_downloader(sqlite_path, Database)
        
        logger.info("✅ Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
