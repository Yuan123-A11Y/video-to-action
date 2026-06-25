# Video-to-Action 数据库优化方案

## 📊 项目概述

本项目使用 MySQL 数据库替换原有的 SQLite，提供更好的性能、并发支持和可扩展性。

## 🗄️ 数据库架构

### 核心表结构

1. **videos** - 视频表
   - 存储视频元数据、转录文本、分析结果
   - 支持全文索引（标题、转录文本）
   - 状态追踪（pending/downloading/completed/failed）

2. **tools** - 工具表
   - 存储软件工具信息
   - JSON 字段存储安装命令、配置步骤
   - 支持全文搜索

3. **video_tools** - 视频-工具关联表
   - 多对多关系
   - 相关性评分

4. **download_jobs** - 下载任务表
   - 异步任务管理
   - 重试历史记录

5. **downloaded_videos** - 已下载视频表
   - 下载历史记录

6. **transcript_jobs** - 转录任务表
   - 转录任务状态管理

7. **system_config** - 系统配置表
   - 键值对配置存储

### 性能优化

- ✅ 所有常用查询字段都已添加索引
- ✅ 使用 InnoDB 引擎支持事务
- ✅ UTF8MB4 字符集支持 emoji
- ✅ 连接池管理（10 个连接）
- ✅ 异步操作（aiomysql）

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install aiomysql pydantic-settings
```

### 2. 配置 MySQL

复制 `.env.example` 为 `.env` 并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=video_to_action
```

### 3. 初始化数据库

```bash
python init_mysql.py
```

这会：
- 创建数据库（如果不存在）
- 执行 `database/schema.sql` 创建所有表
- 插入默认配置数据
- 验证安装结果

### 4. 迁移数据（可选）

如果你有现有的 SQLite 数据库：

```bash
python -m database.migrate_to_mysql
```

这会：
- 从 `data/knowledge_base.db` 迁移视频和工具数据
- 从 `data/dy_downloader.db` 迁移下载历史数据
- 自动处理 ID 映射关系

## 📚 使用示例

### 基本操作

```python
from database.mysql_db import Database, init_db, close_db
import asyncio

async def main():
    # 初始化连接池
    await init_db()
    
    try:
        # 创建视频记录
        video_id = await Database.create_video({
            "url": "https://example.com/video/123",
            "platform": "douyin",
            "title": "示例视频",
            "status": "pending"
        })
        
        # 查询视频
        video = await Database.get_video_by_id(video_id)
        print(video)
        
        # 列出视频（分页）
        videos, total = await Database.list_videos(page=1, size=20)
        print(f"Total: {total}, Videos: {len(videos)}")
        
    finally:
        await close_db()

asyncio.run(main())
```

### 高级查询

```python
# 按平台筛选
videos, _ = await Database.list_videos(
    platform="douyin",
    status="completed",
    page=1,
    size=10
)

# 关键词搜索
videos, _ = await Database.list_videos(
    keyword="教程",
    page=1,
    size=10
)

# 工具查询
tools, _ = await Database.list_tools(
    category="video-processing",
    is_paid=False,
    keyword="ffmpeg"
)
```

## 🔧 配置说明

### 环境变量（.env）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MYSQL_HOST` | MySQL 主机地址 | localhost |
| `MYSQL_PORT` | MySQL 端口 | 3306 |
| `MYSQL_USER` | 用户名 | root |
| `MYSQL_PASSWORD` | 密码 | - |
| `MYSQL_DATABASE` | 数据库名 | video_to_action |
| `MYSQL_POOL_SIZE` | 连接池大小 | 10 |

### 系统配置（数据库）

```python
# 获取配置
max_downloads = await Database.get_config("max_concurrent_downloads")
print(f"Max concurrent downloads: {max_downloads}")

# 设置配置
await Database.set_config(
    key="max_concurrent_downloads",
    value=5,
    config_type="integer",
    description="最大并发下载数"
)
```

## 📈 性能对比

### SQLite vs MySQL

| 指标 | SQLite | MySQL（优化后） |
|------|--------|---------------------|
| 并发连接 | 1（写锁） | 100+ |
| 适合场景 | 单机、小规模 | 多用户、大规模 |
| 全文搜索 | 有限 | 强大（全文索引） |
| 事务支持 | 有限 | 完整 ACID |
| 备份恢复 | 文件复制 | mysqldump |

## 🛠️ 维护命令

### 备份数据库

```bash
mysqldump -u root -p video_to_action > backup_$(date +%Y%m%d).sql
```

### 恢复数据库

```bash
mysql -u root -p video_to_action < backup_20240625.sql
```

### 优化表

```sql
OPTIMIZE TABLE videos;
OPTIMIZE TABLE tools;
ANALYZE TABLE videos;
```

## 📝 API 参考

### Database 类方法

#### Video 操作
- `create_video(data)` - 创建视频
- `get_video_by_id(id)` - 按 ID 获取
- `get_video_by_url(url)` - 按 URL 获取
- `update_video(id, data)` - 更新视频
- `delete_video(id)` - 删除视频
- `list_videos(...)` - 列出视频（分页+筛选）

#### Tool 操作
- `create_tool(data)` - 创建工具
- `get_tool_by_id(id)` - 按 ID 获取
- `get_tool_by_name(name)` - 按名称获取
- `update_tool(id, data)` - 更新工具
- `delete_tool(id)` - 删除工具
- `list_tools(...)` - 列出工具（分页+筛选）

#### Video-Tool 操作
- `link_video_tool(video_id, tool_id, score)` - 关联
- `unlink_video_tool(video_id, tool_id)` - 取消关联
- `get_tools_by_video(video_id)` - 获取视频的工具
- `get_videos_by_tool(tool_id)` - 获取工具的视频

#### Download Job 操作
- `create_download_job(data)` - 创建任务
- `update_download_job(id, data)` - 更新任务
- `get_download_job(id)` - 获取任务
- `list_download_jobs(...)` - 列出任务

#### System Config 操作
- `get_config(key)` - 获取配置
- `set_config(key, value, type, desc)` - 设置配置

## 🚨 故障排除

### 连接失败

```
Error: (2003, "Can't connect to MySQL server on 'localhost'")
```

**解决**：
1. 检查 MySQL 是否运行：`systemctl status mysql`
2. 检查端口：`netstat -an | grep 3306`
3. 检查防火墙设置

### 字符集错误

```
Error: (1366, "Incorrect string value")
```

**解决**：
1. 确保数据库使用 `utf8mb4`
2. 检查连接字符集：`SHOW VARIABLES LIKE 'character_set%';`

### 连接池耗尽

```
Error: Timeout acquiring connection from pool
```

**解决**：
1. 增加 `MYSQL_POOL_SIZE`
2. 检查连接是否正确关闭
3. 使用 `async with` 上下文管理器

## 📖 更多信息

- MySQL 文档：https://dev.mysql.com/doc/
- aiomysql 文档：https://aiomysql.readthedocs.io/
- 项目 README：../README.md

---

**作者**: Video-to-Action Team  
**更新**: 2026-06-25  
**版本**: 1.0.0
