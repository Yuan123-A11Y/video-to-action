"""FastAPI 后端 - 提供 Web UI 所需的 API 接口。"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# 先定义 ROOT_DIR，再配置日志
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 加载 .env 环境变量（必须在其他导入之前，确保 JWT_SECRET 等配置可用）
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

# 配置日志（输出到文件 + 控制台）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(ROOT_DIR / 'api.log', encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加项目根目录到 Python 路径（已在上面完成，这里不需要重复）
# sys.path.insert(0, str(ROOT_DIR))  # 已在上面执行

from video_to_action.analyzer_v2 import AnalyzerV2
from video_to_action.config import get_output_dir, load_config
from video_to_action.downloader import download_video
from video_to_action.extractor import Extractor
from video_to_action.utils import detect_platform
from api.task_manager import TaskManager
from api.ws_manager import ws_manager
from api.cache import cached_response, invalidate_cache

# 导入认证路由
from api.auth.router import router as auth_router
from api.middleware.auth_middleware import AuthMiddleware, get_current_user_from_state, require_authenticated_user

app = FastAPI(title="Video-to-Action API", version="1.0.0")

# 添加认证中间件（必须在 CORS 中间件之后）
app.add_middleware(AuthMiddleware)

# 集成认证路由
app.include_router(auth_router, prefix="", tags=["authentication"])

# CORS 配置（生产环境应限制为前端域名）
# 从环境变量读取允许的来源，默认允许 localhost（开发环境）
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 添加认证中间件（必须在 CORS 中间件之后）
app.add_middleware(AuthMiddleware)

# 全局配置
config = load_config()

# 知识库实例（懒加载，使用工厂函数）
kb = None
kb_initialized = False


class _KBAccessor:
    """兼容性层：让 kb.xxx 自动转发到 get_kb().xxx。"""

    def __getattr__(self, name):
        return getattr(get_kb(), name)

    def __setattr__(self, name, value):
        setattr(get_kb(), name, value)


def get_kb():
    """获取知识库实例（懒加载，支持降级）。"""
    global kb, kb_initialized
    if kb is not None and not isinstance(kb, _KBAccessor):
        return kb

    if not kb_initialized:
        from video_to_action.knowledge_base_factory import create_knowledge_base
        kb = create_knowledge_base(fallback=True)
        kb_initialized = True

    return kb


# 创建兼容性层（让 kb.xxx 自动转发到 get_kb().xxx）
kb = _KBAccessor()


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
    task_id: str
    message: str


@app.get("/")
async def root():
    """API 根路径。"""
    return {
        "name": "Video-to-Action API",
        "version": "1.0.0",
        "endpoints": {
            "GET /health": "健康检查",
            "POST /api/process": "处理视频",
            "GET /api/tasks/{task_id}": "获取任务状态",
            "WS /ws/tasks/{task_id}": "WebSocket 实时进度推送",
            "GET /api/videos": "获取视频列表（分页）",
            "GET /api/videos/{video_id}": "获取视频详情",
            "PUT /api/videos/{video_id}": "更新视频信息",
            "DELETE /api/videos/{video_id}": "删除视频",
            "GET /api/tools": "获取工具列表（分页）",
            "GET /api/tools/{tool_id}": "获取工具详情",
            "PUT /api/tools/{tool_id}": "更新工具信息",
            "DELETE /api/tools/{tool_id}": "删除工具",
            "GET /api/search": "搜索知识库",
            "GET /api/stats": "获取统计信息",
        },
    }


@app.get("/health")
async def health_check():
    """健康检查端点。

    Returns:
        dict: 包含服务状态、版本、数据库状态的字典
    """
    from video_to_action.knowledge_base_factory import create_knowledge_base

    db_status = "connected"
    try:
        test_kb = create_knowledge_base(fallback=False)
        if test_kb is None:
            db_status = "disconnected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/process", response_model=ProcessResponse)
async def process_video(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """处理视频（异步）。"""
    # 前置校验：快速检测是否为有效视频链接
    url = request.url.strip()
    from video_to_action.ytdlp_downloader import detect_video_platform
    platform = detect_video_platform(url)

    # 检查URL中是否包含可识别的视频ID
    import re
    has_video_id = bool(
        re.search(r'modal_id=(\d{10,})', url) or
        re.search(r'/video/(\d{10,})', url) or
        re.search(r'(bilibili\.com|youtube\.com|youtu\.be|v\.douyin\.com|tiktok\.com)', url) or
        platform != "unknown"
    )

    # 如果是抖音用户主页等非视频页面，给出明确提示
    if '/user/' in url or '/profile' in url:
        return ProcessResponse(
            task_id="invalid",
            message="ERROR: 检测到用户主页链接，请提供具体的视频播放页链接（如分享中的视频URL）",
        )

    # 创建新任务
    task_id = task_manager.create_task()

    async def process_task():
        """后台处理任务（含 WebSocket 进度推送）。"""
        total_steps = 5
        tid = task_id
        tid_str = str(task_id)  # WS manager 的 key 是 str，需要显式转换

        try:
            # 更新任务状态为处理中 + 推送
            task_manager.update_task(tid, "processing")
            await push_status(tid_str, "processing")
            await asyncio.sleep(0.8)  # 等前端建 WS 连接（加长等待）

            # 步骤 1：下载视频 (0% → 20%)
            await push_progress(tid_str, step=1, total_steps=total_steps,
                              step_name="下载视频", message="正在从源站下载视频...", percentage=0)
            output_dir = get_output_dir(config)
            download_result = download_video(request.url, config, output_dir)

            if not download_result["success"]:
                logger.error(f"Task {tid} download failed: {download_result['stderr']}")
                task_manager.update_task(tid, "failed",
                    error="视频下载失败，请查看日志获取详细信息")
                await push_status(tid_str, "failed",
                    error="视频下载失败，请检查链接是否有效")
                return

            video_path = Path(download_result["output_path"])
            await push_progress(tid_str, step=1, total_steps=total_steps,
                              step_name="下载视频", message="视频下载完成", percentage=20)

            # 步骤 2：提取内容 (20% → 40%)
            await push_progress(tid_str, step=2, total_steps=total_steps,
                              step_name="内容提取", message="正在提取音频和关键帧...", percentage=25)
            extractor = Extractor(config, output_dir)

            # 使用平台策略处理（优先拉取字幕，失败则回退到 Whisper）
            from video_to_action.utils import detect_platform
            platform = detect_platform(request.url)
            await push_progress(tid_str, step=2, total_steps=total_steps,
                              step_name="内容提取", message=f"正在使用 {platform} 策略提取内容...", percentage=28)
            
            extracted = extractor.process_with_platform_strategy(video_path, platform, request.url)

            await push_progress(tid_str, step=2, total_steps=total_steps,
                              step_name="内容提取", message=f"内容提取完成（{len(extracted.get('text',''))} 字符）", percentage=40)

            # 步骤 3：分析内容 (40% → 70%)
            await push_progress(tid_str, step=3, total_steps=total_steps,
                              step_name="智能分析", message="AI 正在分析视频内容...", percentage=45)
            analyzer = AnalyzerV2(config)
            analyzer.set_video_context(video_url=request.url, video_path=str(video_path))
            frames = extracted.get("frames", [])
            
            # 获取元数据并传递给分析器
            metadata = extracted.get("metadata", {})
            
            plan = analyzer.analyze(
                extracted.get("text", ""),
                platform,
                frames=frames if frames else None,
                metadata=metadata if metadata else None,
            )
            await push_progress(tid_str, step=3, total_steps=total_steps,
                              step_name="智能分析", message="分析完成，生成操作方案...", percentage=70)

            # 步骤 4：保存到知识库 (70% → 90%)
            video_id = None
            if request.save_to_kb:
                await push_progress(tid_str, step=4, total_steps=total_steps,
                                  step_name="保存结果", message="正在保存到知识库...", percentage=75)
                # 从 LLM 结果或元数据中提取标题（优先级：plan.title > metadata.title > theme）
                video_title = plan.get("title") or (metadata or {}).get("title") or plan.get("theme", "")
                video_id = get_kb().add_video_analysis(
                    url=request.url,
                    platform=download_result["platform"],
                    title=video_title,
                    theme=plan.get("theme", ""),
                    summary=plan.get("summary", ""),
                    transcription_text=extracted.get("text", ""),
                    analysis_result=plan,
                )

                # 使缓存失效（新增了视频）
                invalidate_cache("api_cache:get_videos:*")
                invalidate_cache("api_cache:get_stats:*")

            await push_progress(tid_str, step=4, total_steps=total_steps,
                              step_name="保存结果", message="已保存到知识库", percentage=90)

            # 步骤 5：完成 (100%)
            task_manager.update_task(
                tid,
                "completed",
                result={
                    "video_id": video_id,
                    "theme": plan.get("theme"),
                    "summary": plan.get("summary"),
                    "tools": plan.get("tools", []),
                    "video_path": str(video_path),
                    "transcription_length": len(extracted.get("text", "")),
                    "frame_count": len(frames),
                }
            )
            await push_progress(tid_str, step=5, total_steps=total_steps,
                              step_name="处理完成", message="全部处理完成！", percentage=100)
            await push_status(tid_str, "completed")

        except Exception as e:
            logger.error(f"Task {tid} failed: {e}", exc_info=True)
            task_manager.update_task(tid, "failed",
                error="处理失败，请查看日志获取详细信息")
            await push_status(tid_str, "failed",
                error=str(e))
    
    background_tasks.add_task(process_task)
    return ProcessResponse(
        task_id=str(task_id),
        message=f"任务已提交，任务 ID：{task_id}",
    )


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: int):
    """获取任务状态（含进度信息，兼容前端轮询）。"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 返回格式兼容前端期望的数据结构（包含 progress 以支持轮询降级）
    response = {
        "status": task["status"],
        "result": task["result"],
        "error": task.get("error"),
        # 轮询模式下的进度信息：根据状态推断当前步骤
        "progress": None,
    }

    # 根据任务状态补充进度信息，让轮询模式下进度面板也能正常显示
    status = task["status"]
    if status == "pending":
        response["progress"] = {"step": 0, "total_steps": 5, "step_name": "等待处理", "message": "任务已提交，排队中...", "percentage": 0}
    elif status == "processing":
        # 尝试从 WS 管理器获取最新进度
        latest_progress = ws_manager.get_latest_progress(str(task_id))
        if latest_progress:
            response["progress"] = latest_progress
        else:
            response["progress"] = {"step": 1, "total_steps": 5, "step_name": "正在处理", "message": "任务执行中...", "percentage": 10}
    elif status == "completed":
        response["progress"] = {"step": 5, "total_steps": 5, "step_name": "处理完成", "message": "全部处理完成！", "percentage": 100}
    elif status == "failed":
        response["progress"] = {"step": 0, "total_steps": 5, "step_name": "处理失败", "message": task.get("error", "未知错误"), "percentage": 0}

    return response


@app.get("/api/tasks")
async def list_tasks(limit: int = 10, status_filter: str = ""):
    """列出最近的任务（用于前端自动恢复进度面板）。"""
    tasks = task_manager.get_all_tasks(limit=limit)
    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]
    return {"tasks": tasks}


@app.get("/api/search")
@cached_response(expire=10)  # 搜索结果缓存 10 秒（搜索查询通常唯一，短缓存即可）
async def search(query: str, type: str = "all", limit: int = 20):
    """搜索知识库（支持视频和工具）。"""
    videos = []
    tools = []
    if type in ("all", "video"):
        videos = kb.search_videos(query, limit=limit)
    if type in ("all", "tool"):
        tools = kb.search_tools(query, limit=limit)
    return {"videos": videos, "tools": tools, "total": len(videos) + len(tools)}


@app.get("/api/stats")
@cached_response(expire=300)  # 统计信息缓存 5 分钟
async def get_stats():
    """获取知识库统计信息。"""
    return kb.get_statistics()


@app.get("/api/videos")
@cached_response(expire=60)  # 视频列表缓存 60 秒
async def get_videos(limit: int = 50, offset: int = 0):
    """获取视频列表（带分页）。"""
    videos = kb.get_videos(limit, offset)
    total = kb.get_videos_count()
    return {"videos": videos, "total": total, "limit": limit, "offset": offset}


@app.get("/api/videos/{video_id}")
@cached_response(expire=60)  # 视频详情缓存 60 秒
async def get_video(video_id: int):
    """获取视频详情。"""
    video = kb.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return video


@app.get("/api/videos/{video_id}/analysis")
@cached_response(expire=300)  # 分析结果缓存 5 分钟
async def get_video_analysis(video_id: int):
    """获取视频分析结果。"""
    video = kb.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # Return analysis result from video object
    analysis_result = video.get("analysis_result")
    if not analysis_result:
        raise HTTPException(status_code=404, detail="分析结果不存在")

    return analysis_result


@app.get("/api/tools")
@cached_response(expire=60)  # 工具列表缓存 60 秒
async def get_tools(limit: int = 50, offset: int = 0):
    """获取工具列表（带分页）。"""
    tools = kb.get_tools(limit, offset)
    total = kb.get_tools_count()
    return {"tools": tools, "total": total, "limit": limit, "offset": offset}


@app.get("/api/tools/{tool_id}")
@cached_response(expire=60)  # 工具详情缓存 60 秒
async def get_tool(tool_id: int):
    """获取工具详情。"""
    tool = kb.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool


# ==================== 删除/更新接口 ====================

@app.delete("/api/videos/{video_id}")
async def delete_video(
    video_id: int,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """删除视频。"""
    if not kb.delete_video(video_id):
        raise HTTPException(status_code=404, detail="视频不存在")

    # 使缓存失效
    invalidate_cache("api_cache:get_videos:*")
    invalidate_cache("api_cache:get_video:*")
    invalidate_cache("api_cache:get_stats:*")

    return {"success": True, "message": "视频已删除"}


@app.put("/api/videos/{video_id}")
async def update_video(
    video_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """更新视频信息。"""
    if not kb.update_video(video_id, **data):
        raise HTTPException(status_code=404, detail="视频不存在或没有可更新的字段")

    # 使缓存失效
    invalidate_cache("api_cache:get_videos:*")
    invalidate_cache(f"api_cache:get_video:{video_id}*")
    invalidate_cache("api_cache:get_stats:*")

    return {"success": True, "message": "视频已更新"}


@app.delete("/api/tools/{tool_id}")
async def delete_tool(
    tool_id: int,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """删除工具。"""
    if not kb.delete_tool(tool_id):
        raise HTTPException(status_code=404, detail="工具不存在")

    # 使缓存失效
    invalidate_cache("api_cache:get_tools:*")
    invalidate_cache("api_cache:get_tool:*")
    invalidate_cache("api_cache:get_stats:*")

    return {"success": True, "message": "工具已删除"}


@app.put("/api/tools/{tool_id}")
async def update_tool(
    tool_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """更新工具信息。"""
    if not kb.update_tool(tool_id, **data):
        raise HTTPException(status_code=404, detail="工具不存在或没有可更新的字段")

    # 使缓存失效
    invalidate_cache("api_cache:get_tools:*")
    invalidate_cache(f"api_cache:get_tool:{tool_id}*")
    invalidate_cache("api_cache:get_stats:*")

    return {"success": True, "message": "工具已更新"}


# ==================== 批量处理接口 ====================

class BatchProcessRequest(BaseModel):
    urls: list[str]
    level: str = "auto"
    save_to_kb: bool = True


@app.post("/api/batch/process")
async def batch_process_videos(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """批量提交视频处理任务。"""
    task_ids = []
    for url in request.urls:
        url = url.strip()
        if not url:
            continue
        task_id = task_manager.create_task()
        task_ids.append({"url": url, "task_id": str(task_id)})

        # 为每个 URL 启动后台处理任务（复用 process_video 的逻辑）
        async def process_task(tid: str = task_id, video_url: str = url):
            total_steps = 5
            try:
                task_manager.update_task(tid, "processing")
                await push_status(tid_str, "processing")
                await asyncio.sleep(0.8)

                await push_progress(tid_str, step=1, total_steps=total_steps,
                                    step_name="下载视频", message="正在下载...", percentage=0)
                output_dir = get_output_dir(config)
                download_result = download_video(video_url, config, output_dir)

                if not download_result["success"]:
                    task_manager.update_task(tid, "failed", error="视频下载失败")
                    await push_status(tid_str, "failed", error="视频下载失败")
                    return

                video_path = Path(download_result["output_path"])
                await push_progress(tid_str, step=1, total_steps=total_steps,
                                    step_name="下载视频", message="下载完成", percentage=20)

                await push_progress(tid_str, step=2, total_steps=total_steps,
                                    step_name="内容提取", message="正在提取...", percentage=25)
                extractor = Extractor(config, output_dir)
                
                # 使用平台策略处理
                from video_to_action.utils import detect_platform
                platform = detect_platform(video_url)
                await push_progress(tid_str, step=2, total_steps=total_steps,
                                    step_name="内容提取", message=f"正在使用 {platform} 策略提取...", percentage=28)
                
                extracted = extractor.process_with_platform_strategy(video_path, platform, video_url)
                await push_progress(tid_str, step=2, total_steps=total_steps,
                                    step_name="内容提取", message="提取完成", percentage=40)

                await push_progress(tid_str, step=3, total_steps=total_steps,
                                    step_name="智能分析", message="AI 分析中...", percentage=45)
                analyzer = AnalyzerV2(config)
                analyzer.set_video_context(video_url=request.url, video_path=str(video_path))
                frames = extracted.get("frames", [])
                
                # 获取元数据并传递给分析器
                metadata = extracted.get("metadata", {})
                
                plan = analyzer.analyze(
                    extracted.get("text", ""),
                    platform,
                    frames=frames if frames else None,
                    metadata=metadata if metadata else None,
                )
                await push_progress(tid_str, step=3, total_steps=total_steps,
                                    step_name="智能分析", message="分析完成", percentage=70)

                if request.save_to_kb:
                    await push_progress(tid_str, step=4, total_steps=total_steps,
                                        step_name="保存结果", message="保存到知识库...", percentage=75)
                    # 从 LLM 结果或元数据中提取标题
                    batch_video_title = plan.get("title") or (metadata or {}).get("title") or plan.get("theme", "")
                    get_kb().add_video_analysis(
                        url=video_url,
                        platform=download_result["platform"],
                        title=batch_video_title,
                        theme=plan.get("theme", ""),
                        summary=plan.get("summary", ""),
                        transcription_text=extracted.get("text", ""),
                        analysis_result=plan,
                    )

                    # 使缓存失效（新增了视频）
                    invalidate_cache("api_cache:get_videos:*")
                    invalidate_cache("api_cache:get_stats:*")

                    await push_progress(tid_str, step=4, total_steps=total_steps,
                                        step_name="保存结果", message="已保存", percentage=90)

                task_manager.update_task(tid, "completed", result={
                    "theme": plan.get("theme"),
                    "summary": plan.get("summary"),
                    "tools": plan.get("tools", []),
                })
                await push_progress(tid_str, step=5, total_steps=total_steps,
                                    step_name="完成", message="处理完成", percentage=100)
                await push_status(tid_str, "completed")

            except Exception as e:
                logger.error(f"Batch task {tid} failed: {e}", exc_info=True)
                task_manager.update_task(tid, "failed", error=str(e))
                await push_status(tid_str, "failed", error=str(e))

        background_tasks.add_task(process_task)

    return {"task_ids": task_ids, "message": f"已提交 {len(task_ids)} 个任务"}


@app.get("/api/batch/status")
async def batch_status(task_ids: str = Query(...)):
    """查询批量任务状态（传入逗号分隔的 task_id 列表）。"""
    ids = [tid.strip() for tid in task_ids.split(",") if tid.strip()]
    results = []
    for tid in ids:
        try:
            tid_int = int(tid)
            task = task_manager.get_task(tid_int)
            results.append({
                "task_id": tid,
                "status": task["status"] if task else "not_found",
                "error": task.get("error") if task else None,
            })
        except (ValueError, KeyError):
            results.append({"task_id": tid, "status": "not_found"})
    return {"tasks": results}


# ==================== WebSocket 端点 ====================

@app.websocket("/ws/tasks/{task_id}")
async def websocket_task_progress(websocket: WebSocket, task_id: str):
    """
    WebSocket 端点 - 实时推送任务处理进度。

    协议：
      - 客户端发送 {"type": "ping"} → 服务端回复 {"type": "pong"}
      - 服务端主动推送：
        * {"type": "progress", "data": {step, total_steps, step_name, message, percentage}}
        * {"type": "status",  data": {status, error?}}
    """
    await ws_manager.connect(task_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws_manager.handle_ping(task_id, websocket)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(task_id, websocket)


# ==================== 进度推送辅助函数 ====================

async def push_progress(task_id: str, step: int, total_steps: int, step_name: str, message: str, percentage: int):
    """向任务的所有 WebSocket 连接推送进度更新。"""
    logger.info(f"🔍 push_progress: task={task_id}, step={step}/{total_steps}, {percentage}%, msg={message[:30]}")
    try:
        await ws_manager.broadcast_progress(
            task_id=task_id,
            step=step,
            total_steps=total_steps,
            step_name=step_name,
            message=message,
            percentage=percentage,
        )
    except Exception as e:
        logger.warning(f"Failed to push progress for task {task_id}: {e}")


async def push_status(task_id: str, status: str, error: Optional[str] = None):
    """推送任务状态变更。"""
    try:
        await ws_manager.broadcast_status(task_id=task_id, status=status, error=error)
    except Exception as e:
        logger.warning(f"Failed to push status for task {task_id}: {e}")


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
