"""基于 GreenVideo 网站的备选视频下载器。"""

import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

from video_to_action.ytdlp_downloader import detect_video_platform


class GreenVideoDownloader:
    """基于 GreenVideo 网站的备选视频下载器。

    通过 Playwright 自动化访问 GreenVideo 解析页面，
    填入视频链接后提取下载地址，最终用 requests 下载视频文件。
    """

    def __init__(self, config: dict, output_dir: Path):
        self.config = config
        self.output_dir = output_dir

    def _get_platform_url(self, platform: str) -> str:
        platforms = self.config.get("platforms", {})
        return platforms.get(platform, {}).get("greenvideo_url", "")

    def _extract_download_url(self, page) -> str | None:
        """从 GreenVideo 解析结果页面提取视频下载链接。"""
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
                try:
                    page = browser.new_page()
                    page.goto(platform_url, wait_until="domcontentloaded", timeout=30000)

                    # 找到输入框并填入链接
                    input_selectors = [
                        "input[type='text']",
                        "input[placeholder*='链接']",
                        "input[placeholder*='URL']",
                        "textarea",
                    ]
                    filled = False
                    for selector in input_selectors:
                        try:
                            page.locator(selector).first.fill(url)
                            filled = True
                            break
                        except Exception:
                            continue

                    if not filled:
                        return {
                            "success": False,
                            "platform": platform,
                            "method": "greenvideo",
                            "output_path": "",
                            "stdout": "",
                            "stderr": "未找到输入框",
                        }

                    # 找到并点击解析按钮
                    button_selectors = [
                        "button:has-text('解析')",
                        "button:has-text('下载')",
                        "button[type='submit']",
                        "a:has-text('解析')",
                    ]
                    clicked = False
                    for selector in button_selectors:
                        try:
                            page.locator(selector).first.click(timeout=5000)
                            clicked = True
                            break
                        except Exception:
                            continue

                    if not clicked:
                        return {
                            "success": False,
                            "platform": platform,
                            "method": "greenvideo",
                            "output_path": "",
                            "stdout": "",
                            "stderr": "未找到解析按钮",
                        }

                    # 等待解析结果：优先等待下载链接出现，超时 15 秒
                    try:
                        page.wait_for_selector(
                            "a[download], video source, .download-link a, a.btn-download",
                            timeout=15000,
                        )
                    except Exception:
                        # 回退：等待固定时间（页面可能在渲染中）
                        time.sleep(3)

                    download_url = self._extract_download_url(page)

                    if not download_url:
                        return {
                            "success": False,
                            "platform": platform,
                            "method": "greenvideo",
                            "output_path": "",
                            "stdout": "",
                            "stderr": "未提取到下载链接",
                        }
                finally:
                    browser.close()

            # 下载视频（流式下载，避免大文件OOM）
            import uuid

            filename = f"{platform}_greenvideo_{uuid.uuid4().hex[:8]}.mp4"
            output_path = self.output_dir / filename
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # 构造请求头（携带 Referer 和 Cookie，部分站点需要）
            headers = {}
            platform_cfg = self.config.get("platforms", {}).get(platform, {})
            cfg_headers = platform_cfg.get("headers", {})
            if cfg_headers:
                headers.update(cfg_headers)
            # 如果没有配置 Referer，默认使用平台页面
            if "Referer" not in headers:
                headers["Referer"] = platform_cfg.get("greenvideo_url", platform_url)

            # 携带 Cookie（从 config 读取）
            cookies = {}
            raw_cookies = platform_cfg.get("cookies", {}).get("raw", {})
            if raw_cookies:
                cookies.update(raw_cookies)

            response = requests.get(
                download_url,
                timeout=60,
                stream=True,
                headers=headers or None,
                cookies=cookies or None,
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" in content_type:
                return {
                    "success": False,
                    "platform": platform,
                    "method": "greenvideo",
                    "output_path": "",
                    "stdout": "",
                    "stderr": "下载链接返回非视频内容（可能是解析失败）",
                }

            # 流式写入文件
            downloaded_size = 0
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

            # 检查文件大小（下载完成后检查）
            if downloaded_size < 10240:  # 10KB 阈值
                output_path.unlink(missing_ok=True)
                return {
                    "success": False,
                    "platform": platform,
                    "method": "greenvideo",
                    "output_path": "",
                    "stdout": "",
                    "stderr": "下载的文件过小，可能不是有效视频",
                }

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
