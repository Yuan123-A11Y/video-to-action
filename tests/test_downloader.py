# g:\trae\video-to-action\tests\test_downloader.py
"""视频下载器模块的单元测试。"""

from pathlib import Path
from unittest.mock import patch

from video_to_action.downloader import (
    DouyinDownloader,
    GreenVideoDownloader,
    YtDlpDownloader,
)


def test_yt_dlp_downloader_builds_command():
    """验证 YtDlpDownloader 能正确构造 yt-dlp 命令列表。"""
    config = {"download": {"primary": "yt-dlp", "format": "mp4", "quality": "best"}}
    with patch.object(YtDlpDownloader, "_check_dependency"):
        downloader = YtDlpDownloader(config, output_dir=Path("outputs"))
    cmd = downloader._build_command(
        "https://www.bilibili.com/video/BV1xx411c7mD", Path("outputs/test.mp4")
    )
    assert "yt-dlp" in cmd
    assert "https://www.bilibili.com/video/BV1xx411c7mD" in cmd
    assert str(Path("outputs/test.mp4")) in cmd


def test_yt_dlp_downloader_adds_headers_and_cookies():
    """验证 YtDlpDownloader 能根据配置添加请求头和 Cookie 参数。"""
    config = {
        "download": {
            "headers": {"Referer": "https://www.bilibili.com"},
            "cookies": {"browser": "chrome"},
        }
    }
    with patch.object(YtDlpDownloader, "_check_dependency"):
        downloader = YtDlpDownloader(config, output_dir=Path("outputs"))
    cmd = downloader._build_command(
        "https://www.bilibili.com/video/BV1xx411c7mD", Path("outputs/test.mp4")
    )
    assert "--add-header" in cmd
    assert "Referer:https://www.bilibili.com" in cmd
    assert "--cookies-from-browser" in cmd
    assert "chrome" in cmd


def test_yt_dlp_downloader_supports_cookie_file():
    """验证 YtDlpDownloader 支持从 Cookie 文件导入。"""
    config = {
        "download": {
            "cookies": {"file": "~/cookies.txt"},
        }
    }
    with patch.object(YtDlpDownloader, "_check_dependency"):
        downloader = YtDlpDownloader(config, output_dir=Path("outputs"))
    cmd = downloader._build_command(
        "https://www.douyin.com/video/123", Path("outputs/test.mp4")
    )
    assert "--cookies" in cmd
    assert "cookies.txt" in " ".join(cmd)


def test_detect_platform_delegates_to_utils():
    """验证 detect_video_platform 正确委托给 utils.detect_platform。"""
    from video_to_action.downloader import detect_video_platform

    assert detect_video_platform("https://v.douyin.com/abc") == "douyin"
    assert detect_video_platform("https://www.youtube.com/watch?v=abc") == "youtube"


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


def test_yt_dlp_downloader_raw_cookies(tmp_path):
    """验证 YtDlpDownloader 能将 raw Cookie 字典写入 Netscape 文件并传入 yt-dlp。"""
    config = {
        "download": {
            "cookies": {
                "raw": {
                    "msToken": "abc123",
                    "ttwid": "xyz789",
                }
            }
        }
    }
    with patch.object(YtDlpDownloader, "_check_dependency"):
        downloader = YtDlpDownloader(config, output_dir=tmp_path)
    cmd = downloader._build_command(
        "https://www.douyin.com/video/123", tmp_path / "test.mp4"
    )
    assert "--cookies" in cmd
    cookie_path = Path(cmd[cmd.index("--cookies") + 1])
    assert cookie_path.exists()
    content = cookie_path.read_text(encoding="utf-8")
    assert "# Netscape HTTP Cookie File" in content
    assert "msToken\tabc123" in content
    assert ".douyin.com" in content


def test_yt_dlp_downloader_platform_override(tmp_path):
    """验证平台级 Headers/Cookies 覆盖全局配置。"""
    config = {
        "download": {
            "headers": {"Referer": "https://global.example.com"},
            "cookies": {"browser": "chrome"},
            "platforms": {
                "douyin": {
                    "headers": {"Referer": "https://www.douyin.com/"},
                    "cookies": {"raw": {"ttwid": "override"}},
                }
            },
        }
    }
    with patch.object(YtDlpDownloader, "_check_dependency"):
        downloader = YtDlpDownloader(config, output_dir=tmp_path)
    cmd = downloader._build_command(
        "https://www.douyin.com/video/123", tmp_path / "test.mp4"
    )
    assert "Referer:https://www.douyin.com/" in cmd
    assert "--cookies-from-browser" not in cmd
    assert "--cookies" in cmd
    assert "ttwid\toverride" in Path(
        cmd[cmd.index("--cookies") + 1]
    ).read_text(encoding="utf-8")


def test_douyin_downloader_init():
    """验证 DouyinDownloader 初始化正确，能读取 douyin_downloader 配置。"""
    config = {
        "douyin_downloader": {
            "thread": 3,
            "retry_times": 5,
            "proxy": "http://proxy:8080",
            "cookies": {
                "msToken": "test_token",
                "ttwid": "test_ttwid",
            },
        }
    }
    downloader = DouyinDownloader(config, output_dir=Path("outputs"))
    assert downloader.dy_config["thread"] == 3
    assert downloader.dy_config["retry_times"] == 5
    assert downloader.dy_config["proxy"] == "http://proxy:8080"


def test_douyin_downloader_load_raw_cookies():
    """验证 DouyinDownloader 能从配置中的 raw cookies 加载。"""
    config = {
        "douyin_downloader": {
            "cookies": {
                "msToken": "abc123",
                "ttwid": "xyz789",
                "empty_field": "",
            },
        }
    }
    downloader = DouyinDownloader(config, output_dir=Path("outputs"))
    cookies = downloader._load_cookies()
    assert cookies["msToken"] == "abc123"
    assert cookies["ttwid"] == "xyz789"
    assert "empty_field" not in cookies


def test_douyin_downloader_parse_netscape_cookies(tmp_path):
    """验证 DouyinDownloader 能正确解析 Netscape 格式 Cookie 文件。"""
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".douyin.com\tTRUE\t/\tFALSE\t0\tmsToken\ttest_ms_token\n"
        ".douyin.com\tTRUE\t/\tFALSE\t0\tttwid\ttest_ttwid\n"
        ".douyin.com\tTRUE\t/\tFALSE\t0\tsid_tt\ttest_sid\n",
        encoding="utf-8",
    )
    config = {"douyin_downloader": {"cookies": {}}}
    downloader = DouyinDownloader(config, output_dir=tmp_path)
    cookies = downloader._parse_netscape_cookies(cookie_file)
    assert cookies["msToken"] == "test_ms_token"
    assert cookies["ttwid"] == "test_ttwid"
    assert cookies["sid_tt"] == "test_sid"
    assert len(cookies) == 3


def test_douyin_downloader_resolve_tool_root():
    """验证 DouyinDownloader 能正确解析工具根目录。"""
    # 测试使用内置 tools 目录（project_path 为空或不存在时）
    config = {"douyin_downloader": {"project_path": ""}}
    downloader = DouyinDownloader(config, output_dir=Path("outputs"))
    assert downloader._tool_root.name == "douyin-downloader"
    assert "tools" in str(downloader._tool_root)

    # 测试不存在的路径会回退到内置目录
    config = {"douyin_downloader": {"project_path": "nonexistent_path"}}
    downloader = DouyinDownloader(config, output_dir=Path("outputs"))
    assert downloader._tool_root.name == "douyin-downloader"


def test_download_video_douyin_uses_douyin_downloader():
    """验证 download_video 对抖音 URL 优先使用 douyin-downloader。"""
    from video_to_action.downloader import download_video

    config = {"download": {"fallback": "yt-dlp"}, "douyin_downloader": {}}
    test_url = "https://v.douyin.com/test123/"

    with patch.object(DouyinDownloader, "download") as mock_dy_download, patch.object(
        YtDlpDownloader, "_check_dependency"
    ), patch.object(YtDlpDownloader, "download") as mock_yt_download:
        mock_dy_download.return_value = {
            "success": True,
            "platform": "douyin",
            "method": "douyin-downloader",
            "output_path": "/path/to/video.mp4",
            "stdout": "",
            "stderr": "",
        }
        result = download_video(test_url, config, Path("outputs"))
        assert result["method"] == "douyin-downloader"
        assert result["success"] is True
        mock_dy_download.assert_called_once()
        mock_yt_download.assert_not_called()


def test_download_video_douyin_falls_back_to_yt_dlp():
    """验证 douyin-downloader 失败时回退到 yt-dlp。"""
    from video_to_action.downloader import download_video

    config = {"download": {"fallback": "yt-dlp"}, "douyin_downloader": {}}
    test_url = "https://v.douyin.com/test123/"

    with patch.object(DouyinDownloader, "download") as mock_dy_download, patch.object(
        YtDlpDownloader, "_check_dependency"
    ), patch.object(YtDlpDownloader, "download") as mock_yt_download:
        mock_dy_download.return_value = {
            "success": False,
            "platform": "douyin",
            "method": "douyin-downloader",
            "output_path": "",
            "stdout": "",
            "stderr": "下载失败",
        }
        mock_yt_download.return_value = {
            "success": True,
            "platform": "douyin",
            "method": "yt-dlp",
            "output_path": "/path/to/video.mp4",
            "stdout": "",
            "stderr": "",
        }
        result = download_video(test_url, config, Path("outputs"))
        assert result["method"] == "yt-dlp"
        assert result["success"] is True
        mock_dy_download.assert_called_once()
        mock_yt_download.assert_called_once()
