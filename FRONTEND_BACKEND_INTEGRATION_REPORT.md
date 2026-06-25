# Video-to-Action 前后端联调修复方案

## 📊 执行摘要

本文档全面分析了 `video-to-action` 项目的前后端交互逻辑，识别了 **5 个关键问题**，并提供了详细的修复方案。

**关键发现**：
- ✅ 前端所有 API 调用都有对应的后端接口（8/8 已连接）
- 🔴 3 个严重问题需要立即修复
- 🟡 2 个功能缺失需要补充

---

## 一、前端-后端 API 映射表

### 1.1 完整接口对照

| 前端调用位置 | HTTP 方法 | API 路径 | 请求参数 | 后端状态 | 响应数据格式 |
|-------------|----------|---------|---------|---------|------------|
| `index.html:814` | POST | `/api/process` | `{url, level, save_to_kb}` | ✅ | `{success, message, data: {task_id}}` |
| `index.html:846` | GET | `/api/tasks/{task_id}` | - | ✅ | `{status, result}` |
| `index.html:907` | GET | `/api/videos` | `?limit=100&offset=0` | ✅ | `{videos: [...]}` |
| `index.html:1099` | GET | `/api/videos/{id}` | - | ✅ | `{id, url, platform, ...}` |
| `index.html:952` | GET | `/api/tools` | `?limit=100&offset=0` | ✅ | `{tools: [...]}` |
| `index.html:1141` | GET | `/api/tools/{id}` | - | ✅ | `{id, name, purpose, ...}` |
| `index.html:1004` | GET | `/api/search` | `?query=...&type=...` | ✅ | `{results: [...]}` |
| `index.html:1047` | GET | `/api/stats` | - | ✅ | `{video_count, tool_count, platform_stats}` |

### 1.2 数据结构对照

#### 视频对象（Video）
```typescript
// 前端期望的数据格式
interface Video {
  id: number;
  url: string;
  platform: string;  // "douyin", "bilibili", "youtube"
  title: string | null;
  theme: string;
  summary: string;
  transcription_text: string;
  analysis_result: object;
  created_at: string;  // ISO 8601
  tools: Tool[];  // 关联工具
}
```

#### 工具对象（Tool）
```typescript
// 前端期望的数据格式
interface Tool {
  id: number;
  name: string;
  purpose: string;
  install_commands: string[];
  config_steps: string[];
  warnings: string[];
  alternatives: string[];
  is_paid: boolean;
  needs_credential: boolean;
  videos: Video[];  // 来源视频
}
```

#### 任务对象（Task）
```typescript
// 前端期望的数据格式
interface Task {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result: {
    theme?: string;
    summary?: string;
    tools?: Tool[];
    video_path?: string;
    transcription_length?: number;
    frame_count?: number;
    error?: string;
  } | null;
}
```

---

## 二、关键问题清单

### 🔴 严重问题（P0）

#### 问题 1：任务状态存储在内存，重启丢失

**位置**：`api/main.py` 第 59 行
```python
# 当前实现
tasks = {}  # 全局变量，存储在内存中
```

**问题**：
- 服务器重启后所有任务状态丢失
- 无法在多进程/多机器环境下共享任务状态
- 用户刷新页面后无法看到历史任务

**修复方案**：使用 SQLite 或 Redis 持久化任务状态

**修复代码**：
```python
# 方案 A：使用 SQLite（简单，无需额外依赖）
import sqlite3
from pathlib import Path

class TaskManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def create_task(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (status) VALUES ('pending')"
            )
            return cursor.lastrowid
    
    def update_task(self, task_id: int, status: str, result: dict = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE id = ?",
                (status, json.dumps(result) if result else None, task_id)
            )
    
    def get_task(self, task_id: int) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "status": row["status"],
                "result": json.loads(row["result"]) if row["result"] else None
            }

# 在 main.py 中使用
task_manager = TaskManager(Path("data/tasks.db"))

@app.post("/api/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    task_id = task_manager.create_task()
    # ... 其余代码
```

---

#### 问题 2：API 端点直接操作数据库，未使用 KnowledgeBase 封装

**位置**：`api/main.py` 第 175-258 行

**当前代码**：
```python
@app.get("/api/videos")
async def get_videos(limit: int = 50, offset: int = 0):
    import sqlite3  # ❌ 直接在端点中导入
    
    with sqlite3.connect(kb.db_path) as conn:  # ❌ 直接使用 sqlite3
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM videos ...")
        # ...
```

**问题**：
- 代码重复（每个端点都要写数据库连接逻辑）
- 绕过 `KnowledgeBase` 类的封装
- 难以切换到 MySQL（需要修改所有端点）

**修复方案**：在 `KnowledgeBase` 类中添加查询方法

**修复代码**：
```python
# 在 knowledge_base.py 中添加方法
class KnowledgeBase:
    # ... 现有代码 ...
    
    def get_videos(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """获取视频列表。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM videos ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_video(self, video_id: int) -> dict | None:
        """获取视频详情。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
            row = cursor.fetchone()
            if not row:
                return None
            video = dict(row)
            video["tools"] = self.get_video_tools(video_id)
            if video.get("analysis_result"):
                video["analysis_result"] = json.loads(video["analysis_result"])
            return video
    
    def get_tools(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """获取工具列表。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tools ORDER BY name LIMIT ? OFFSET ?",
                (limit, offset)
            )
            tools = []
            for row in cursor.fetchall():
                tool = dict(row)
                for field in ["install_commands", "config_steps", "warnings", "alternatives"]:
                    if tool.get(field):
                        tool[field] = json.loads(tool[field])
                tools.append(tool)
            return tools
    
    def get_tool(self, tool_id: int) -> dict | None:
        """获取工具详情。"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,))
            row = cursor.fetchone()
            if not row:
                return None
            tool = dict(row)
            for field in ["install_commands", "config_steps", "warnings", "alternatives"]:
                if tool.get(field):
                    tool[field] = json.loads(tool[field])
            cursor = conn.execute(
                """SELECT v.* FROM videos v
                   JOIN video_tools vt ON v.id = vt.video_id
                   WHERE vt.tool_id = ?""",
                (tool_id,)
            )
            tool["videos"] = [dict(row) for row in cursor.fetchall()]
            return tool

# 在 api/main.py 中简化端点
@app.get("/api/videos")
async def get_videos(limit: int = 50, offset: int = 0):
    return {"videos": kb.get_videos(limit, offset)}  # ✅ 使用 KnowledgeBase

@app.get("/api/videos/{video_id}")
async def get_video(video_id: int):
    video = kb.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return video

@app.get("/api/tools")
async def get_tools(limit: int = 50, offset: int = 0):
    return {"tools": kb.get_tools(limit, offset)}

@app.get("/api/tools/{tool_id}")
async def get_tool(tool_id: int):
    tool = kb.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool
```

---

#### 问题 3：MySQL 实现已完成但未集成

**位置**：`database/mysql_db.py`（已实现），`api/main.py`（未使用）

**问题**：
- `database/mysql_db.py` 提供了完整的异步 MySQL 操作
- 但 `api/main.py` 仍然使用 SQLite
- 无法利用 MySQL 的高并发和性能优势

**修复方案**：创建统一的数据库接口，支持 SQLite 和 MySQL 切换

**修复代码**：
```python
# 创建 database/base.py - 统一接口
from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class DatabaseInterface(ABC):
    """数据库接口抽象类。"""
    
    @abstractmethod
    def add_video_analysis(self, url: str, platform: str, ...) -> int:
        pass
    
    @abstractmethod
    def get_videos(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_video(self, video_id: int) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def get_tools(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_tool(self, tool_id: int) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def search_videos(self, query: str, limit: int = 10) -> List[Dict]:
        pass
    
    @abstractmethod
    def search_tools(self, query: str, limit: int = 10) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict:
        pass

# SQLite 实现（现有 KnowledgeBase）
class SQLiteDatabase(DatabaseInterface):
    def __init__(self, db_path: Path):
        self.kb = KnowledgeBase(db_path)
    
    # 实现所有抽象方法，委托给 self.kb

# MySQL 实现
class MySQLDatabase(DatabaseInterface):
    def __init__(self, settings):
        self.pool = None
        self.settings = settings
    
    async def init_db(self):
        self.pool = await aiomysql.create_pool(...)
    
    # 实现所有抽象方法

# 在 api/main.py 中根据配置选择数据库
from database.base import DatabaseInterface

# 根据配置选择数据库类型
db_type = config.get("database", {}).get("type", "sqlite")

if db_type == "mysql":
    from database.mysql_db import MySQLDatabase
    db = MySQLDatabase(config["database"])
    await db.init_db()
else:
    from video_to_action.knowledge_base import KnowledgeBase
    db = KnowledgeBase()

# 所有端点使用 db 对象
@app.get("/api/videos")
async def get_videos(limit: int = 50, offset: int = 0):
    return {"videos": db.get_videos(limit, offset)}
```

---

### 🟡 功能缺失（P1）

#### 问题 4：缺少视频/工具的删除和更新接口

**缺失接口**：
- `DELETE /api/videos/{video_id}` - 删除视频
- `PUT /api/videos/{video_id}` - 更新视频
- `DELETE /api/tools/{tool_id}` - 删除工具
- `PUT /api/tools/{tool_id}` - 更新工具

**修复方案**：添加这些接口

**修复代码**：
```python
# 在 api/main.py 中添加
@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: int):
    """删除视频。"""
    with sqlite3.connect(kb.db_path) as conn:
        cursor = conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="视频不存在")
    return {"success": True, "message": "视频已删除"}

@app.put("/api/videos/{video_id}")
async def update_video(video_id: int, updates: dict):
    """更新视频信息。"""
    allowed_fields = ["theme", "summary", "title"]
    set_clauses = []
    params = []
    for field in allowed_fields:
        if field in updates:
            set_clauses.append(f"{field} = ?")
            params.append(updates[field])
    
    if not set_clauses:
        raise HTTPException(status_code=400, detail="没有可更新的字段")
    
    params.append(video_id)
    with sqlite3.connect(kb.db_path) as conn:
        conn.execute(
            f"UPDATE videos SET {', '.join(set_clauses)} WHERE id = ?",
            params
        )
    return {"success": True, "message": "视频已更新"}

# 工具的删除和更新接口类似
```

**前端补充**：在 `index.html` 中添加删除按钮
```javascript
// 在 viewVideo 函数的模态框中添加删除按钮
<button onclick="deleteVideo(${v.id})" class="text-red-400 hover:text-red-300">
    删除视频
</button>

async function deleteVideo(videoId) {
    if (!confirm('确定要删除这个视频吗？')) return;
    try {
        await axios.delete(`${API_BASE}/videos/${videoId}`);
        showToast('视频已删除', 'success');
        document.querySelector('.fixed').remove();  // 关闭模态框
        loadVideos();  // 重新加载列表
    } catch (error) {
        showToast('删除失败', 'error');
    }
}
```

---

#### 问题 5：分页功能不完整

**问题**：
- 后端支持 `limit` 和 `offset`，但不返回总记录数
- 前端无法实现完整的分页 UI（不知道总共有多少页）

**修复方案**：添加 `total` 字段

**修复代码**：
```python
# 在 api/main.py 中修改
@app.get("/api/videos")
async def get_videos(limit: int = 50, offset: int = 0):
    """获取视频列表。"""
    import sqlite3
    
    with sqlite3.connect(kb.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # 获取总记录数
        cursor = conn.execute("SELECT COUNT(*) as total FROM videos")
        total = cursor.fetchone()["total"]
        
        # 获取分页数据
        cursor = conn.execute(
            "SELECT * FROM videos ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        videos = [dict(row) for row in cursor.fetchall()]
    
    return {
        "videos": videos,
        "total": total,
        "limit": limit,
        "offset": offset
    }
```

**前端补充**：添加分页 UI
```javascript
// 在 loadVideos 函数中处理分页
let currentPage = 1;
const pageSize = 12;

async function loadVideos(page = 1) {
    currentPage = page;
    const offset = (page - 1) * pageSize;
    const response = await axios.get(`${API_BASE}/videos?limit=${pageSize}&offset=${offset}`);
    const { videos, total } = response.data;
    
    renderVideos(videos);
    renderPagination(total, page, pageSize);
}

function renderPagination(total, currentPage, pageSize) {
    const totalPages = Math.ceil(total / pageSize);
    const paginationDiv = document.getElementById('videos-pagination');
    
    paginationDiv.innerHTML = `
        <button onclick="loadVideos(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>上一页</button>
        <span>${currentPage} / ${totalPages}</span>
        <button onclick="loadVideos(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>下一页</button>
    `;
}
```

---

## 三、修复优先级和实施计划

### 优先级分类

| 优先级 | 问题 | 工作量 | 影响 |
|--------|------|--------|------|
| P0 | 任务状态持久化 | 2h | 高 - 影响核心功能 |
| P0 | API 端点使用 KnowledgeBase | 3h | 高 - 影响代码质量 |
| P0 | MySQL 集成 | 4h | 高 - 影响性能 |
| P1 | 添加删除/更新接口 | 2h | 中 - 影响功能完整性 |
| P1 | 分页功能完善 | 1h | 中 - 影响用户体验 |

### 实施步骤

#### 阶段 1：核心问题修复（第 1-2 天）
1. ✅ 修复任务状态持久化（问题 1）
2. ✅ 重构 API 端点，使用 KnowledgeBase 封装（问题 2）
3. ✅ 测试所有现有接口

#### 阶段 2：数据库升级（第 3-4 天）
1. ✅ 创建统一数据库接口（问题 3）
2. ✅ 实现 MySQL 适配层
3. ✅ 添加数据库配置选项
4. ✅ 测试 SQLite 和 MySQL 切换

#### 阶段 3：功能补充（第 5 天）
1. ✅ 添加删除/更新接口（问题 4）
2. ✅ 完善分页功能（问题 5）
3. ✅ 前端添加相应 UI

#### 阶段 4：测试和文档（第 6-7 天）
1. ✅ 编写单元测试
2. ✅ 编写 API 文档
3. ✅ 端到端测试

---

## 四、测试计划

### 4.1 单元测试

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_process_video():
    response = client.post("/api/process", json={
        "url": "https://www.youtube.com/watch?v=test",
        "level": "extract",
        "save_to_kb": False
    })
    assert response.status_code == 200
    assert "task_id" in response.json()["data"]

def test_get_videos():
    response = client.get("/api/videos?limit=10")
    assert response.status_code == 200
    assert "videos" in response.json()
    assert "total" in response.json()  # 分页修复后

def test_delete_video():
    # 先创建一个视频
    # 然后删除它
    # 确认删除成功
    pass
```

### 4.2 集成测试

```python
# tests/test_frontend_backend_integration.py
import asyncio
from playwright.async_api import async_playwright

async def test_process_video_flow():
    """测试完整的视频处理流程。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # 1. 打开前端页面
        await page.goto("<ADDRESS_REMOVED>")
        
        # 2. 输入视频 URL
        await page.fill("#video-url", "https://www.youtube.com/watch?v=test")
        
        # 3. 点击处理按钮
        await page.click("#process-btn")
        
        # 4. 等待任务完成
        await page.wait_for_selector("#processing-result", timeout=60000)
        
        # 5. 验证结果
        result = await page.text_content("#result-content")
        assert "theme" in result
        
        # 6. 检查视频库
        await page.click("#nav-videos")
        await page.wait_for_selector("#videos-list")
        videos = await page.query_selector_all(".video-card")
        assert len(videos) > 0
        
        await browser.close()
```

---

## 五、总结

### 5.1 已连接的功能
✅ 所有核心 API 接口都已实现并连接（8/8）

### 5.2 需要修复的问题
🔴 **3 个严重问题**：
1. 任务状态持久化
2. API 端点代码重复
3. MySQL 未集成

🟡 **2 个功能缺失**：
1. 删除/更新接口
2. 分页功能不完整

### 5.3 预期成果
修复后，系统将具备：
- ✅ 完整的视频处理流程（前端 → 后端 → 前端）
- ✅ 持久化的任务状态
- ✅ 可切换的数据库后端（SQLite/MySQL）
- ✅ 完整的 CRUD 功能
- ✅ 完善的分页和搜索

---

## 附录：完整的前端 API 调用代码

### A.1 processVideo 函数
```javascript
async function processVideo() {
    const url = document.getElementById('video-url').value.trim();
    if (!url) {
        showToast('请输入视频链接', 'warning');
        return;
    }
    
    const btn = document.getElementById('process-btn');
    btn.disabled = true;
    btn.textContent = '处理中...';
    
    try {
        // 调用后端 API
        const response = await axios.post(`${API_BASE}/process`, {
            url: url,
            level: currentLevel,
            save_to_kb: document.getElementById('save-to-kb').checked,
        });
        
        const taskId = response.data.data.task_id;
        // 开始轮询任务状态
        pollTaskStatus(taskId);
    } catch (error) {
        showToast('任务提交失败', 'error');
        btn.disabled = false;
    }
}
```

### A.2 pollTaskStatus 函数
```javascript
async function pollTaskStatus(taskId) {
    try {
        const response = await axios.get(`${API_BASE}/tasks/${taskId}`);
        const task = response.data;
        
        if (task.status === 'processing') {
            // 继续轮询
            setTimeout(() => pollTaskStatus(taskId), 2000);
        } else if (task.status === 'completed') {
            // 显示结果
            document.getElementById('result-content').textContent = 
                JSON.stringify(task.result, null, 2);
            showToast('视频处理完成', 'success');
        } else if (task.status === 'failed') {
            showToast('视频处理失败', 'error');
        }
    } catch (error) {
        // 继续轮询
        setTimeout(() => pollTaskStatus(taskId), 3000);
    }
}
```

---

**文档版本**：v1.0  
**生成时间**：2026-06-25  
**作者**：Senior Developer（高级开发工程师）
