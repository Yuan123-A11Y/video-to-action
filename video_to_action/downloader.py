"""视频下载模块，支持 yt-dlp 主方案和 GreenVideo 备选方案。"""

import shutil
import subprocess
from pathlib import Path

from video_to_action.utils import detect_platform


def detect_video_platform(url: str) -> str:
    """公开的视频平台检测函数，委托给 utils.detect_platform 处理。

    Args:
        url: 待检测的视频页面 URL。

    Returns:
        检测到的平台名称，如 "douyin"、"bilibili"、"youtube" 或 "unknown"。
    """
    return detect_platform(url)


class YtDlpDownloader:
    """基于 yt-dlp 命令行工具的视频下载器。"""

    def __init__(self, config: dict, output_dir: Path):
        """初始化下载器并校验 yt-dlp 依赖是否可用。

        Args:
            config: 项目配置字典，包含 download 相关参数。
            output_dir: 视频输出目录。

        Raises:
            EnvironmentError: 当系统未安装 yt-dlp 时抛出。
        """
        self.config = config
        self.output_dir = output_dir
        self._check_dependency()

    def _check_dependency(self) -> None:
        """检查 yt-dlp 命令是否存在于系统 PATH 中。"""
        if shutil.which("yt-dlp") is None:
            raise EnvironmentError("未找到 yt-dlp，请先安装: pip install yt-dlp")

    def _build_command(self, url: str, output_path: Path) -> list[str]:
        """构造 yt-dlp 下载命令列表。

        Args:
            url: 视频页面 URL。
            output_path: 视频保存路径。

        Returns:
            可直接传给 subprocess.run 的命令参数列表。
        """
        quality = self.config.get("download", {}).get("quality", "best")
        return [
            "yt-dlp",
            "--no-warnings",
            "--no-check-certificates",
            "-f", f"best[ext=mp4]/best",
            "--newline",
            "-o", str(output_path),
            url,
        ]

    def download(self, url: str, filename: str | None = None) -> dict:
        """使用 yt-dlp 下载指定 URL 的视频。

        Args:
            url: 视频页面 URL。
            filename: 输出文件名模板；为空时自动生成 "平台_%(id)s.%(ext)s"。

        Returns:
            包含下载结果的字典：success、platform、method、output_path、stdout、stderr。
        """
        platform = detect_video_platform(url)
        if filename is None:
            filename = f"{platform}_%(id)s.%(ext)s"
        output_path = self.output_dir / filename

        command = self._build_command(url, output_path)
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

        return {
            "success": result.returncode == 0,
            "platform": platform,
            "method": "yt-dlp",
            "output_path": str(output_path),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
