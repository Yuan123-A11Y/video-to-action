# g:\trae\video-to-action\tests\test_integration.py
"""流水线集成测试。"""

from unittest.mock import MagicMock, patch

from video_to_action.cli import main


def test_cli_observe_mode_short_circuits_execution():
    """观察模式应在分析后结束，不执行命令。"""
    with (
        patch("video_to_action.cli.download_video") as mock_download,
        patch("video_to_action.cli.Extractor") as MockExtractor,
        patch("video_to_action.analyzer.Analyzer") as MockAnalyzer,
        patch("video_to_action.cli.load_config") as mock_load_config,
    ):
        # Mock 配置
        mock_load_config.return_value = {
            "automation_level": "observe",
            "max_retries": 3,
            "output_dir": "outputs",
            "download": {"primary": "douyin-downloader", "fallback": "yt-dlp"},
            "llm": {"provider": "mock"},
            "safety": {"forbidden_keywords": [], "require_confirm": []},
        }
        mock_download.return_value = {
            "success": True,
            "platform": "douyin",
            "method": "yt-dlp",
            "output_path": "outputs/douyin_test.mp4",
        }
        mock_extractor = MagicMock()
        mock_extractor.process.return_value = {
            "text": "这是一个测试视频",
            "segments": [],
            "frames": [],
        }
        MockExtractor.return_value = mock_extractor
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "theme": "测试",
            "summary": "测试摘要",
            "tools": [],
        }
        MockAnalyzer.return_value = mock_analyzer

        exit_code = main(["process", "https://v.douyin.com/abc123", "--level", "observe"])
        assert exit_code == 0
