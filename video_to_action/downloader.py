"""视频下载模块兼容层。

重新导出各下载器类，保持向后兼容。
新代码建议直接导入对应模块：
  - from video_to_action.douyin_downloader import DouyinDownloader
  - from video_to_action.ytdlp_downloader import YtDlpDownloader, detect_video_platform
  - from video_to_action.greenvideo_downloader import GreenVideoDownloader
"""

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


def _check_existing_download(url: str, output_dir: Path) -> dict | None:
    """检查是否已存在完整下载文件，支持断点续传预检查。

    根据 URL 平台查找输出目录中已有的视频文件，若存在完整文件则直接返回，
    避免重复下载。
    """

    platform = detect_video_platform(url)
    video_suffixes = {".mp4", ".webm", ".mkv", ".mov", ".avi"}

    candidates = sorted(
        output_dir.glob(f"{platform}_*"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.suffix.lower() in video_suffixes and candidate.exists():
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
        green = GreenVideoDownloader(config, output_dir)
        green_result = green.download(url)
        if green_result["success"]:
            return green_result
        failure_messages.append(f"GreenVideo 失败: {green_result.get('stderr', '')}")
        return {
            "success": False,
            "platform": platform,
            "method": "greenvideo",
            "output_path": "",
            "stdout": "",
            "stderr": "; ".join(failure_messages),
        }

    result["platform"] = platform
    result["stderr"] = "; ".join(failure_messages) if failure_messages else result.get("stderr", "")
    return result
