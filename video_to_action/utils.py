"""通用工具函数。"""

import logging
import re
from pathlib import Path

from rich.logging import RichHandler


# 平台检测规则
PLATFORM_PATTERNS = {
    "douyin": [r"douyin\.com", r"iesdouyin\.com", r"v\.douyin\.com"],
    "bilibili": [r"bilibili\.com", r"b23\.tv"],
    "youtube": [r"youtube\.com", r"youtu\.be"],
}


def detect_platform(url: str) -> str:
    """根据 URL 检测视频平台。"""
    url_lower = url.lower()
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url_lower):
                return platform
    return "unknown"


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符。"""
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", name)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned


def is_dangerous_command(
    command: str, forbidden_keywords: list[str] | None = None
) -> bool:
    """检查命令是否包含危险操作。"""
    if forbidden_keywords is None:
        forbidden_keywords = ["rm -rf /", "format", "del /f /s /q"]
    command_lower = command.lower()
    return any(keyword.lower() in command_lower for keyword in forbidden_keywords)


def ensure_dir(path: Path) -> Path:
    """确保目录存在，返回 Path 对象。"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging(
    level: int = logging.INFO,
    log_file: str | Path | None = None,
    rich_tracebacks: bool = True,
) -> None:
    """配置统一的日志系统。

    使用 rich 的 RichHandler 输出彩色日志到控制台，并可选将日志写入文件。

    Args:
        level: 日志级别，默认为 logging.INFO。传入 logging.DEBUG 可输出详细调试信息。
        log_file: 日志文件路径；为 None 时不写入文件。
        rich_tracebacks: 是否使用 rich 渲染异常回溯，默认为 True。
    """
    handlers: list[logging.Handler] = [
        RichHandler(rich_tracebacks=rich_tracebacks)
    ]

    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,  # 覆盖已有配置
    )


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger 实例。

    Args:
        name: logger 名称，通常为模块名（如 __name__）。

    Returns:
        配置好的 logger 实例。
    """
    return logging.getLogger(name)
