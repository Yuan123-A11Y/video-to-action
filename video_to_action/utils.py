"""通用工具函数。"""

import re
from pathlib import Path


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


def is_dangerous_command(command: str, forbidden_keywords: list[str] | None = None) -> bool:
    """检查命令是否包含危险操作。"""
    if forbidden_keywords is None:
        forbidden_keywords = ["rm -rf /", "format", "del /f /s /q"]
    command_lower = command.lower()
    return any(keyword.lower() in command_lower for keyword in forbidden_keywords)


def ensure_dir(path: Path) -> Path:
    """确保目录存在，返回 Path 对象。"""
    path.mkdir(parents=True, exist_ok=True)
    return path
