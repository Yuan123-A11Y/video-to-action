"""共享测试 fixtures 和配置。"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def temp_output_dir(tmp_path):
    """创建临时输出目录。"""
    output_dir = tmp_path / "outputs"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def sample_config():
    """返回基础配置字典。"""
    return {
        "automation_level": "confirm",
        "max_retries": 3,
        "output_dir": "outputs",
        "download": {
            "primary": "douyin-downloader",
            "fallback": "yt-dlp",
            "format": "mp4",
            "quality": "best",
            "headers": {"User-Agent": "TestAgent/1.0"},
            "cookies": {},
        },
        "douyin_downloader": {
            "thread": 2,
            "retry_times": 3,
            "proxy": "",
            "cookies": {},
        },
        "platforms": {
            "douyin": {"greenvideo_url": "https://greenvideo.cc/douyin"},
            "bilibili": {"greenvideo_url": "https://greenvideo.cc/bilibili"},
        },
        "transcription": {"model": "base", "language": "zh"},
        "llm": {
            "provider": "mock",
            "api_key": "",
            "base_url": "https://api.test.com/v1",
            "model": "test-model",
            "max_tokens": 1024,
            "temperature": 0.3,
        },
        "safety": {
            "forbidden_keywords": ["rm -rf /", "format"],
            "require_confirm": ["run_remote_script"],
        },
    }


@pytest.fixture
def mock_video_file(tmp_path):
    """创建模拟的视频文件。"""
    video_file = tmp_path / "test_video.mp4"
    # 写入一个小的无效 MP4 头部，仅用于路径存在性测试
    video_file.write_bytes(b"\x00\x00\x00\x1cftypmp42\x00\x00\x00\x01mp42")
    return video_file


@pytest.fixture
def mock_audio_file(tmp_path):
    """创建模拟的音频文件。"""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"RIFF" + b"\x00" * 44)  # 最小 WAV 头部
    return audio_file


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run 返回成功结果。"""
    import subprocess

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "mock stdout"
        result.stderr = ""
        result.text = "mock stdout"
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    return mock_run


@pytest.fixture
def mock_ffmpeg_available(monkeypatch):
    """模拟 ffmpeg 可用。"""
    import shutil

    monkeypatch.setattr(shutil, "which", lambda x: "ffmpeg" if x == "ffmpeg" else None)
    return True


@pytest.fixture
def mock_ffmpeg_unavailable(monkeypatch):
    """模拟 ffmpeg 不可用。"""
    import shutil

    monkeypatch.setattr(shutil, "which", lambda x: None)
    return False
