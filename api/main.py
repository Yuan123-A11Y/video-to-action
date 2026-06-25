"""FastAPI 后端 - 提供 Web UI 所需的 API 接口。"""

import sys
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from video_to_action.analyzer_v2 import AnalyzerV2
from video_to_action.config import get_output_dir, load_config
from video_to_action.downloader import download_video
from video_to_action.extractor import Extractor
from video_to_action.knowledge_base import KnowledgeBase
from api.task_manager import TaskManager

app = FastAPI(title="Video-to-Action API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局配置
config = load_config()

# 根据配置选择数据库类型
db_config = config.get("database", {})
if db_config.get("type") == "mysql":
    from video_to_action.mysql_knowledge_base import MySQLKnowledgeBase
    kb = MySQLKnowledgeBase(
        host=db_config.get("host", "localhost"),
        port=db_config.get("port", 3306),
        user=db_config.get("user", "root"),
        password=db_config.get("password", ""),
        database=db_config.get("database", "video_to_action"),
    )
    print("✅ 使用 MySQL 数据库")
else:
    kb = KnowledgeBase()
    print("✅ 使用 SQLite 数据库")

# 任务管理器（替换原来的内存存储）
data_dir = Path(config.get("output", {}).get("base_dir", "data"))
data_dir.mkdir(parents=True, exist_ok=True)
task_manager = TaskManager(data_dir / "tasks.db")


# 请求模型
class ProcessRequest(BaseModel):
    url: str
    level: str = "auto"
    save_to_kb: bool = True


class SearchRequest(BaseModel):
    query: str
    type: str = "video"  # video or tool
    limit: int = 10


# 响应模型
class ProcessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


@app.get("/")
async def root():
    """API 根路径。"""
    return {
        "name": "Video-to-Action API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/process": "处理视频",
            "GET /api/search": "搜索知识库",
            "GET /api/stats": "获取统计信息",
            "GET /api/videos": "获取视频列表",
            "GET /api/videos/{video_id}": "获取视频详情",
            "GET /api/tools": "获取工具列表",
        },
    }


@app.post("/api/process", response_model=ProcessResponse)
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    """处理视频（异步）。"""
    # 创建新任务
    task_id = task_manager.create_task()
    
    def process_task():
        """后台处理任务。"""
        try:
            # 更新任务状态为处理中
            task_manager.update_task(task_id, "processing")
            
            # 步骤 1：下载视频
            output_dir = get_output_dir(config)
            download_result = download_video(request.url, config, output_dir)
            
            if not download_result["success"]:
                task_manager.update_task(
                    task_id, 
                    "failed",
                    error=download_result["stderr"]
                )
                return
            
            video_path = Path(download_result["output_path"])
            
            # 步骤 2：提取内容
            extractor = Extractor(config, output_dir)
            extracted = extractor.process(video_path)
            
            # 步骤 3：分析内容
            analyzer = AnalyzerV2(config)
            frames = extracted.get("frames", [])
            plan = analyzer.analyze(
                extracted.get("text", ""),
                download_result["platform"],
                frames=frames if frames else None,
            )
            
            # 步骤 4：保存到知识库
            if request.save_to_kb:
                kb.add_video_analysis(
                    url=request.url,
                    platform=download_result["platform"],
                    title=None,
                    theme=plan.get("theme", ""),
                    summary=plan.get("summary", ""),
                    transcription_text=extracted.get("text", ""),
                    analysis_result=plan,
                )
            
            # 更新任务状态为完成
            task_manager.update_task(
                task_id,
                "completed",
                result={
                    "theme": plan.get("theme"),
                    "summary": plan.get("summary"),
                    "tools": plan.get("tools", []),
                    "video_path": str(video_path),
                    "transcription_length": len(extracted.get("text", "")),
                    "frame_count": len(frames),
                }
            )
            
        except Exception as e:
            # 更新任务状态为失败
            task_manager.update_task(task_id, "failed", error=str(e))
    
    background_tasks.add_task(process_task)
    return ProcessResponse(
        success=True,
        message=f"任务已提交，任务 ID：{task_id}",
        data={"task_id": task_id},
    )


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: int):
    """获取任务状态。"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 返回格式兼容前端期望的数据结构
    return {
        "status": task["status"],
        "result": task["result"],
        "error": task.get("error")
    }


@app.get("/api/search")
async def search(query: str, type: str = "video", limit: int = 10):
    """搜索知识库。"""
    if type == "video":
        results = kb.search_videos(query, limit=limit)
        return {"results": results}
    else:
        results = kb.search_tools(query, limit=limit)
        return {"results": results}


@app.get("/api/stats")
async def get_stats():
    """获取知识库统计信息。"""
    return kb.get_statistics()


@app.get("/api/videos")
async def get_videos(limit: int = 50, offset: int = 0):
    """获取视频列表（带分页）。"""
    videos = kb.get_videos(limit, offset)
    total = kb.get_videos_count()
    return {"videos": videos, "total": total, "limit": limit, "offset": offset}


@app.get("/api/videos/{video_id}")
async def get_video(video_id: int):
    """获取视频详情。"""
    video = kb.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return video


@app.get("/api/tools")
async def get_tools(limit: int = 50, offset: int = 0):
    """获取工具列表（带分页）。"""
    tools = kb.get_tools(limit, offset)
    total = kb.get_tools_count()
    return {"tools": tools, "total": total, "limit": limit, "offset": offset}


@app.get("/api/tools/{tool_id}")
async def get_tool(tool_id: int):
    """获取工具详情。"""
    tool = kb.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
