# g:\trae\video-to-action\tests\test_downloader.py
"""视频下载器模块的单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from video_to_action.downloader import YtDlpDownloader


def test_yt_dlp_downloader_builds_command():
    """验证 YtDlpDownloader 能正确构造 yt-dlp 命令列表。"""
    config = {"download": {"primary": "yt-dlp", "format": "mp4", "quality": "best"}}
    with patch.object(YtDlpDownloader, "_check_dependency"):
        downloader = YtDlpDownloader(config, output_dir=Path("outputs"))
    cmd = downloader._build_command("https://www.bilibili.com/video/BV1xx411c7mD", Path("outputs/test.mp4"))
    assert "yt-dlp" in cmd
    assert "https://www.bilibili.com/video/BV1xx411c7mD" in cmd
    assert str(Path("outputs/test.mp4")) in cmd


def test_detect_platform_delegates_to_utils():
    """验证 detect_video_platform 正确委托给 utils.detect_platform。"""
    from video_to_action.downloader import detect_video_platform

    assert detect_video_platform("https://v.douyin.com/abc") == "douyin"
    assert detect_video_platform("https://www.youtube.com/watch?v=abc") == "youtube"


from video_to_action.downloader import GreenVideoDownloader


def test_greenvideo_url_for_platform():
    """验证 GreenVideoDownloader 能根据平台读取对应的 greenvideo_url 配置。"""
    config = {
        "platforms": {
            "douyin": {"greenvideo_url": "https://greenvideo.cc/douyin"},
            "bilibili": {"greenvideo_url": "https://greenvideo.cc/bilibili"},
        }
    }
    downloader = GreenVideoDownloader(config, output_dir=Path("outputs"))
    assert downloader._get_platform_url("douyin") == "https://greenvideo.cc/douyin"
    assert downloader._get_platform_url("bilibili") == "https://greenvideo.cc/bilibili"
