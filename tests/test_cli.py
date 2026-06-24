# g:\trae\video-to-action\tests\test_cli.py
"""命令行入口测试。"""

from video_to_action.cli import parse_arguments


def test_parse_arguments():
    """测试默认参数解析。"""
    args = parse_arguments(["https://v.douyin.com/abc123"])
    assert args.url == "https://v.douyin.com/abc123"
    assert args.level == "auto"


def test_parse_arguments_with_level():
    """测试指定 level 参数。"""
    args = parse_arguments(["https://v.douyin.com/abc123", "--level", "observe"])
    assert args.level == "observe"
