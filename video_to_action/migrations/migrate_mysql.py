"""
MySQL 数据库迁移脚本。

使用方法：
    # 作为模块运行（使用 .env 中的配置）
    python -m video_to_action.migrations.migrate_mysql

    # 在代码中使用
    from video_to_action.migrations.migrate_mysql import migrate
    migrate()  # 使用默认配置
    migrate(host="localhost", user="root", password="", database="custom_db")  # 使用指定配置
"""

import argparse
import logging
from typing import Optional

import pymysql
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


def get_db_connection(
    host: str = None,
    port: int = None,
    user: str = None,
    password: str = None,
    database: str = None
):
    """获取数据库连接。"""
    connection = pymysql.connect(
        host=host or os.getenv("MYSQL_HOST", "localhost"),
        port=port or int(os.getenv("MYSQL_PORT", "3306")),
        user=user or os.getenv("MYSQL_USER", "root"),
        password=password or os.getenv("MYSQL_PASSWORD", ""),
        database=database or os.getenv("MYSQL_DATABASE", "video_to_action"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection


def get_current_version(conn) -> str:
    """获取当前数据库版本。"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT config_value FROM system_config WHERE config_key = 'db_version'")
            row = cursor.fetchone()
            return row["config_value"] if row else "0.0.0"
    except pymysql.OperationalError:
        # system_config 表不存在
        return "0.0.0"


def set_version(conn, version: str):
    """设置数据库版本。"""
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO system_config (config_key, config_value, config_type, description)
            VALUES ('db_version', %s, 'string', '数据库版本')
            ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
        """, (version,))
    conn.commit()


def migration_v1_0_0(conn) -> bool:
    """迁移到 v1.0.0：创建 users 表。"""
    logger.info("执行迁移 v1.0.0：创建 users 表")

    try:
        with conn.cursor() as cursor:
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

        conn.commit()
        logger.info("✅ 迁移 v1.0.0 完成：users 表已创建")
        return True

    except Exception as e:
        logger.error(f"❌ 迁移 v1.0.0 失败：{e}")
        conn.rollback()
        return False


def migration_v1_1_0(conn) -> bool:
    """迁移到 v1.1.0：为 user_preferences 表添加 user_id_int 字段。"""
    logger.info("执行迁移 v1.1.0：为 user_preferences 表添加 user_id_int 字段")

    try:
        with conn.cursor() as cursor:
            # 检查 user_preferences 表是否存在
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'user_preferences'
            """, (conn.db,))

            if not cursor.fetchone():
                logger.warning("user_preferences 表不存在，跳过此迁移")
                return True

            # 检查字段是否已存在
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'user_preferences'
                  AND COLUMN_NAME = 'user_id_int'
            """, (conn.db,))

            if not cursor.fetchone():
                # 添加 user_id_int 字段（先检查 users 表是否存在）
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'
                """, (conn.db,))
                users_exists = cursor.fetchone()[0] > 0

                if users_exists:
                    cursor.execute("""
                        ALTER TABLE user_preferences
                        ADD COLUMN user_id_int INT UNSIGNED,
                        ADD CONSTRAINT fk_user_preferences_user_id_int
                        FOREIGN KEY (user_id_int) REFERENCES users(id) ON DELETE SET NULL
                    """)
                    logger.info("✅ 已添加 user_id_int 字段（含外键）")
                else:
                    try:
                        cursor.execute("""
                            ALTER TABLE user_preferences
                            ADD COLUMN user_id_int INT UNSIGNED
                        """)
                        logger.info("✅ 已添加 user_id_int 字段（无外键，users 表不存在）")
                    except Exception as e:
                        logger.warning(f"⚠️ 添加 user_id_int 失败: {e}")

            # 检查 user_id_hash 字段是否已存在
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'user_preferences'
                  AND COLUMN_NAME = 'user_id_hash'
            """, (conn.db,))

            if not cursor.fetchone():
                # 添加 user_id_hash 字段
                cursor.execute("""
                    ALTER TABLE user_preferences
                    ADD COLUMN user_id_hash CHAR(64) GENERATED ALWAYS AS (SHA2(user_id, 256)) STORED UNIQUE
                """)
                logger.info("✅ 已添加 user_id_hash 字段")

        conn.commit()
        logger.info("✅ 迁移 v1.1.0 完成")
        return True

    except Exception as e:
        logger.error(f"❌ 迁移 v1.1.0 失败：{e}")
        conn.rollback()
        return False


def migrate(
    host: str = None,
    port: int = None,
    user: str = None,
    password: str = None,
    database: str = None,
    target_version: str = None
) -> bool:
    """执行数据库迁移。

    Args:
        host: MySQL 主机地址
        port: MySQL 端口
        user: MySQL 用户名
        password: MySQL 密码
        database: MySQL 数据库名
        target_version: 目标版本（可选，默认迁移到最新版本）

    Returns:
        迁移是否成功
    """
    conn = get_db_connection(host, port, user, password, database)

    try:
        # 获取当前版本
        current_version = get_current_version(conn)
        logger.info(f"当前数据库版本：{current_version}")

        # 定义迁移路径
        migrations = [
            ("1.0.0", migration_v1_0_0),
            ("1.1.0", migration_v1_1_0),
        ]

        # 执行迁移
        migrated = False
        for version, migration_func in migrations:
            if current_version < version:
                if target_version and version > target_version:
                    break

                logger.info(f"开始迁移到 v{version}")
                if migration_func(conn):
                    set_version(conn, version)
                    current_version = version
                    migrated = True
                else:
                    logger.error(f"迁移到 v{version} 失败")
                    return False

        if not migrated:
            logger.info("数据库已是最新版本，无需迁移")

        return True

    except Exception as e:
        logger.error(f"迁移失败：{e}")
        return False

    finally:
        conn.close()


def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="MySQL 数据库迁移工具")
    parser.add_argument("--host", default=None, help="MySQL 主机地址")
    parser.add_argument("--port", type=int, default=None, help="MySQL 端口")
    parser.add_argument("--user", default=None, help="MySQL 用户名")
    parser.add_argument("--password", default=None, help="MySQL 密码")
    parser.add_argument("--database", default=None, help="MySQL 数据库名")
    parser.add_argument("--target", default=None, help="目标版本（可选，默认迁移到最新）")
    args = parser.parse_args()

    logger.info("开始数据库迁移...")
    success = migrate(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        target_version=args.target
    )

    if success:
        logger.info("✅ 数据库迁移完成")
    else:
        logger.error("❌ 数据库迁移失败")
        exit(1)


if __name__ == "__main__":
    main()
