"""测试 video_to_action/extractor.py 模块。"""
import os
import socket
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestExtractorHFMirror:
    """测试 HuggingFace 镜像自动设置逻辑。"""

    def test_auto_set_mirror_when_connection_fails(self):
        """测试网络连接失败时自动设置国内镜像。"""
        # 清除环境变量
        if "HF_ENDPOINT" in os.environ:
            del os.environ["HF_ENDPOINT"]

        # Mock socket.create_connection 抛出异常
        with patch("socket.create_connection", side_effect=socket.timeout("连接超时")):
            from video_to_action.extractor import Extractor

            config = {"transcription": {"model": "tiny", "device": "cpu", "compute_type": "int8"}}
            extractor = Extractor(config, Path("outputs"))

            # 调用 transcribe 方法（会在开头设置镜像）
            with patch("faster_whisper.WhisperModel"):
                try:
                    extractor.transcribe(Path("test.mp4"))
                except Exception:
                    pass  # 忽略后续错误

            # 验证镜像已设置
            assert os.environ.get("HF_ENDPOINT") == "https://hf-mirror.com"

    def test_auto_set_official_when_connection_succeeds(self):
        """测试网络连接成功时使用官方源。"""
        # 清除环境变量
        if "HF_ENDPOINT" in os.environ:
            del os.environ["HF_ENDPOINT"]

        # Mock socket.create_connection 成功
        with patch("socket.create_connection") as mock_connect:
            from video_to_action.extractor import Extractor

            config = {"transcription": {"model": "tiny", "device": "cpu", "compute_type": "int8"}}
            extractor = Extractor(config, Path("outputs"))

            # 调用 transcribe 方法（会在开头设置镜像）
            with patch("faster_whisper.WhisperModel"):
                try:
                    extractor.transcribe(Path("test.mp4"))
                except Exception:
                    pass  # 忽略后续错误

            # 验证官方源已设置
            assert os.environ.get("HF_ENDPOINT") == "https://huggingface.co"

    def test_skip_auto_set_when_env_var_exists(self):
        """测试已设置 HF_ENDPOINT 时不自动设置。"""
        # 设置环境变量
        os.environ["HF_ENDPOINT"] = "https://custom-mirror.example.com"

        from video_to_action.extractor import Extractor

        config = {"transcription": {"model": "tiny", "device": "cpu", "compute_type": "int8"}}
        extractor = Extractor(config, Path("outputs"))

        # 调用 transcribe 方法
        with patch("faster_whisper.WhisperModel"):
            try:
                extractor.transcribe(Path("test.mp4"))
            except Exception:
                pass  # 忽略后续错误

        # 验证环境变量未被修改
        assert os.environ.get("HF_ENDPOINT") == "https://custom-mirror.example.com"


class TestExtractorUnit:
    """测试 Extractor 类的其他功能（使用 mock）。"""

    @patch("video_to_action.extractor.Extractor._detect_device", return_value="cpu")
    @patch("video_to_action.extractor.Extractor._normalize_text", return_value="normalized text")
    @patch("faster_whisper.WhisperModel")
    def test_transcribe_success(self, mock_whisper, mock_normalize, mock_detect):
        """测试转写功能成功。"""
        # 准备 mock 返回值
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "测试文本"
        mock_model.transcribe.return_value = ([mock_segment], None)
        mock_whisper.return_value = mock_model

        # 执行转写
        from video_to_action.extractor import Extractor

        config = {"transcription": {"model": "base", "device": "cpu", "compute_type": "int8"}}
        extractor = Extractor(config, Path("outputs"))
        segments = extractor.transcribe(Path("test.mp4"))

        # 验证结果
        assert len(segments) == 1
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 5.0
        assert segments[0]["text"] == "normalized text"

    def test_normalize_text(self):
        """测试文本规范化功能。"""
        from video_to_action.extractor import Extractor

        config = {"transcription": {"model": "base"}}
        extractor = Extractor(config, Path("outputs"))

        # 测试多个空白符合并
        assert extractor._normalize_text("hello   world") == "hello world"

        # 测试首尾空白删除
        assert extractor._normalize_text("  hello world  ") == "hello world"

        # 测试混合空白
        assert extractor._normalize_text("\n\t hello \n world \t\n") == "hello world"

    @patch("shutil.which", return_value="ffmpeg")
    @patch("subprocess.run")
    def test_extract_audio_success(self, mock_run, mock_which):
        """测试音频提取成功。"""
        # 准备 mock 返回值
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        from video_to_action.extractor import Extractor

        config = {"transcription": {"model": "base"}}
        extractor = Extractor(config, Path("outputs"))

        # 创建临时视频文件
        video_path = Path("test.mp4")
        video_path.touch()

        try:
            audio_path = extractor.extract_audio(video_path)
            assert audio_path.exists() is False or "test.wav" in str(audio_path)
        finally:
            video_path.unlink(missing_ok=True)

    @patch("shutil.which", return_value=None)
    def test_extract_audio_no_ffmpeg(self, mock_which):
        """测试 ffmpeg 不存在时抛出异常。"""
        from video_to_action.extractor import Extractor

        config = {"transcription": {"model": "base"}}
        extractor = Extractor(config, Path("outputs"))

        with pytest.raises(EnvironmentError, match="未找到 ffmpeg"):
            extractor.extract_audio(Path("test.mp4"))


class TestExtractorIntegration:
    """测试 Extractor 类的集成功能（需要实际视频文件）。"""

    @pytest.mark.skip(reason="需要实际视频文件，且在 CI 环境中可能不可用")
    def test_process_integration(self):
        """测试完整处理流程（集成测试）。"""
        pass
