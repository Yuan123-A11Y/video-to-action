# g:\trae\video-to-action\tests\test_config.py
from pathlib import Path

from video_to_action.config import load_config


def test_load_config_default(tmp_path):
    """测试加载默认配置文件。"""
    # 使用 example 配置文件
    import video_to_action.config as config_module

    example_path = Path(config_module.__file__).parent.parent / "config" / "settings.example.yaml"
    if example_path.exists():
        config = load_config(example_path)
        assert "automation_level" in config
        assert "max_retries" in config
        assert "download" in config
        assert config["download"]["primary"] == "douyin-downloader"
        assert "douyin_downloader" in config
        assert "platforms" in config
    else:
        # 如果没有 example 文件，创建临时配置
        config_data = """automation_level: auto
max_retries: 3
download:
  primary: douyin-downloader
  fallback: yt-dlp
  format: mp4
  quality: best
douyin_downloader:
  project_path: ""
  thread: 3
platforms:
  douyin:
    name: 抖音
transcription:
  model: base
  language: zh
llm:
  provider: mock
safety:
  forbidden_keywords: []
  require_confirm: []
"""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(config_data)
        config = load_config(config_file)
        assert config["automation_level"] == "auto"
        assert config["max_retries"] == 3
        assert config["download"]["primary"] == "douyin-downloader"
