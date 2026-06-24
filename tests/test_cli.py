# g:\trae\video-to-action\tests\test_cli.py
"""命令行入口测试。"""

from video_to_action.cli import _format_trae_prompt, parse_arguments


def test_parse_arguments():
    """测试默认参数解析。"""
    args = parse_arguments(["https://v.douyin.com/abc123"])
    assert args.url == "https://v.douyin.com/abc123"
    assert args.level == "auto"


def test_parse_arguments_with_level():
    """测试指定 level 参数。"""
    args = parse_arguments(["https://v.douyin.com/abc123", "--level", "observe"])
    assert args.level == "observe"


def test_parse_arguments_with_extract_level():
    """测试 extract 模式参数解析。"""
    args = parse_arguments(["https://v.douyin.com/abc123", "--level", "extract"])
    assert args.level == "extract"


def test_format_trae_prompt_contains_text_and_platform():
    """测试 Trae Prompt 包含转录文本和平台信息。"""
    extracted = {"text": "这是一个测试视频", "frames": []}
    prompt = _format_trae_prompt(extracted, "抖音")
    assert "这是一个测试视频" in prompt
    assert "抖音" in prompt
    assert "JSON" in prompt
