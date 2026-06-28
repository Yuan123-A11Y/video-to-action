"""
数据库迁移脚本：为 tools 表添加 idx_tool_name 索引。

支持 SQLite 和 MySQL 两种数据库。
使用方法：
    python database/migrate.py
"""

import os
import shutil
from pathlib import Path

import yaml


def load_database_config():
    """加载数据库配置。"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    db_config = config.get("database", {})
    
    # 处理 SQLite 数据库路径
    if db_config.get("type") == "sqlite":
        db_path = db_config.get("database", "data/video_to_action.db")
        # 如果是相对路径，转换为绝对路径
        if not Path(db_path).is_absolute():
            db_path = Path(__file__).parent.parent / db_path
        db_config["database_path"] = str(db_path)
    
    return db_config


def migrate_sqlite(db_path: str):
    """迁移 SQLite 数据库（需要重建表）。"""
    import sqlite3

    print(f"[MIGRATE] Start migrating SQLite database: {db_path}")

    # 1. 备份数据库
    backup_path = f"{db_path}.backup_{Path(__file__).stem}"
    shutil.copy2(db_path, backup_path)
    print(f"[OK] Database backed up to: {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 2. 检查索引是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_tool_name'")
        if cursor.fetchone():
            print("[SKIP] Index idx_tool_name already exists, skip migration")
            conn.close()
            return

        # 3. 创建新表（带索引）
        cursor.execute("""
            CREATE TABLE tools_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                purpose TEXT,
                links TEXT,
                install_commands TEXT,
                config_steps TEXT,
                warnings TEXT,
                video_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(id)
            )
        """)

        # 4. 创建索引
        cursor.execute("CREATE INDEX idx_tool_name ON tools_new(name)")

        # 5. 复制数据
        cursor.execute("""
            INSERT INTO tools_new
            SELECT id, name, purpose, links, install_commands, config_steps, warnings, video_id, created_at
            FROM tools
        """)

        # 6. 删除旧表
        cursor.execute("DROP TABLE tools")

        # 7. 重命名新表
        cursor.execute("ALTER TABLE tools_new RENAME TO tools")

        conn.commit()
        print("[OK] SQLite database migration successful!")

        # 8. 分析表以优化查询计划
        cursor.execute("ANALYZE tools")
        conn.commit()
        print("[OK] Executed ANALYZE to optimize query plan")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        conn.close()


def migrate_mysql(config: dict):
    """迁移 MySQL 数据库。"""
    import pymysql

    print(f"[MIGRATE] Start migrating MySQL database: {config['host']}:{config['port']}/{config['database']}")

    conn = pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
    )
    cursor = conn.cursor()

    try:
        # 2. 检查索引是否已存在
        cursor.execute("SHOW INDEX FROM tools WHERE Key_name = 'idx_tool_name'")
        if cursor.fetchone():
            print("[SKIP] Index idx_tool_name already exists, skip migration")
            conn.close()
            return

        # 3. 添加索引
        cursor.execute("ALTER TABLE tools ADD INDEX idx_tool_name (name(50))")

        conn.commit()
        print("[OK] MySQL database migration successful!")

        # 4. 分析表以优化查询计划
        cursor.execute("ANALYZE TABLE tools")
        conn.commit()
        print("[OK] Executed ANALYZE to optimize query plan")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        conn.close()


def main():
    """主函数。"""
    print("=" * 60)
    print("Video-to-Action Database Migration Script")
    print("Version: 1.1.0")
    print("Date: 2026-06-26")
    print("Description: Add idx_tool_name index to tools table")
    print("=" * 60)

    config = load_database_config()
    db_type = config.get("type", "sqlite")

    if db_type == "sqlite":
        db_path = config.get("database_path", "data/video_to_action.db")
        if not Path(db_path).exists():
            print(f"[WARN] Database file not found: {db_path}")
            print("[INFO] Please run 'python database/init_sqlite.py' to create database")
            return
        migrate_sqlite(db_path)
    elif db_type == "mysql":
        migrate_mysql(config)
    else:
        print(f"[ERROR] Unsupported database type: {db_type}")
        return

    print("\n[OK] Migration completed!")


if __name__ == "__main__":
    main()
