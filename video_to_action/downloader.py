"""视频下载模块兼容层。

重新导出各下载器类，保持向后兼容。
新代码建议直接导入对应模块：
  - from video_to_action.douyin_downloader import DouyinDownloader
  - from video_to_action.ytdlp_downloader import YtDlpDownloader, detect_video_platform
  - from video_to_action.greenvideo_downloader import GreenVideoDownloader
"""

import re
from pathlib import Path

from video_to_action.douyin_downloader import DouyinDownloader
from video_to_action.greenvideo_downloader import GreenVideoDownloader
from video_to_action.ytdlp_downloader import (
    YtDlpDownloader,
    detect_video_platform,
)

__all__ = [
    "DouyinDownloader",
    "YtDlpDownloader",
    "GreenVideoDownloader",
    "detect_video_platform",
    "download_video",
]


def _extract_video_id_from_url(url: str) -> str | None:
    """从 URL 中提取视频 ID。

    支持以下格式：
    - modal_id=XXX（抖音各种页面）
    - /video/XXX（通用格式）
    - 最后一段数字（兜底）

    返回视频 ID 字符串，或 None（无法提取时）。
    """
    # 方式 1：modal_id= 参数（至少 10 位数字）
    m = re.search(r"modal_id=(\d{10,})", url)
    if m:
        return m.group(1)

    # 方式 2：/video/ 路径（至少 10 位数字）
    m = re.search(r"/video/(\d{10,})", url)
    if m:
        return m.group(1)

    # 方式 3：URL 路径最后一段数字（至少 10 位，排除短链）
    m = re.search(r"/([0-9]{10,})(?:/|\?|$)", url)
    if m:
        return m.group(1)

    return None


def _check_existing_download(url: str, output_dir: Path) -> dict | None:
    """检查是否已存在完整下载文件，支持断点续传预检查。

    根据 URL 中的视频 ID 精确匹配已下载文件，避免不同视频之间误命中缓存。
    """
    platform = detect_video_platform(url)
    expected_video_id = _extract_video_id_from_url(url)
    video_suffixes = {".mp4", ".webm", ".mkv", ".mov", ".avi"}

    # 优先精确匹配：文件名中包含视频 ID
    if expected_video_id:
        exact_match = output_dir / f"{platform}_{expected_video_id}.mp4"
        if exact_match.exists() and exact_match.stat().st_size > 1024 * 1024:
            return {
                "success": True,
                "platform": platform,
                "method": "cached",
                "output_path": str(exact_match.resolve()),
                "stdout": f"找到已下载的文件（{exact_match.stat().st_size // 1024 // 1024}MB），跳过下载",
                "stderr": "",
            }

    # 兜底：按平台前缀查找（兼容性保留）
    candidates = sorted(
        output_dir.glob(f"{platform}_*"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.suffix.lower() in video_suffixes and candidate.exists():
            # 如果能提取视频 ID，则校验文件名是否包含该 ID
            if expected_video_id and expected_video_id not in candidate.name:
                continue  # 跳过不匹配的缓存文件
            file_size = candidate.stat().st_size
            if file_size > 1024 * 1024:
                return {
                    "success": True,
                    "platform": platform,
                    "method": "cached",
                    "output_path": str(candidate.resolve()),
                    "stdout": f"找到已下载的文件（{file_size // 1024 // 1024}MB），跳过下载",
                    "stderr": "",
                }

    return None


def download_video(url: str, config: dict, output_dir: Path) -> dict:
    """组合主方案和备选方案下载视频，支持断点续传。

    对于抖音 URL，优先使用 douyin-downloader；
    其他平台或抖音失败时，回退到 yt-dlp；
    最后尝试 GreenVideo（如配置）。

    断点续传：若输出目录中已存在完整文件，则直接返回，避免重复下载。
    """
    existing = _check_existing_download(url, output_dir)
    if existing:
        return existing

    platform = detect_video_platform(url)
    failure_messages: list[str] = []

    if platform == "douyin":
        try:
            dy_downloader = DouyinDownloader(config, output_dir)
            result = dy_downloader.download(url)
            if result["success"]:
                return result
            failure_messages.append(f"douyin-downloader 失败: {result.get('stderr', '')}")
        except Exception as e:
            failure_messages.append(f"douyin-downloader 异常: {e}")

    result = None  # 初始化，防止后续引用未定义
    try:
        downloader = YtDlpDownloader(config, output_dir)
        result = downloader.download(url)
        if result["success"]:
            return result
        failure_messages.append(f"yt-dlp 失败: {result.get('stderr', '')}")
    except Exception as e:
        result = {"success": False, "method": "yt-dlp", "stderr": str(e)}
        failure_messages.append(f"yt-dlp 异常: {e}")

    fallback = config.get("download", {}).get("fallback")
    if fallback == "greenvideo":
        try:
            green = GreenVideoDownloader(config, output_dir)
            green_result = green.download(url)
            if green_result["success"]:
                return green_result
            failure_messages.append(f"GreenVideo 失败: {green_result.get('stderr', '')}")
        except Exception as e:
            failure_messages.append(f"GreenVideo 异常: {e}")

    if result is None:
        return {
            "success": False,
            "platform": platform,
            "method": "unknown",
            "output_path": "",
            "stdout": "",
            "stderr": "; ".join(failure_messages) or "所有下载方案均失败",
        }

    result["platform"] = platform
    result["stderr"] = "; ".join(failure_messages) if failure_messages else result.get("stderr", "")
    return result
