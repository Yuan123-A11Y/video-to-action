"""Test cases for video_to_action/utils.py"""

import logging
from pathlib import Path


from video_to_action.utils import (
    detect_platform,
    ensure_dir,
    get_logger,
    is_dangerous_command,
    sanitize_filename,
    setup_logging,
)


class TestDetectPlatform:
    """Test detect_platform function."""

    def test_detect_douyin_url(self):
        """Test detecting douyin URLs."""
        urls = [
            "https://www.douyin.com/video/123456",
            "https://v.douyin.com/iRNBhoP/",
            "https://www.iesdouyin.com/share/video/123456",
        ]

        for url in urls:
            result = detect_platform(url)
            assert result == "douyin", f"Failed for {url}"

    def test_detect_bilibili_url(self):
        """Test detecting bilibili URLs."""
        urls = [
            "https://www.bilibili.com/video/BV1xx411c7mD",
            "https://b23.tv/BV1xx411c7mD",
        ]

        for url in urls:
            result = detect_platform(url)
            assert result == "bilibili", f"Failed for {url}"

    def test_detect_youtube_url(self):
        """Test detecting YouTube URLs."""
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
        ]

        for url in urls:
            result = detect_platform(url)
            assert result == "youtube", f"Failed for {url}"

    def test_detect_unknown_url(self):
        """Test detecting unknown URLs."""
        urls = [
            "https://www.example.com/video/123",
            "https://vimeo.com/123456",
        ]

        for url in urls:
            result = detect_platform(url)
            assert result == "unknown", f"Failed for {url}"

    def test_detect_case_insensitive(self):
        """Test that detection is case-insensitive."""
        urls = [
            "https://WWW.DOUYIN.COM/video/123",
            "https://WWW.BILIBILI.COM/video/BV1xx",
        ]

        for url in urls:
            result = detect_platform(url)
            assert result != "unknown", f"Failed for {url}"

    def test_detect_empty_url(self):
        """Test detecting empty URL."""
        result = detect_platform("")

        assert result == "unknown"

    def test_detect_partial_match(self):
        """Test that partial matches are correctly identified."""
        # Should not match "douyin" in "notdouyinexample.com"
        result = detect_platform("https://notdouyinexample.com/video/123")
        assert result == "unknown"


class TestSanitizeFilename:
    """Test sanitize_filename function."""

    def test_sanitize_basic(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("simple_file.mp4")

        assert result == "simple_file.mp4"

    def test_sanitize_with_spaces(self):
        """Test sanitization of filenames with spaces."""
        result = sanitize_filename("file with spaces.mp4")

        assert " " not in result
        assert "_" in result

    def test_sanitize_with_illegal_chars(self):
        """Test sanitization of filenames with illegal characters."""
        illegal_chars = ["\\", "/", "*", "?", '"', "<", ">", "|"]

        for char in illegal_chars:
            filename = f"file{char}name.mp4"
            result = sanitize_filename(filename)
            assert char not in result, f"Failed for char {char}"

    def test_sanitize_with_colon(self):
        """Test sanitization of filenames with colons (Windows)."""
        result = sanitize_filename("file:name.mp4")

        assert ":" not in result
        assert "_" in result

    def test_sanitize_leading_trailing_spaces(self):
        """Test sanitization of filenames with leading/trailing spaces."""
        result = sanitize_filename("  file name  ")

        # sanitize_filename strips leading/trailing spaces, then replaces spaces with _
        assert result == "file_name"

    def test_sanitize_multiple_spaces(self):
        """Test sanitization of filenames with multiple spaces."""
        result = sanitize_filename("file   name.mp4")

        assert "   " not in result
        assert "file_name.mp4" == result or "__" not in result

    def test_sanitize_unicode(self):
        """Test sanitization of filenames with unicode characters."""
        result = sanitize_filename("文件名_测试.mp4")

        assert result == "文件名_测试.mp4"


class TestIsDangerousCommand:
    """Test is_dangerous_command function."""

    def test_dangerous_rm_rf_root(self):
        """Test detecting dangerous rm -rf / command."""
        result = is_dangerous_command("rm -rf /")

        assert result is True

    def test_dangerous_format(self):
        """Test detecting dangerous format command."""
        result = is_dangerous_command("format C:")

        assert result is True

    def test_dangerous_del(self):
        """Test detecting dangerous del command."""
        result = is_dangerous_command("del /f /s /q C:\\")

        assert result is True

    def test_safe_command(self):
        """Test that safe commands are not detected as dangerous."""
        safe_commands = [
            "echo hello",
            "ls -la",
            "pip install requests",
            "git status",
        ]

        for cmd in safe_commands:
            result = is_dangerous_command(cmd)
            assert result is False, f"False positive for {cmd}"

    def test_custom_forbidden_keywords(self):
        """Test with custom forbidden keywords."""
        result = is_dangerous_command("custom_dangerous_cmd", forbidden_keywords=["custom_dangerous"])

        assert result is True

    def test_case_insensitive_dangerous(self):
        """Test that dangerous command detection is case-insensitive."""
        result = is_dangerous_command("RM -RF /")

        assert result is True

    def test_empty_command(self):
        """Test with empty command."""
        result = is_dangerous_command("")

        assert result is False


class TestEnsureDir:
    """Test ensure_dir function."""

    def test_ensure_existing_dir(self, tmp_path: Path):
        """Test ensuring an existing directory."""
        result = ensure_dir(tmp_path)

        assert result == tmp_path
        assert result.exists()

    def test_ensure_new_dir(self, tmp_path: Path):
        """Test ensuring a new directory."""
        new_dir = tmp_path / "new_dir"

        result = ensure_dir(new_dir)

        assert result == new_dir
        assert result.exists()
        assert result.is_dir()

    def test_ensure_nested_dir(self, tmp_path: Path):
        """Test ensuring a nested directory."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"

        result = ensure_dir(nested_dir)

        assert result == nested_dir
        assert result.exists()


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        # Should not raise
        setup_logging(level=logging.INFO)

        logger = logging.getLogger("test_logger")
        assert logger is not None

    def test_setup_logging_with_file(self, tmp_path: Path):
        """Test logging setup with log file."""
        log_file = tmp_path / "test.log"

        setup_logging(level=logging.DEBUG, log_file=log_file)

        assert log_file.parent.exists()

    def test_setup_logging_with_rich_tracebacks(self):
        """Test logging setup with rich tracebacks."""
        # Should not raise
        setup_logging(level=logging.INFO, rich_tracebacks=True)

    def test_setup_logging_without_rich_tracebacks(self):
        """Test logging setup without rich tracebacks."""
        # Should not raise
        setup_logging(level=logging.INFO, rich_tracebacks=False)


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logging.Logger instance."""
        result = get_logger("test_module")

        assert isinstance(result, logging.Logger)

    def test_get_logger_with_different_names(self):
        """Test get_logger with different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1 is not logger2

    def test_get_logger_returns_same_instance(self):
        """Test that get_logger returns same instance for same name."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        assert logger1 is logger2
