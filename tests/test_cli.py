"""
CLI 模块单元测试。

测试命令行入口的各项功能：
- 参数解析
- 主流程控制
- 知识库集成
- 错误处理
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_to_action.cli import parse_arguments


class TestParseArguments:
    """测试命令行参数解析。"""

    def test_parse_process_command(self):
        """测试解析 process 命令。"""
        argv = ["process", "https://www.douyin.com/video/123456"]
        args = parse_arguments(argv)
        assert args.command == "process"
        assert args.url == "https://www.douyin.com/video/123456"
        assert args.level == "auto"  # 默认值

    def test_parse_process_command_with_options(self):
        """测试解析 process 命令带选项。"""
        argv = [
            "process",
            "https://www.douyin.com/video/123456",
            "--level",
            "observe",
            "--config",
            "custom_config.yaml",
            "--output",
            "custom_output",
            "--save-to-kb",
            "--verbose",
        ]
        args = parse_arguments(argv)
        assert args.level == "observe"
        assert args.config == "custom_config.yaml"
        assert args.output == "custom_output"
        assert args.save_to_kb is True
        assert args.verbose is True

    def test_parse_kb_stats_command(self):
        """测试解析 kb-stats 命令。"""
        argv = ["kb-stats"]
        args = parse_arguments(argv)
        assert args.command == "kb-stats"

    def test_parse_invalid_level(self):
        """测试解析无效的自动化级别。"""
        argv = ["process", "https://example.com", "--level", "invalid"]
        with pytest.raises(SystemExit):
            parse_arguments(argv)


class TestCLIProcessFlow:
    """测试 CLI 主流程（mock 各模块）。"""

    @patch("video_to_action.cli_process.download_video")
    @patch("video_to_action.cli_process.Extractor")
    @patch("video_to_action.cli_process.AnalyzerV2")
    @patch("video_to_action.cli_process.Executor")
    @patch("video_to_action.cli_process.Reporter")
    def test_process_flow_success(self, mock_reporter, mock_executor, mock_analyzer, mock_extractor, mock_download):
        """测试完整流程成功。"""
        # Mock 下载
        mock_download.return_value = {
            "success": True,
            "platform": "douyin",
            "method": "yt-dlp",
            "output_path": "/path/to/video.mp4",
        }

        # Mock 提取
        mock_extractor_instance = MagicMock()
        mock_extractor_instance.transcribe.return_value = [{"start": 0, "end": 5, "text": "测试文本"}]
        mock_extractor_instance.extract_audio.return_value = Path("/path/to/audio.wav")
        mock_extractor.return_value = mock_extractor_instance

        # Mock 分析
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.analyze.return_value = {
            "theme": "测试",
            "summary": "测试摘要",
            "tools": [],
            "needs_credential": False,
            "is_paid": False,
            "alternative_tools": [],
        }
        mock_analyzer.return_value = mock_analyzer_instance

        # Mock 执行
        mock_executor_instance = MagicMock()
        mock_executor_instance.execute_plan.return_value = []
        mock_executor.return_value = mock_executor_instance

        # Mock 报告
        mock_reporter_instance = MagicMock()
        mock_reporter_instance.generate.return_value = "/path/to/report.md"
        mock_reporter.return_value = mock_reporter_instance

        # 运行主流程
        from video_to_action.cli import main

        with patch("sys.argv", ["cli.py", "process", "https://www.douyin.com/video/123456"]):
            exit_code = main()
            assert exit_code == 0


class TestCLIURLFormatSupport:
    """测试 CLI 对各种 URL 格式的支持。"""

    def test_douyin_short_url(self):
        """测试抖音短链格式。"""
        from video_to_action.downloader import detect_video_platform

        url = "https://v.douyin.com/iRNBho6/"
        platform = detect_video_platform(url)
        assert platform == "douyin"

    def test_douyin_video_url(self):
        """测试抖音 /video/ 格式。"""
        from video_to_action.downloader import detect_video_platform

        url = "https://www.douyin.com/video/7513843872540233023"
        platform = detect_video_platform(url)
        assert platform == "douyin"

    def test_douyin_modal_id_url(self):
        """测试抖音 modal_id 参数格式。"""
        from video_to_action.downloader import detect_video_platform

        url = "https://www.douyin.com/jingxuan/course?modal_id=7513843872540233023"
        platform = detect_video_platform(url)
        assert platform == "douyin"

    def test_bilibili_url(self):
        """测试 B站 URL 格式。"""
        from video_to_action.downloader import detect_video_platform

        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        platform = detect_video_platform(url)
        assert platform == "bilibili"

    def test_youtube_url(self):
        """测试 YouTube URL 格式。"""
        from video_to_action.downloader import detect_video_platform

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        platform = detect_video_platform(url)
        assert platform == "youtube"

    def test_unknown_url(self):
        """测试未知 URL 格式。"""
        from video_to_action.downloader import detect_video_platform

        url = "https://www.example.com/video/123"
        platform = detect_video_platform(url)
        assert platform == "unknown"
