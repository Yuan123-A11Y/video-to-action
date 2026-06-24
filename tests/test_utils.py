# g:\trae\video-to-action\tests\test_utils.py
from video_to_action.utils import (
    detect_platform,
    sanitize_filename,
    is_dangerous_command,
)


def test_detect_platform_douyin():
    """检测抖音相关 URL 的平台。"""
    assert detect_platform("https://v.douyin.com/abc123") == "douyin"
    assert detect_platform("https://www.douyin.com/video/123") == "douyin"


def test_detect_platform_bilibili():
    """检测哔哩哔哩相关 URL 的平台。"""
    assert detect_platform("https://www.bilibili.com/video/BV1xx411c7mD") == "bilibili"
    assert detect_platform("https://b23.tv/abc123") == "bilibili"


def test_detect_platform_youtube():
    """检测 YouTube 相关 URL 的平台。"""
    assert detect_platform("https://www.youtube.com/watch?v=abc123") == "youtube"
    assert detect_platform("https://youtu.be/abc123") == "youtube"


def test_detect_platform_unknown():
    """未知平台应返回 unknown。"""
    assert detect_platform("https://example.com/video") == "unknown"


def test_sanitize_filename():
    """清理文件名中的非法字符和空白。"""
    assert sanitize_filename("hello/world") == "hello_world"
    assert sanitize_filename("test:file") == "test_file"
    assert sanitize_filename("  spaced  ") == "spaced"


def test_is_dangerous_command():
    """识别包含危险关键字的命令。"""
    assert is_dangerous_command("rm -rf /") is True
    assert is_dangerous_command("format c:") is True
    assert is_dangerous_command("pip install requests") is False
