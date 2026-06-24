# g:\trae\video-to-action\tests\test_config.py
from pathlib import Path

from video_to_action.config import load_config


def test_load_config_default(tmp_path):
    """测试加载默认配置文件。"""
    config_path = Path("g:/trae/video-to-action/config/settings.yaml")
    config = load_config(config_path)
    assert config["automation_level"] == "auto"
    assert config["max_retries"] == 3
    assert config["download"]["primary"] == "douyin-downloader"
    assert config["download"]["fallback"] == "yt-dlp"
    assert "douyin_downloader" in config
    assert "platforms" in config
