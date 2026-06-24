"""视频下载模块，支持 yt-dlp 主方案和 GreenVideo 备选方案。"""

import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

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


class GreenVideoDownloader:
    """基于 GreenVideo 网站的备选视频下载器。"""

    def __init__(self, config: dict, output_dir: Path):
        """初始化 GreenVideo 下载器。

        Args:
            config: 项目配置字典，包含 platforms 中各平台的 greenvideo_url。
            output_dir: 视频输出目录。
        """
        self.config = config
        self.output_dir = output_dir

    def _get_platform_url(self, platform: str) -> str:
        """根据平台名称获取对应的 GreenVideo 解析入口 URL。"""
        platforms = self.config.get("platforms", {})
        return platforms.get(platform, {}).get("greenvideo_url", "")

    def _extract_download_url(self, page) -> str | None:
        """从 GreenVideo 解析结果页面提取视频下载链接。"""
        # 尝试多种常见选择器
        selectors = [
            "a[download]",
            "video source",
            ".download-link a",
            "a.btn-download",
            "button[data-url]",
        ]
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    if selector == "video source":
                        return element.get_attribute("src")
                    return element.get_attribute("href") or element.get_attribute("data-url")
            except Exception:
                continue
        return None

    def download(self, url: str, platform: str | None = None) -> dict:
        """使用 GreenVideo 网站下载视频。"""
        if platform is None:
            platform = detect_video_platform(url)
        platform_url = self._get_platform_url(platform)
        if not platform_url:
            return {
                "success": False,
                "platform": platform,
                "method": "greenvideo",
                "output_path": "",
                "stdout": "",
                "stderr": f"未配置 {platform} 的 GreenVideo URL",
            }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(platform_url, wait_until="domcontentloaded", timeout=30000)

                # 找到输入框并填入链接
                input_selectors = ["input[type='text']", "input[placeholder*='链接']", "input[placeholder*='URL']", "textarea"]
                filled = False
                for selector in input_selectors:
                    try:
                        page.locator(selector).first.fill(url)
                        filled = True
                        break
                    except Exception:
                        continue

                if not filled:
                    browser.close()
                    return {"success": False, "platform": platform, "method": "greenvideo", "output_path": "", "stdout": "", "stderr": "未找到输入框"}

                # 找到并点击解析按钮
                button_selectors = ["button:has-text('解析')", "button:has-text('下载')", "button[type='submit']", "a:has-text('解析')"]
                clicked = False
                for selector in button_selectors:
                    try:
                        page.locator(selector).first.click(timeout=5000)
                        clicked = True
                        break
                    except Exception:
                        continue

                if not clicked:
                    browser.close()
                    return {"success": False, "platform": platform, "method": "greenvideo", "output_path": "", "stdout": "", "stderr": "未找到解析按钮"}

                # 等待解析结果
                time.sleep(8)

                download_url = self._extract_download_url(page)
                browser.close()

                if not download_url:
                    return {"success": False, "platform": platform, "method": "greenvideo", "output_path": "", "stdout": "", "stderr": "未提取到下载链接"}

                # 下载视频
                import requests
                response = requests.get(download_url, timeout=60)
                response.raise_for_status()

                filename = f"{platform}_greenvideo_{int(time.time())}.mp4"
                output_path = self.output_dir / filename
                with open(output_path, "wb") as f:
                    f.write(response.content)

                return {
                    "success": True,
                    "platform": platform,
                    "method": "greenvideo",
                    "output_path": str(output_path),
                    "stdout": f"通过 GreenVideo 下载: {download_url}",
                    "stderr": "",
                }
        except Exception as e:
            return {
                "success": False,
                "platform": platform,
                "method": "greenvideo",
                "output_path": "",
                "stdout": "",
                "stderr": str(e),
            }


def download_video(url: str, config: dict, output_dir: Path) -> dict:
    """组合主方案和备选方案下载视频。"""
    # 先尝试 yt-dlp
    try:
        downloader = YtDlpDownloader(config, output_dir)
        result = downloader.download(url)
        if result["success"]:
            return result
    except Exception as e:
        result = {"success": False, "method": "yt-dlp", "stderr": str(e)}

    # yt-dlp 失败，尝试 GreenVideo
    fallback = config.get("download", {}).get("fallback")
    if fallback == "greenvideo":
        green = GreenVideoDownloader(config, output_dir)
        green_result = green.download(url)
        if green_result["success"]:
            return green_result
        return {
            "success": False,
            "platform": detect_video_platform(url),
            "method": "greenvideo",
            "output_path": "",
            "stdout": "",
            "stderr": f"yt-dlp 失败: {result.get('stderr', '')}; GreenVideo 失败: {green_result.get('stderr', '')}",
        }

    return result
