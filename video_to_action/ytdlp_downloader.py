"""基于 yt-dlp 的视频下载器，支持多平台和断点续传。"""

from pathlib import Path
from typing import Any

import yt_dlp
from rich.progress import BarColumn, DownloadColumn, Progress, TransferSpeedColumn

from video_to_action.exceptions import DownloadError
from video_to_action.utils import detect_platform


def detect_video_platform(url: str) -> str:
    """公开的视频平台检测函数，委托给 utils.detect_platform 处理。"""
    return detect_platform(url)


class YtDlpDownloader:
    """基于 yt-dlp Python API 的视频下载器。"""

    def __init__(self, config: dict, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
        self.download_config = config.get("download", {})
        self.platforms = self.download_config.get("platforms", {})
        self.headers = self.download_config.get("headers", {})
        self.cookies = self.download_config.get("cookies", {})
        self._check_dependency()

    def _check_dependency(self) -> None:
        # 检查 yt-dlp Python 包是否可用（类内部使用 Python API，非 CLI）
        try:
            import yt_dlp  # noqa: F401
        except ImportError:
            raise DownloadError(message="未找到 yt-dlp Python 包", suggestion="请先安装: pip install yt-dlp")

    def _platform_settings(self, url: str) -> tuple[dict[str, str], dict[str, Any]]:
        platform = detect_video_platform(url)
        platform_cfg = self.platforms.get(platform, {})

        # 请求头：全局 + 平台特定
        merged_headers = dict(self.headers)
        merged_headers.update(platform_cfg.get("headers", {}))

        # Cookie：优先使用平台特定配置，否则使用全局配置
        # 配置路径：download.cookies.<platform> 或 download.cookies
        cookies_config = self.download_config.get("cookies", {})
        platform_cookies = cookies_config.get(platform)

        if platform_cookies is not None:
            merged_cookies = dict(platform_cookies)
        else:
            # 如果没有平台特定配置，使用全局Cookie（如果有）
            if cookies_config and not any(k in cookies_config for k in ["douyin", "bilibili", "youtube"]):
                merged_cookies = dict(cookies_config)
            else:
                merged_cookies = {}

        return merged_headers, merged_cookies

    def _domain_for_url(self, url: str) -> str:
        platform = detect_video_platform(url)
        domain_map = {
            "douyin": ".douyin.com",
            "bilibili": ".bilibili.com",
            "youtube": ".youtube.com",
        }
        return domain_map.get(platform, ".douyin.com")

    def _write_raw_cookies_file(self, url: str, raw_cookies: dict[str, str]) -> Path | None:
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
        """构造 yt-dlp CLI 命令列表（供外部调用）。"""
        command = [
            "yt-dlp",
            "--no-warnings",
            "--no-check-certificates",
            "-f",
            "best[ext=mp4]/best",
            "--newline",
        ]

        headers, cookies = self._platform_settings(url)

        default_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        merged_headers = {"User-Agent": default_user_agent}
        merged_headers.update(headers)
        for key, value in merged_headers.items():
            command.extend(["--add-header", f"{key}:{value}"])

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

        command.extend(["-o", str(output_path), url])
        return command

    def _create_progress_bar(self) -> Progress:
        return Progress(
            "[bold blue]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            DownloadColumn(),
            TransferSpeedColumn(),
        )

    def _get_ydl_opts(self, output_path: Path) -> dict:
        default_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        return {
            "format": "best[ext=mp4]/best",
            "outtmpl": str(output_path),
            "no_warnings": True,
            "no_check_certificates": True,
            "newline": True,
            "user_agent": default_user_agent,
        }

    def _build_ydl_opts(self, url: str, output_path: Path) -> dict:
        ydl_opts = self._get_ydl_opts(output_path)

        headers, cookies = self._platform_settings(url)

        merged_headers = {"User-Agent": ydl_opts.get("user_agent", "")}
        merged_headers.update(headers)
        ydl_opts["http_headers"] = dict(merged_headers)

        raw_cookies = cookies.get("raw") or {}
        browser = cookies.get("browser")
        cookie_file = cookies.get("file")

        # 调试信息
        print(f"[yt-dlp] Cookie配置：raw={bool(raw_cookies)}, browser={browser}, file={cookie_file}")

        # 优先使用Cookie文件（Netscape格式）
        if cookie_file:
            cookie_path = Path(cookie_file)
            # 如果是相对路径，相对于项目根目录解析
            if not cookie_path.is_absolute():
                # 假设配置文件在 config/settings.yaml，项目根目录是其父目录的父目录
                project_root = Path(__file__).resolve().parent.parent
                cookie_path = project_root / cookie_file

            if cookie_path.exists():
                ydl_opts["cookiefile"] = str(cookie_path)
                print(f"[yt-dlp] 使用Cookie文件：{cookie_path}")
            else:
                print(f"[yt-dlp] 警告：Cookie文件不存在：{cookie_path}")

        # 其次使用原始Cookie（会写入临时文件）
        elif raw_cookies:
            raw_cookie_path = self._write_raw_cookies_file(url, raw_cookies)
            if raw_cookie_path:
                ydl_opts["cookiefile"] = str(raw_cookie_path)
                print(f"[yt-dlp] 使用原始Cookie（已写入：{raw_cookie_path}）")

        # 最后尝试从浏览器读取
        elif browser:
            ydl_opts["cookiesfrombrowser"] = (browser,)
            print(f"[yt-dlp] 从浏览器读取Cookie：{browser}")

        ydl_opts["continuedl"] = True
        ydl_opts["progress_hooks"] = []

        return ydl_opts

    def _is_complete_file(self, file_path: Path) -> bool:
        if not file_path.exists():
            return False
        return file_path.stat().st_size > 1024 * 1024

    def download(self, url: str, filename: str | None = None) -> dict:
        """使用 yt-dlp Python API 下载视频，支持 rich 进度条和断点续传。"""
        platform = detect_video_platform(url)
        if filename is None:
            filename = f"{platform}_%(id)s.%(ext)s"
        output_path = self.output_dir / filename

        # 断点续传检查
        existing_files = list(self.output_dir.glob(f"{platform}_*"))
        if existing_files:
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

        downloaded_path: Path | None = None

        with self._create_progress_bar() as progress:
            task = progress.add_task("[cyan]下载视频...", total=0)

            def progress_hook(d: dict) -> None:
                nonlocal downloaded_path
                if d["status"] == "downloading":
                    if task.total == 0:
                        total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                        progress.update(task.id, total=total_bytes)
                    downloaded = d.get("downloaded_bytes", 0)
                    progress.update(task.id, completed=downloaded)
                elif d["status"] == "finished":
                    filepath = d.get("filename", "")
                    if filepath:
                        downloaded_path = Path(filepath).resolve()
                    progress.update(task.id, completed=task.total or 1, total=task.total or 1)

            ydl_opts = self._build_ydl_opts(url, output_path)
            ydl_opts["progress_hooks"] = [progress_hook]

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

        if downloaded_path is None or not downloaded_path.exists():
            downloaded_path = self._find_latest_downloaded_file(platform, output_path)
        return {
            "success": downloaded_path.exists(),
            "platform": platform,
            "method": "yt-dlp",
            "output_path": str(downloaded_path),
            "stdout": "下载完成" if downloaded_path.exists() else "",
            "stderr": "" if downloaded_path.exists() else "未找到下载的文件",
        }

    def _find_latest_downloaded_file(self, platform: str, fallback_path: Path) -> Path:
        candidates = sorted(
            self.output_dir.glob(f"{platform}_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            if candidate.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov", ".avi"}:
                if candidate.exists():
                    return candidate.resolve()

        all_candidates = sorted(
            self.output_dir.glob("*.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for candidate in all_candidates:
            if candidate.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov", ".avi"}:
                return candidate.resolve()

        return fallback_path
