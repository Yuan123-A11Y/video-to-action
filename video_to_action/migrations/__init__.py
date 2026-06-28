"""
数据库迁移脚本 - 用于升级数据库 schema。

此脚本会被 `knowledge_base.py` 和 `mysql_knowledge_base.py` 在初始化时调用，
也可以在部署时手动运行以升级现有数据库。

使用方法：
    python -m video_to_action.migrations.migrate_sqlite [db_path]
    python -m video_to_action.migrations.migrate_mysql

或者直接在代码中使用：
    from video_to_action.migrations.migrate_sqlite import migrate as sqlite_migrate
    sqlite_migrate("path/to/db.sqlite")

    from video_to_action.migrations.migrate_mysql import migrate as mysql_migrate
    mysql_migrate()
"""

__version__ = "1.0.0"
