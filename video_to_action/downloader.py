"""视频下载模块，支持 douyin-downloader（抖音）、yt-dlp 和 GreenVideo 备选方案。"""

import asyncio
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yt_dlp
from playwright.sync_api import sync_playwright
from rich.progress import BarColumn, DownloadColumn, Progress, TransferSpeedColumn

from video_to_action.utils import detect_platform


def detect_video_platform(url: str) -> str:
    """公开的视频平台检测函数，委托给 utils.detect_platform 处理。

    Args:
        url: 待检测的视频页面 URL。

    Returns:
        检测到的平台名称，如 "douyin"、"bilibili"、"youtube" 或 "unknown"。
    """
    return detect_platform(url)


class DouyinDownloader:
    """基于 douyin-downloader 的抖音视频下载器。

    使用项目内置的 tools/douyin-downloader 模块下载抖音视频，
    支持短链解析、无水印下载、Cookie 鉴权。
    """

    def __init__(self, config: dict, output_dir: Path):
        """初始化抖音下载器。

        Args:
            config: 项目配置字典，包含 douyin_downloader 相关参数。
            output_dir: 视频输出目录。
        """
        self.config = config
        self.output_dir = output_dir
        self.dy_config = config.get("douyin_downloader", {})
        self._project_root = Path(__file__).parent.parent
        self._config_dir = self._project_root / "config"
        self._tool_root = self._resolve_tool_root()
        self._ensure_module_path()

    def _resolve_tool_root(self) -> Path:
        """解析 douyin-downloader 工具根目录。

        优先使用配置中的 project_path，否则使用内置的 tools/douyin-downloader。

        Returns:
            douyin-downloader 工具根目录路径。
        """
        project_path = self.dy_config.get("project_path", "")
        if project_path:
            path = Path(project_path)
            if path.exists():
                return path
        return self._project_root / "tools" / "douyin-downloader"

    def _ensure_module_path(self) -> None:
        """将 douyin-downloader 目录加入 sys.path，确保模块可导入。"""
        tool_root_str = str(self._tool_root)
        if tool_root_str not in sys.path:
            sys.path.insert(0, tool_root_str)

    def _resolve_config_path(self, path_str: str) -> Path:
        """解析配置文件中的路径，支持相对路径（相对于配置目录）和绝对路径。

        Args:
            path_str: 配置文件中的路径字符串。

        Returns:
            解析后的绝对路径。
        """
        path = Path(path_str)
        if path.is_absolute():
            return path
        # 先尝试相对于配置目录
        config_relative = self._config_dir / path
        if config_relative.exists():
            return config_relative
        # 再尝试相对于项目根目录
        project_relative = self._project_root / path
        if project_relative.exists():
            return project_relative
        # 都不存在，返回配置目录下的路径（调用方会检查存在性）
        return config_relative

    def _load_cookies(self) -> dict[str, str]:
        """从配置中加载抖音 Cookies。

        优先级：配置中的 raw cookies > config/douyin_cookies.txt 文件 > 浏览器导入

        Returns:
            Cookie 键值对字典。
        """
        # 1. 优先从配置中的 raw cookies 加载
        raw_cookies = self.dy_config.get("cookies", {})
        if raw_cookies and isinstance(raw_cookies, dict):
            # 过滤掉空值
            non_empty = {k: v for k, v in raw_cookies.items() if v}
            if non_empty:
                return non_empty

        # 2. 从默认 cookie 文件加载
        default_cookie_file = self._config_dir / "douyin_cookies.txt"
        if default_cookie_file.exists():
            cookies = self._parse_netscape_cookies(default_cookie_file)
            if cookies:
                return cookies

        # 3. 尝试从浏览器导入
        try:
            browser_cookies = self._load_cookies_from_browser("chrome")
            if browser_cookies:
                return browser_cookies
        except Exception:
            pass

        return {}

    def _parse_netscape_cookies(self, cookie_path: Path) -> dict[str, str]:
        """解析 Netscape 格式的 Cookie 文件。

        Args:
            cookie_path: Cookie 文件路径。

        Returns:
            Cookie 键值对字典。
        """
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
        """从浏览器导入 Cookies（通过 yt-dlp 中转）。

        Args:
            browser: 浏览器名称（chrome/firefox/edge 等）。

        Returns:
            Cookie 键值对字典。
        """
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--cookies-from-browser",
                    browser,
                    "--print-json",
                    "--skip-download",
                    "https://www.douyin.com",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return {}
        except Exception:
            pass
        return {}

    def download(self, url: str, filename: str | None = None) -> dict:
        """使用 douyin-downloader 下载指定抖音视频。

        Args:
            url: 抖音视频 URL（支持短链）。
            filename: 输出文件名；为空时自动生成。

        Returns:
            包含下载结果的字典：success、platform、method、output_path、stdout、stderr。
        """
        platform = "douyin"
        try:
            result = asyncio.run(self._async_download(url))
            if result["success"] and result.get("video_path"):
                video_path = Path(result["video_path"])
                if filename is None:
                    filename = f"{platform}_{video_path.stem}.mp4"
                dest_path = self.output_dir / filename
                self.output_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(video_path, dest_path)
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
        """异步执行抖音视频下载。

        Args:
            url: 抖音视频 URL。

        Returns:
            下载结果字典。
        """
        from auth import CookieManager
        from config import ConfigLoader
        from control import RateLimiter, RetryHandler
        from core import DouyinAPIClient, DownloaderFactory, URLParser
        from storage import FileManager
        from utils.validators import is_short_url, normalize_short_url

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        # 加载 cookies
        cookies_dict = self._load_cookies()
        if not cookies_dict:
            stderr_parts.append("未找到可用的抖音 Cookies")

        # 构建 douyin-downloader 配置
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

        # 初始化组件
        cookie_manager = CookieManager()
        cookie_manager.set_cookies(cookies_dict)

        file_manager = FileManager(dy_config_dict["path"])
        rate_limiter = RateLimiter(max_per_second=float(dy_config_dict["rate_limit"]))
        retry_handler = RetryHandler(max_retries=dy_config_dict["retry_times"])

        # 创建 ConfigLoader 实例（用默认配置 + 我们的覆盖）
        config_loader = ConfigLoader()
        config_loader.config.update(dy_config_dict)

        async with DouyinAPIClient(
            cookie_manager.get_cookies(),
            proxy=dy_config_dict.get("proxy") or None,
        ) as api_client:
            # 解析短链
            current_url = url
            if is_short_url(url):
                resolved_url = await api_client.resolve_short_url(
                    normalize_short_url(url)
                )
                if resolved_url:
                    current_url = resolved_url
                    stdout_parts.append(f"短链解析成功: {resolved_url}")
                else:
                    stderr_parts.append("短链解析失败")

            # 解析 URL
            parsed = URLParser.parse(current_url)
            if not parsed:
                stderr_parts.append(f"URL 解析失败: {current_url}")
                return {
                    "success": False,
                    "stdout": "\n".join(stdout_parts),
                    "stderr": "\n".join(stderr_parts),
                }

            stdout_parts.append(f"URL 类型: {parsed['type']}")

            # 创建下载器
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

            # 执行下载
            result = await downloader.download(parsed)
            stdout_parts.append(
                f"下载结果: 总计 {result.total}, 成功 {result.success}, "
                f"失败 {result.failed}, 跳过 {result.skipped}"
            )

            if result.success > 0:
                # 找到下载的视频文件
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
        """在下载目录中查找下载的视频文件。

        Args:
            search_dir: 搜索目录。
            aweme_id: 视频 ID。

        Returns:
            找到的视频文件路径，未找到返回 None。
        """
        if not search_dir.exists():
            return None

        video_suffixes = {".mp4", ".webm", ".mkv", ".mov"}
        candidates: list[Path] = []

        for root, dirs, files in os.walk(search_dir):
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix.lower() in video_suffixes:
                    # 优先匹配包含 aweme_id 的文件
                    if aweme_id and aweme_id in fname:
                        return fpath
                    candidates.append(fpath)

        # 按修改时间排序，返回最新的
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return candidates[0]
        return None


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
        self.download_config = config.get("download", {})
        self.platforms = self.download_config.get("platforms", {})
        self.headers = self.download_config.get("headers", {})
        self.cookies = self.download_config.get("cookies", {})
        self._check_dependency()

    def _check_dependency(self) -> None:
        """检查 yt-dlp 命令是否存在于系统 PATH 中。"""
        if shutil.which("yt-dlp") is None:
            raise EnvironmentError("未找到 yt-dlp，请先安装: pip install yt-dlp")

    def _platform_settings(self, url: str) -> tuple[dict[str, str], dict[str, Any]]:
        """合并全局与平台级的 Headers/Cookies 配置。

        Args:
            url: 视频页面 URL。

        Returns:
            (merged_headers, merged_cookies) 元组。
        """
        platform = detect_video_platform(url)
        platform_cfg = self.platforms.get(platform, {})

        merged_headers = dict(self.headers)
        merged_headers.update(platform_cfg.get("headers", {}))

        # 平台级 Cookie 配置若存在则完全覆盖全局配置，确保平台可独立指定来源
        platform_cookies = platform_cfg.get("cookies")
        if platform_cookies is not None:
            merged_cookies = dict(platform_cookies)
        else:
            merged_cookies = dict(self.cookies)
        return merged_headers, merged_cookies

    def _domain_for_url(self, url: str) -> str:
        """根据 URL 返回用于 Netscape Cookie 文件的域。"""
        platform = detect_video_platform(url)
        domain_map = {
            "douyin": ".douyin.com",
            "bilibili": ".bilibili.com",
            "youtube": ".youtube.com",
        }
        return domain_map.get(platform, ".douyin.com")

    def _write_raw_cookies_file(
        self, url: str, raw_cookies: dict[str, str]
    ) -> Path | None:
        """将原始 Cookie 字典写入 yt-dlp 可用的 Netscape Cookie 文件。

        Args:
            url: 用于推断 Cookie 域的视频 URL。
            raw_cookies: Cookie 名称到值的映射。

        Returns:
            写入后的 Cookie 文件路径；若 raw_cookies 为空则返回 None。
        """
        if not raw_cookies:
            return None

        domain = self._domain_for_url(url)
        cookie_path = self.output_dir / "yt_dlp_cookies.txt"
        lines = ["# Netscape HTTP Cookie File\n"]
        for name, value in raw_cookies.items():
            if not name or value is None:
                continue
            lines.append(f"{domain}\tTRUE\t/\tFALSE\t0\t{name}\t{value}\n")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        cookie_path.write_text("".join(lines), encoding="utf-8")
        return cookie_path

    def _build_command(self, url: str, output_path: Path) -> list[str]:
        """构造 yt-dlp 下载命令列表。

        Args:
            url: 视频页面 URL。
            output_path: 视频保存路径。

        Returns:
            可直接传给 subprocess.run 的命令参数列表。
        """
        command = [
            "yt-dlp",
            "--no-warnings",
            "--no-check-certificates",
            "-f",
            "best[ext=mp4]/best",
            "--newline",
        ]

        headers, cookies = self._platform_settings(url)

        # 添加自定义请求头，绕过部分平台的反爬校验
        default_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        merged_headers = {"User-Agent": default_user_agent}
        merged_headers.update(headers)
        for key, value in merged_headers.items():
            command.extend(["--add-header", f"{key}:{value}"])

        # 添加 Cookie 支持：raw 字典 > 浏览器导入 > 文件导入
        raw_cookies = cookies.get("raw") or {}
        browser = cookies.get("browser")
        cookie_file = cookies.get("file")
        raw_cookie_path = self._write_raw_cookies_file(url, raw_cookies)
        if raw_cookie_path:
            command.extend(["--cookies", str(raw_cookie_path)])
        elif browser:
            command.extend(["--cookies-from-browser", browser])
        elif cookie_file:
            command.extend(["--cookies", str(Path(cookie_file).expanduser())])

        command.extend(
            [
                "-o",
                str(output_path),
                url,
            ]
        )
        return command

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

        # 使用 --print 获取 yt-dlp 实际写入的文件路径
        command = self._build_command(url, output_path) + [
            "--print",
            "after_move:filepath",
        ]
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8"
        )

        real_path = self._extract_real_path(result.stdout, output_path)
        return {
            "success": result.returncode == 0 and real_path.exists(),
            "platform": platform,
            "method": "yt-dlp",
            "output_path": str(real_path),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def _extract_real_path(self, stdout: str, fallback_path: Path) -> Path:
        """从 yt-dlp 输出中提取最终文件路径。

        yt-dlp 的 --print after_move:filepath 会在下载完成后输出真实路径。
        如果解析失败或文件不存在，则回退到模板路径或输出目录中最新匹配文件。
        """
        if stdout:
            for line in reversed(stdout.strip().splitlines()):
                line = line.strip()
                if line and not line.startswith("[") and Path(line).exists():
                    return Path(line).resolve()

        if fallback_path.exists():
            return fallback_path.resolve()

        # 回退：查找输出目录中最新创建的视频文件
        candidates = sorted(
            self.output_dir.glob("*.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            if candidate.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov", ".avi"}:
                return candidate.resolve()
        return fallback_path

    def _create_progress_bar(self) -> Progress:
        """创建 rich 进度条组件。

        Returns:
            配置好的 Progress 对象，显示任务描述、进度条、百分比、下载量和速度。
        """
        return Progress(
            "[bold blue]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            DownloadColumn(),
            TransferSpeedColumn(),
        )

    def _get_ydl_opts(self, output_path: Path) -> dict:
        """构造 yt-dlp Python API 选项字典。

        Args:
            output_path: 视频保存路径模板。

        Returns:
            yt-dlp 选项字典，包含格式、请求头、Cookie 等配置。
        """
        # 获取默认 User-Agent
        default_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )

        # 合并全局与平台级配置（使用第一个 URL 作为示例，实际应在 download 方法中传入）
        # 此处返回基础配置，Cookie/Header 需在调用处根据 URL 补充
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": str(output_path),
            "no_warnings": True,
            "no_check_certificates": True,
            "newline": True,
            "user_agent": default_user_agent,
        }
        return ydl_opts

    def _build_ydl_opts(self, url: str, output_path: Path) -> dict:
        """根据 URL 和输出路径构造完整的 yt-dlp 选项。

        Args:
            url: 视频页面 URL，用于推断平台和合并配置。
            output_path: 视频保存路径模板。

        Returns:
            完整的 yt-dlp 选项字典。
        """
        ydl_opts = self._get_ydl_opts(output_path)

        # 合并平台级 Headers 和 Cookies
        headers, cookies = self._platform_settings(url)

        # 设置请求头
        merged_headers = {"User-Agent": ydl_opts.get("user_agent", "")}
        merged_headers.update(headers)
        http_headers = {}
        for key, value in merged_headers.items():
            http_headers[key] = value
        ydl_opts["http_headers"] = http_headers

        # 设置 Cookie
        raw_cookies = cookies.get("raw") or {}
        browser = cookies.get("browser")
        cookie_file = cookies.get("file")

        # 写入原始 Cookie 文件
        raw_cookie_path = self._write_raw_cookies_file(url, raw_cookies)
        if raw_cookie_path:
            ydl_opts["cookiefile"] = str(raw_cookie_path)
        elif browser:
            ydl_opts["cookiesfrombrowser"] = (browser,)
        elif cookie_file:
            ydl_opts["cookiefile"] = str(Path(cookie_file).expanduser())

        # 启用断点续传
        ydl_opts["continuedl"] = True

        # 添加进度钩子（由调用方覆盖）
        ydl_opts["progress_hooks"] = []

        return ydl_opts

    def _is_complete_file(self, file_path: Path) -> bool:
        """检查文件是否完整。

        简单检查文件大小是否大于 1MB，避免误判。
        对于更严格的检查，可扩展为校验文件哈希或元数据。

        Args:
            file_path: 待检查的文件路径。

        Returns:
            文件存在且大小超过 1MB 时返回 True。
        """
        if not file_path.exists():
            return False
        return file_path.stat().st_size > 1024 * 1024

    def download(self, url: str, filename: str | None = None) -> dict:
        """使用 yt-dlp Python API 下载指定 URL 的视频，支持进度显示和断点续传。

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

        # 断点续传：检查目标文件是否已存在
        # 注意：由于 yt-dlp 的命名模板，实际文件名可能包含视频 ID
        # 此处做简单检查：查找输出目录中匹配平台的已下载文件
        existing_files = list(self.output_dir.glob(f"{platform}_*"))
        if existing_files:
            # 按修改时间排序，取最新的完整文件
            existing_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for candidate in existing_files:
                if candidate.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov"}:
                    if self._is_complete_file(candidate):
                        return {
                            "success": True,
                            "platform": platform,
                            "method": "yt-dlp",
                            "output_path": str(candidate),
                            "stdout": "文件已存在且完整，跳过下载",
                            "stderr": "",
                        }

        # 使用 rich 进度条下载
        with self._create_progress_bar() as progress:
            task = progress.add_task("[cyan]下载视频...", total=0)

            def progress_hook(d: dict) -> None:
                """yt-dlp 进度回调函数。"""
                if d["status"] == "downloading":
                    # 首次收到数据，设置总大小
                    if task.total == 0:
                        total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                        progress.update(task.id, total=total_bytes)
                    downloaded = d.get("downloaded_bytes", 0)
                    progress.update(task.id, completed=downloaded)
                elif d["status"] == "finished":
                    progress.update(task.id, completed=task.total or 1, total=task.total or 1)

            # 构造 yt-dlp 选项
            ydl_opts = self._build_ydl_opts(url, output_path)
            ydl_opts["progress_hooks"] = [progress_hook]

            # 添加 after_move 钩子以获取真实文件路径（通过 print 输出后解析）
            ydl_opts["print"] = [{"after_move": "filepath"}]

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                return {
                    "success": False,
                    "platform": platform,
                    "method": "yt-dlp",
                    "output_path": "",
                    "stdout": "",
                    "stderr": str(e),
                }

        # 下载完成后，查找实际输出文件
        # yt-dlp 会将文件路径输出到 stdout，但 Python API 中需通过其他方式获取
        # 此处采用回退策略：查找输出目录中最新创建的文件
        real_path = self._find_latest_downloaded_file(platform, output_path)
        return {
            "success": real_path.exists(),
            "platform": platform,
            "method": "yt-dlp",
            "output_path": str(real_path),
            "stdout": "下载完成" if real_path.exists() else "",
            "stderr": "" if real_path.exists() else "未找到下载的文件",
        }

    def _find_latest_downloaded_file(self, platform: str, fallback_path: Path) -> Path:
        """查找最新下载的视频文件。

        Args:
            platform: 视频平台名称，用于筛选文件。
            fallback_path: 回退路径模板。

        Returns:
            最新视频文件的绝对路径；未找到时返回 fallback_path。
        """
        # 优先查找匹配平台的文件
        candidates = sorted(
            self.output_dir.glob(f"{platform}_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            if candidate.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov", ".avi"}:
                if candidate.exists():
                    return candidate.resolve()

        # 回退：查找输出目录中所有视频文件
        all_candidates = sorted(
            self.output_dir.glob("*.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for candidate in all_candidates:
            if candidate.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov", ".avi"}:
                return candidate.resolve()

        return fallback_path


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
                    return element.get_attribute("href") or element.get_attribute(
                        "data-url"
                    )
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
                    page.goto(
                        platform_url, wait_until="domcontentloaded", timeout=30000
                    )

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

                    # 等待解析结果
                    time.sleep(8)

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

                # 下载视频
                import requests

                response = requests.get(download_url, timeout=60)
                response.raise_for_status()

                # 校验响应内容类型和大小，避免写入错误页面
                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" in content_type or len(response.content) < 1024:
                    return {
                        "success": False,
                        "platform": platform,
                        "method": "greenvideo",
                        "output_path": "",
                        "stdout": "",
                        "stderr": "下载链接返回非视频内容",
                    }

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


def _check_existing_download(url: str, output_dir: Path) -> dict | None:
    """检查是否已存在完整下载文件，支持断点续传预检查。

    根据 URL 平台查找输出目录中已有的视频文件，若存在完整文件则直接返回，
    避免重复下载。

    Args:
        url: 视频页面 URL，用于推断平台。
        output_dir: 视频输出目录。

    Returns:
        若找到完整文件，返回成功结果字典；否则返回 None。
    """
    platform = detect_video_platform(url)
    video_suffixes = {".mp4", ".webm", ".mkv", ".mov", ".avi"}

    # 按修改时间降序查找匹配平台的最新完整文件
    candidates = sorted(
        output_dir.glob(f"{platform}_*"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.suffix.lower() in video_suffixes and candidate.exists():
            file_size = candidate.stat().st_size
            if file_size > 1024 * 1024:  # 大于 1MB 视为完整
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
    # 断点续传预检查：若已存在完整文件，直接返回
    existing = _check_existing_download(url, output_dir)
    if existing:
        return existing

    platform = detect_video_platform(url)
    failure_messages: list[str] = []

    # 抖音优先使用 douyin-downloader
    if platform == "douyin":
        try:
            dy_downloader = DouyinDownloader(config, output_dir)
            result = dy_downloader.download(url)
            if result["success"]:
                return result
            failure_messages.append(f"douyin-downloader 失败: {result.get('stderr', '')}")
        except Exception as e:
            failure_messages.append(f"douyin-downloader 异常: {e}")

    # 尝试 yt-dlp
    try:
        downloader = YtDlpDownloader(config, output_dir)
        result = downloader.download(url)
        if result["success"]:
            return result
        failure_messages.append(f"yt-dlp 失败: {result.get('stderr', '')}")
    except Exception as e:
        result = {"success": False, "method": "yt-dlp", "stderr": str(e)}
        failure_messages.append(f"yt-dlp 异常: {e}")

    # yt-dlp 失败，尝试 GreenVideo
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

    # 返回最后一次失败结果
    result["platform"] = platform
    result["stderr"] = "; ".join(failure_messages) if failure_messages else result.get("stderr", "")
    return result
