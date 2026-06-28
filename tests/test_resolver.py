"""Test cases for video_to_action/resolver.py"""

from pathlib import Path


from video_to_action.resolver import Resolver


def _make_resolver(tmp_path: Path) -> Resolver:
    """创建一个测试用的 Resolver 实例。"""
    config = {}
    return Resolver(config, tmp_path)


class TestInit:
    """Test Resolver.__init__ method."""

    def test_init_sets_attributes(self, tmp_path: Path):
        """Test that __init__ sets config and output_dir attributes."""
        config = {"test": "config"}
        resolver = Resolver(config, tmp_path)

        assert resolver.config == config
        assert resolver.output_dir == tmp_path


class TestSuggestFix:
    """Test suggest_fix method."""

    def test_pip_command_not_found(self, tmp_path: Path):
        """Test suggesting fix for pip command not found."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("pip install requests", "command not found: pip")

        assert result is not None
        assert "Python" in result
        assert "PATH" in result

    def test_pip_command_not_found_chinese(self, tmp_path: Path):
        """Test suggesting fix for pip command not found (Chinese error)."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("pip install requests", "pip 不是内部或外部命令")

        assert result is not None
        assert "Python" in result

    def test_network_timeout(self, tmp_path: Path):
        """Test suggesting fix for network timeout."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("pip install requests", "ERROR: Connection timeout")

        assert result is not None
        assert "镜像" in result or "mirror" in result.lower()

    def test_network_connection_error(self, tmp_path: Path):
        """Test suggesting fix for network connection error."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("pip install requests", "Connection refused")

        assert result is not None

    def test_permission_denied(self, tmp_path: Path):
        """Test suggesting fix for permission denied."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("chmod +x script.sh", "Permission denied")

        assert result is not None
        assert "管理员" in result or "sudo" in result

    def test_npm_command_not_found(self, tmp_path: Path):
        """Test suggesting fix for npm command not found."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("npm install", "command not found: npm")

        assert result is not None
        assert "Node.js" in result

    def test_git_command_not_found(self, tmp_path: Path):
        """Test suggesting fix for git command not found."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("git clone repo", "command not found: git")

        assert result is not None
        assert "Git" in result

    def test_ffmpeg_not_found(self, tmp_path: Path):
        """Test suggesting fix for ffmpeg not found."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("ffmpeg -i input.mp4", "ffmpeg: command not found")

        assert result is not None
        assert "ffmpeg" in result

    def test_ffmpeg_not_found_chinese(self, tmp_path: Path):
        """Test suggesting fix for ffmpeg not found (Chinese error)."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("ffmpeg -i input.mp4", "ffmpeg 不是内部或外部命令")

        assert result is not None
        assert "ffmpeg" in result

    def test_ytdlp_not_found(self, tmp_path: Path):
        """Test suggesting fix for yt-dlp not found."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("yt-dlp https://youtube.com/watch?v=123", "yt-dlp: command not found")

        assert result is not None
        assert "yt-dlp" in result
        assert "pip install" in result

    def test_ytdlp_not_found_chinese(self, tmp_path: Path):
        """Test suggesting fix for yt-dlp not found (Chinese error)."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("yt-dlp https://youtube.com/watch?v=123", "yt-dlp 不是内部或外部命令")

        assert result is not None
        assert "yt-dlp" in result

    def test_unknown_error(self, tmp_path: Path):
        """Test suggesting fix for unknown error."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("some command", "Some unknown error")

        assert result is None

    def test_empty_error_output(self, tmp_path: Path):
        """Test suggesting fix with empty error output."""
        resolver = _make_resolver(tmp_path)

        result = resolver.suggest_fix("some command", "")

        assert result is None

    def test_case_insensitive_matching(self, tmp_path: Path):
        """Test that error matching is case-insensitive."""
        resolver = _make_resolver(tmp_path)

        # The method converts error_output to lowercase, so we test with mixed case
        result = resolver.suggest_fix("pip install requests", "Command Not Found: pip")

        assert result is not None


class TestExtractExecutableCommand:
    """Test _extract_executable_command method."""

    def test_extract_pip_command(self, tmp_path: Path):
        """Test extracting pip command from suggestion."""
        resolver = _make_resolver(tmp_path)

        result = resolver._extract_executable_command("pip install <pkg> -i https://mirror.com")

        assert result == "pip install <pkg> -i https://mirror.com"

    def test_extract_npm_command(self, tmp_path: Path):
        """Test extracting npm command from suggestion."""
        resolver = _make_resolver(tmp_path)

        result = resolver._extract_executable_command("npm install package")

        assert result == "npm install package"

    def test_extract_git_command(self, tmp_path: Path):
        """Test extracting git command from suggestion."""
        resolver = _make_resolver(tmp_path)

        result = resolver._extract_executable_command("git clone repo")

        assert result == "git clone repo"

    def test_extract_ffmpeg_command(self, tmp_path: Path):
        """Test extracting ffmpeg command from suggestion."""
        resolver = _make_resolver(tmp_path)

        result = resolver._extract_executable_command("ffmpeg -i input.mp4 output.mp4")

        assert result == "ffmpeg -i input.mp4 output.mp4"

    def test_extract_ytdlp_command(self, tmp_path: Path):
        """Test extracting yt-dlp command from suggestion."""
        resolver = _make_resolver(tmp_path)

        result = resolver._extract_executable_command("yt-dlp https://youtube.com/watch?v=123")

        assert result == "yt-dlp https://youtube.com/watch?v=123"

    def test_no_executable_command(self, tmp_path: Path):
        """Test when suggestion doesn't contain executable command."""
        resolver = _make_resolver(tmp_path)

        result = resolver._extract_executable_command("请确保 Python 和 pip 已安装")

        assert result is None

    def test_empty_suggestion(self, tmp_path: Path):
        """Test with empty suggestion."""
        resolver = _make_resolver(tmp_path)

        result = resolver._extract_executable_command("")

        assert result is None

    def test_none_suggestion(self, tmp_path: Path):
        """Test with None suggestion."""
        resolver = _make_resolver(tmp_path)

        result = resolver._extract_executable_command(None)

        assert result is None


class TestResolve:
    """Test resolve method."""

    def test_resolve_with_executable_fix(self, tmp_path: Path):
        """Test resolve returns fix suggestion."""
        resolver = _make_resolver(tmp_path)

        # Use network timeout error
        result = resolver.resolve("pip install requests", "ERROR: Connection timeout")

        # Should be resolved (identified the error)
        assert result["resolved"] is True
        # Message should contain useful information
        assert "建议" in result["message"] or "mirror" in result["message"].lower() or "镜像" in result["message"]

    def test_resolve_with_nonexecutable_fix(self, tmp_path: Path):
        """Test resolve returns non-executable fix."""
        resolver = _make_resolver(tmp_path)

        result = resolver.resolve("some command", "Permission denied")

        assert result["resolved"] is True
        assert result["executable"] is False
        assert result["new_command"] is None
        assert "建议" in result["message"] or "建议" in result["message"]

    def test_resolve_unknown_error(self, tmp_path: Path):
        """Test resolve with unknown error."""
        resolver = _make_resolver(tmp_path)

        result = resolver.resolve("some command", "Some unknown error")

        assert result["resolved"] is False
        assert result["executable"] is False
        assert result["new_command"] is None
        assert "无法自动诊断" in result["message"] or "cannot" in result["message"].lower()

    def test_resolve_with_attempt(self, tmp_path: Path):
        """Test resolve with attempt parameter."""
        resolver = _make_resolver(tmp_path)

        result = resolver.resolve("pip install requests", "command not found: pip", attempt=2)

        # Attempt parameter is not used in current implementation, but should not crash
        assert result["resolved"] is True

    def test_resolve_ffmpeg_error(self, tmp_path: Path):
        """Test resolve with ffmpeg error."""
        resolver = _make_resolver(tmp_path)

        result = resolver.resolve("ffmpeg -i input.mp4", "ffmpeg: command not found")

        assert result["resolved"] is True
        assert "ffmpeg" in result["message"]

    def test_resolve_ytdlp_error(self, tmp_path: Path):
        """Test resolve with yt-dlp error."""
        resolver = _make_resolver(tmp_path)

        result = resolver.resolve("yt-dlp https://youtube.com/watch?v=123", "yt-dlp: command not found")

        assert result["resolved"] is True
        assert "yt-dlp" in result["message"]
        assert "pip install" in result["message"]
