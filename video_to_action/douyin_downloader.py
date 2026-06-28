"""抖音视频下载器，基于 douyin-downloader 工具。"""

import asyncio
import os
import shutil
import sys
from pathlib import Path


class DouyinDownloader:
    """基于 douyin-downloader 的抖音视频下载器。

    使用项目内置的 tools/douyin-downloader 模块下载抖音视频，
    支持短链解析、无水印下载、Cookie 鉴权。
    """

    def __init__(self, config: dict, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
        self.dy_config = config.get("douyin_downloader", {})
        self._project_root = Path(__file__).parent.parent
        self._config_dir = self._project_root / "config"
        self._tool_root = self._resolve_tool_root()
        self._ensure_module_path()

    def _resolve_tool_root(self) -> Path:
        project_path = self.dy_config.get("project_path", "")
        if project_path:
            path = Path(project_path)
            if path.exists():
                return path
        return self._project_root / "tools" / "douyin-downloader"

    def _ensure_module_path(self) -> None:
        tool_root_str = str(self._tool_root)
        if tool_root_str not in sys.path:
            sys.path.insert(0, tool_root_str)

    def _resolve_config_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if path.is_absolute():
            return path
        config_relative = self._config_dir / path
        if config_relative.exists():
            return config_relative
        project_relative = self._project_root / path
        if project_relative.exists():
            return project_relative
        return config_relative

    def _load_cookies(self) -> dict[str, str]:
        raw_cookies = self.dy_config.get("cookies", {})
        if raw_cookies and isinstance(raw_cookies, dict):
            non_empty = {k: v for k, v in raw_cookies.items() if v}
            if non_empty:
                return non_empty

        default_cookie_file = self._config_dir / "douyin_cookies.txt"
        if default_cookie_file.exists():
            cookies = self._parse_netscape_cookies(default_cookie_file)
            if cookies:
                return cookies

        try:
            browser_cookies = self._load_cookies_from_browser("chrome")
            if browser_cookies:
                return browser_cookies
        except Exception:
            pass

        return {}

    def _parse_netscape_cookies(self, cookie_path: Path) -> dict[str, str]:
        cookies: dict[str, str] = {}
        if not cookie_path.exists():
            return cookies

        with open(cookie_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    name = parts[5]
                    value = parts[6]
                    if name:
                        cookies[name] = value
        return cookies

    def _load_cookies_from_browser(self, browser: str) -> dict[str, str]:
        """从浏览器导出 Cookie（使用 yt-dlp 的 --cookies-from-browser 功能导出到临时文件）。"""
        import tempfile

        tmp_cookie_file = None
        try:
            # 让 yt-dlp 将浏览器 Cookie 导出到临时 Netscape 格式文件
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
                tmp_cookie_file = tmp.name

            # 使用 yt-dlp 导出 Cookie 到文件
            # 注意：yt-dlp 本身不提供"仅导出 Cookie"的子命令，
            # 但可以通过 --cookies-from-browser 配合一次空下载来获取 Cookie 文件。
            # 这里采用更可靠的方式：直接用 http.cookiejar 读取浏览器 Cookie
            return self._extract_browser_cookies(browser)
        except Exception:
            return {}
        finally:
            if tmp_cookie_file:
                try:
                    Path(tmp_cookie_file).unlink(missing_ok=True)
                except Exception:
                    pass

    def _extract_browser_cookies(self, browser: str) -> dict[str, str]:
        """尝试用 browser_cookie3 库直接读取浏览器 Cookie。"""
        try:
            import browser_cookie3

            cj = getattr(browser_cookie3, browser, None)
            if cj is None:
                # 浏览器名称映射
                browser_map = {
                    "chrome": browser_cookie3.chrome,
                    "chromium": browser_cookie3.chromium,
                    "firefox": browser_cookie3.firefox,
                    "edge": browser_cookie3.edge,
                    "safari": browser_cookie3.safari,
                }
                cj = browser_map.get(browser)
            if cj is None:
                return {}
            cookie_jar = cj(domain_name=".douyin.com")
            return {c.name: c.value for c in cookie_jar}
        except ImportError:
            # browser_cookie3 未安装，静默失败
            return {}
        except Exception:
            return {}

    def download(self, url: str, filename: str | None = None) -> dict:
        platform = "douyin"
        try:
            # 检查是否已在事件循环中（如在 FastAPI background task 内调用）
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # 已在异步上下文中，用 run_in_executor 避免事件循环冲突
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self._async_download(url)).result(timeout=300)
            else:
                # 普通同步调用
                result = asyncio.run(self._async_download(url))
            if result["success"] and result.get("video_path"):
                video_path = Path(result["video_path"])
                if filename is None:
                    filename = f"{platform}_{video_path.stem}.mp4"
                dest_path = self.output_dir / filename
                self.output_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(video_path, dest_path)
                # 清理临时下载目录（防止磁盘泄漏）
                temp_dir = self.output_dir / "_douyin_temp"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                result["output_path"] = str(dest_path)
                return {
                    "success": True,
                    "platform": platform,
                    "method": "douyin-downloader",
                    "output_path": str(dest_path),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                }
            return {
                "success": False,
                "platform": platform,
                "method": "douyin-downloader",
                "output_path": "",
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", "下载失败"),
            }
        except Exception as e:
            return {
                "success": False,
                "platform": platform,
                "method": "douyin-downloader",
                "output_path": "",
                "stdout": "",
                "stderr": str(e),
            }

    async def _async_download(self, url: str) -> dict:
        from auth import CookieManager
        from control import RateLimiter, RetryHandler
        from core import DouyinAPIClient, DownloaderFactory, URLParser
        from storage import FileManager

        from config import ConfigLoader
        from utils.validators import is_short_url, normalize_short_url

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        cookies_dict = self._load_cookies()
        if not cookies_dict:
            stderr_parts.append("未找到可用的抖音 Cookies")

        temp_download_dir = self.output_dir / "_douyin_temp"
        temp_download_dir.mkdir(parents=True, exist_ok=True)

        dy_config_dict = {
            "path": str(temp_download_dir),
            "music": False,
            "cover": False,
            "avatar": False,
            "json": False,
            "folderstyle": False,
            "filename_template": "{id}",
            "folder_template": "{id}",
            "author_dir": "none",
            "mode": ["post"],
            "thread": self.dy_config.get("thread", 2),
            "retry_times": self.dy_config.get("retry_times", 3),
            "rate_limit": 2,
            "proxy": self.dy_config.get("proxy", ""),
            "database": False,
            "cookies": cookies_dict,
        }

        cookie_manager = CookieManager()
        cookie_manager.set_cookies(cookies_dict)

        file_manager = FileManager(dy_config_dict["path"])
        rate_limiter = RateLimiter(max_per_second=float(dy_config_dict["rate_limit"]))
        retry_handler = RetryHandler(max_retries=dy_config_dict["retry_times"])

        config_loader = ConfigLoader()
        config_loader.config.update(dy_config_dict)

        async with DouyinAPIClient(
            cookie_manager.get_cookies(),
            proxy=dy_config_dict.get("proxy") or None,
        ) as api_client:
            current_url = url
            if is_short_url(url):
                resolved_url = await api_client.resolve_short_url(normalize_short_url(url))
                if resolved_url:
                    current_url = resolved_url
                    stdout_parts.append(f"短链解析成功: {resolved_url}")
                else:
                    stderr_parts.append("短链解析失败")

            parsed = URLParser.parse(current_url)
            if not parsed:
                stderr_parts.append(f"URL 解析失败: {current_url}")
                return {
                    "success": False,
                    "stdout": "\n".join(stdout_parts),
                    "stderr": "\n".join(stderr_parts),
                }

            stdout_parts.append(f"URL 类型: {parsed['type']}")

            downloader = DownloaderFactory.create(
                parsed["type"],
                config_loader,
                api_client,
                file_manager,
                cookie_manager,
                rate_limiter=rate_limiter,
                retry_handler=retry_handler,
            )

            if not downloader:
                stderr_parts.append(f"未找到匹配的下载器: {parsed['type']}")
                return {
                    "success": False,
                    "stdout": "\n".join(stdout_parts),
                    "stderr": "\n".join(stderr_parts),
                }

            result = await downloader.download(parsed)
            stdout_parts.append(
                f"下载结果: 总计 {result.total}, 成功 {result.success}, " f"失败 {result.failed}, 跳过 {result.skipped}"
            )

            if result.success > 0:
                aweme_id = parsed.get("aweme_id", "")
                video_path = self._find_downloaded_video(temp_download_dir, aweme_id)
                if video_path:
                    stdout_parts.append(f"视频文件: {video_path}")
                    return {
                        "success": True,
                        "video_path": str(video_path),
                        "stdout": "\n".join(stdout_parts),
                        "stderr": "\n".join(stderr_parts),
                    }

            stderr_parts.append("未找到下载的视频文件")
            return {
                "success": False,
                "stdout": "\n".join(stdout_parts),
                "stderr": "\n".join(stderr_parts),
            }

    def _find_downloaded_video(self, search_dir: Path, aweme_id: str) -> Path | None:
        if not search_dir.exists():
            return None

        video_suffixes = {".mp4", ".webm", ".mkv", ".mov"}
        candidates: list[Path] = []

        for root, dirs, files in os.walk(search_dir):
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix.lower() in video_suffixes:
                    if aweme_id and aweme_id in fname:
                        return fpath
                    candidates.append(fpath)

        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return candidates[0]
        return None
