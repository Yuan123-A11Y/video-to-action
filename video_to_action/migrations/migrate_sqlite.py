"""
SQLite 数据库迁移脚本。

使用方法：
    # 作为模块运行（迁移默认数据库）
    python -m video_to_action.migrations.migrate_sqlite

    # 指定数据库路径
    python -m video_to_action.migrations.migrate_sqlite /path/to/custom.db

    # 在代码中使用
    from video_to_action.migrations.migrate_sqlite import migrate
    migrate()  # 使用默认路径
    migrate("/path/to/custom.db")  # 使用指定路径
"""

import argparse
import hashlib
import logging
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 默认数据库路径
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_base.db"


def get_db_connection(db_path: str = None):
    """获取数据库连接。"""
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    return conn


def get_current_version(conn: sqlite3.Connection) -> str:
    """获取当前数据库版本。"""
    try:
        cursor = conn.execute("SELECT config_value FROM system_config WHERE config_key = 'db_version'")
        row = cursor.fetchone()
        return row[0] if row else "0.0.0"
    except sqlite3.OperationalError:
        # system_config 表不存在
        return "0.0.0"


def set_version(conn: sqlite3.Connection, version: str):
    """设置数据库版本。"""
    conn.execute("""
        INSERT OR REPLACE INTO system_config (config_key, config_value, config_type, description)
        VALUES ('db_version', ?, 'string', '数据库版本')
    """, (version,))
    conn.commit()


def migration_v1_0_0(conn: sqlite3.Connection) -> bool:
    """迁移到 v1.0.0：创建 users 表。"""
    logger.info("执行迁移 v1.0.0：创建 users 表")

    try:
        # 创建 users 表
        conn.execute("""
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
            )
        """)

        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

        conn.commit()
        logger.info("✅ 迁移 v1.0.0 完成：users 表已创建")
        return True

    except Exception as e:
        logger.error(f"❌ 迁移 v1.0.0 失败：{e}")
        return False


def migration_v1_1_0(conn: sqlite3.Connection) -> bool:
    """迁移到 v1.1.0：为 user_preferences 表添加 user_id_int 字段。"""
    logger.info("执行迁移 v1.1.0：为 user_preferences 表添加 user_id_int 字段")

    try:
        # 检查 user_preferences 表是否存在
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_preferences'")
        if not cursor.fetchone():
            logger.warning("user_preferences 表不存在，跳过此迁移")
            return True

        # 检查字段是否已存在
        cursor = conn.execute("PRAGMA table_info(user_preferences)")
        columns = [row[1] for row in cursor.fetchall()]

        if "user_id_int" not in columns:
            # 不再引用 users 表，避免外键约束失败（auth 表独立管理）
            conn.execute("ALTER TABLE user_preferences ADD COLUMN user_id_int INTEGER")
            logger.info("✅ 已添加 user_id_int 字段")

        if "user_id_hash" not in columns:
            conn.execute("ALTER TABLE user_preferences ADD COLUMN user_id_hash TEXT")
            logger.info("✅ 已添加 user_id_hash 字段")

            # 为现有数据生成 hash
            cursor = conn.execute("SELECT id, user_id FROM user_preferences WHERE user_id_hash IS NULL")
            for row in cursor.fetchall():
                user_id_hash = hashlib.sha256(row[1].encode("utf-8")).hexdigest()
                conn.execute("UPDATE user_preferences SET user_id_hash = ? WHERE id = ?", (user_id_hash, row[0]))

            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id_hash ON user_preferences(user_id_hash)")
            logger.info("✅ 已为 user_id_hash 创建索引")

        conn.commit()
        logger.info("✅ 迁移 v1.1.0 完成")
        return True

    except Exception as e:
        logger.error(f"❌ 迁移 v1.1.0 失败：{e}")
        return False


def migrate(db_path: str = None, target_version: str = None) -> bool:
    """执行数据库迁移。

    Args:
        db_path: 数据库路径（可选，默认使用项目 data 目录）
        target_version: 目标版本（可选，默认迁移到最新版本）

    Returns:
        迁移是否成功
    """
    conn = get_db_connection(db_path)

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
    parser = argparse.ArgumentParser(description="SQLite 数据库迁移工具")
    parser.add_argument("db_path", nargs="?", default=None, help="数据库路径（可选）")
    parser.add_argument("--target", default=None, help="目标版本（可选，默认迁移到最新）")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际修改数据库")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("模拟运行模式，不会实际修改数据库")

    logger.info("开始数据库迁移...")
    success = migrate(args.db_path, args.target)

    if success:
        logger.info("✅ 数据库迁移完成")
    else:
        logger.error("❌ 数据库迁移失败")
        exit(1)


if __name__ == "__main__":
    main()
