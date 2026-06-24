# g:\trae\video-to-action\tests\test_reporter.py
from pathlib import Path

from video_to_action.reporter import Reporter


def test_reporter_generates_markdown():
    """测试报告生成器能够生成中文 Markdown 报告。"""
    config = {}
    reporter = Reporter(config, output_dir=Path("outputs"))
    context = {
        "video_url": "https://v.douyin.com/abc",
        "platform": "douyin",
        "download_method": "yt-dlp",
        "video_path": "outputs/douyin_123.mp4",
        "plan": {
            "theme": "测试主题",
            "summary": "这是一个测试摘要",
            "tools": [{"name": "test-tool", "purpose": "测试工具"}],
        },
        "execution_results": [
            {"success": True, "command": "echo hello", "stdout": "hello", "stderr": ""}
        ],
    }
    report_path = reporter.generate(context)
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "测试主题" in content
    assert "test-tool" in content
