# g:\trae\video-to-action\tests\test_extractor.py
"""Extractor 模块单元测试：验证 ffmpeg 命令构建与文本规范化逻辑。"""

from pathlib import Path

from video_to_action.extractor import Extractor


def test_ffmpeg_command_building():
    """测试 _build_audio_command 构造的 ffmpeg 命令包含输入输出路径。"""
    config = {"transcription": {"model": "base", "language": "zh"}}
    extractor = Extractor(config, output_dir=Path("outputs"))
    cmd = extractor._build_audio_command(Path("video.mp4"), Path("audio.wav"))
    assert "ffmpeg" in cmd
    assert "video.mp4" in cmd
    assert "audio.wav" in cmd


def test_normalize_text():
    """测试 _normalize_text 能去除多余空白并保留单个空格。"""
    config = {"transcription": {"model": "base", "language": "zh"}}
    extractor = Extractor(config, output_dir=Path("outputs"))
    assert extractor._normalize_text("  hello   world  ") == "hello world"
