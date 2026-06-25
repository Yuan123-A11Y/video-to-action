"""
任务管理器 - 持久化任务状态到 SQLite。

提供任务的创建、更新、查询功能，避免服务器重启后任务状态丢失。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class TaskManager:
    """管理任务的生命周期和持久化。"""
    
    def __init__(self, db_path: Path):
        """
        初始化任务管理器。
        
        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status 
                ON tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_created_at 
                ON tasks(created_at DESC)
            """)
    
    def create_task(self) -> int:
        """
        创建新任务。
        
        Returns:
            新任务的 ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (status) VALUES (?)",
                ("pending",)
            )
            return cursor.lastrowid
    
    def update_task(
        self, 
        task_id: int, 
        status: str, 
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        更新任务状态。
        
        Args:
            task_id: 任务 ID
            status: 新状态 (pending/processing/completed/failed)
            result: 任务结果（可选）
            error: 错误信息（可选）
        """
        with sqlite3.connect(self.db_path) as conn:
            if result is not None:
                conn.execute(
                    """UPDATE tasks 
                       SET status = ?, result = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE id = ?""",
                    (status, json.dumps(result, ensure_ascii=False), task_id)
                )
            elif error is not None:
                conn.execute(
                    """UPDATE tasks 
                       SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE id = ?""",
                    (status, error, task_id)
                )
            else:
                conn.execute(
                    """UPDATE tasks 
                       SET status = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE id = ?""",
                    (status, task_id)
                )
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        获取任务信息。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务信息字典，如果任务不存在则返回 None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT id, status, result, error, created_at, updated_at 
                   FROM tasks WHERE id = ?""",
                (task_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            task = dict(row)
            
            # 解析 result JSON
            if task.get("result"):
                task["result"] = json.loads(task["result"])
            
            return task
    
    def get_all_tasks(self, limit: int = 100, offset: int = 0) -> list[Dict[str, Any]]:
        """
        获取所有任务。
        
        Args:
            limit: 返回记录数限制
            offset: 偏移量
            
        Returns:
            任务列表
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT id, status, result, error, created_at, updated_at 
                   FROM tasks 
                   ORDER BY created_at DESC 
                   LIMIT ? OFFSET ?""",
                (limit, offset)
            )
            tasks = []
            for row in cursor.fetchall():
                task = dict(row)
                if task.get("result"):
                    task["result"] = json.loads(task["result"])
                tasks.append(task)
            return tasks
    
    def delete_task(self, task_id: int) -> bool:
        """
        删除任务。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否删除成功
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0
    
    def cleanup_old_tasks(self, days: int = 7):
        """
        清理旧任务。
        
        Args:
            days: 保留最近几天的任务
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """DELETE FROM tasks 
                   WHERE created_at < datetime('now', ?)""",
                (f"-{days} days",)
            )
