#!/usr/bin/env python3
"""
MySQL Database Initialization Script.

Creates the database and all tables for Video-to-Action project.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize MySQL database."""
    try:
        import aiomysql
    except ImportError:
        logger.error("aiomysql not installed. Install with: pip install aiomysql")
        sys.exit(1)
    
    # Load settings
    try:
        from config.settings import get_settings
        settings = get_settings()
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        logger.info("Please create .env file based on .env.example")
        sys.exit(1)
    
    # Read schema file
    schema_path = Path(__file__).parent / "database" / "schema.sql"
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        sys.exit(1)
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    # Connect to MySQL (without database)
    logger.info(f"Connecting to MySQL: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")
    
    try:
        conn = await aiomysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            charset="utf8mb4"
        )
        
        async with conn.cursor() as cursor:
            # Create database if not exists
            logger.info(f"Creating database: {settings.MYSQL_DATABASE}")
            await cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.MYSQL_DATABASE}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            await conn.commit()
        
        conn.close()
        
        # Connect to the database and execute schema
        conn = await aiomysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            db=settings.MYSQL_DATABASE,
            charset="utf8mb4",
            autocommit=True
        )
        
        async with conn.cursor() as cursor:
            # Execute schema SQL (split by ;)
            logger.info("Executing schema SQL...")
            sql_commands = [cmd.strip() for cmd in schema_sql.split(";") if cmd.strip()]
            
            for cmd in sql_commands:
                if cmd:  # Skip empty commands
                    try:
                        await cursor.execute(cmd)
                        logger.debug(f"Executed: {cmd[:50]}...")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            logger.warning(f"Skipped (already exists): {cmd[:50]}...")
                        else:
                            logger.error(f"Error executing: {cmd[:100]}...")
                            logger.error(f"Error: {e}")
            
            logger.info("Schema execution completed!")
        
        conn.close()
        
        # Verify installation
        logger.info("Verifying installation...")
        conn = await aiomysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            db=settings.MYSQL_DATABASE,
            charset="utf8mb4"
        )
        
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES")
            tables = await cursor.fetchall()
            logger.info(f"Created tables: {[t[0] for t in tables]}")
        
        conn.close()
        
        logger.info("✅ Database initialization completed successfully!")
        logger.info(f"\nYou can now:")
        logger.info(f"  1. Review the configuration in .env file")
        logger.info(f"  2. Run the application: python start_web.py")
        logger.info(f"  3. If you have existing SQLite data, run: python -m database.migrate_to_mysql")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_database())
