"""Test cases for video_to_action/reporter.py"""

from pathlib import Path
from unittest.mock import patch


from video_to_action.reporter import Reporter


def _make_reporter(tmp_path: Path) -> Reporter:
    """创建一个测试用的 Reporter 实例。"""
    config = {"report": {"output_dir": str(tmp_path / "reports")}}
    return Reporter(config, tmp_path)


def _make_context() -> dict:
    """创建一个测试用的 context 字典。"""
    return {
        "video_url": "https://www.douyin.com/video/123456",
        "platform": "douyin",
        "download_method": "douyin-downloader",
        "video_path": "/tmp/test.mp4",
        "plan": {
            "theme": "Python环境配置",
            "summary": "本视频介绍了如何配置Python环境",
            "tools": [
                {
                    "name": "pyenv",
                    "purpose": "Python版本管理",
                    "links": ["https://github.com/pyenv/pyenv"],
                    "warnings": ["需要设置环境变量"],
                }
            ],
        },
        "execution_results": [
            {
                "success": True,
                "command": "pyenv install 3.11.0",
                "stdout": "Installation successful",
                "stderr": "",
            },
            {
                "success": False,
                "command": "pyenv global 3.11.0",
                "stdout": "",
                "stderr": "ERROR: Not a git repository",
            },
        ],
    }


class TestInit:
    """Test Reporter.__init__ method."""

    def test_init_creates_reports_dir(self, tmp_path: Path):
        """Test that __init__ creates the reports directory."""
        config = {}
        reporter = Reporter(config, tmp_path)

        assert reporter.config == config
        assert reporter.output_dir == tmp_path
        assert reporter.reports_dir == tmp_path / "reports"
        assert (tmp_path / "reports").exists()

    def test_init_always_uses_reports_subdir(self, tmp_path: Path):
        """Test that __init__ always uses 'reports' subdirectory."""
        config = {"report": {"output_dir": str(tmp_path / "custom_reports")}}
        reporter = Reporter(config, tmp_path)

        # Should ignore config and use output_dir / "reports"
        assert reporter.reports_dir == tmp_path / "reports"


class TestFormatExecutionResults:
    """Test _format_execution_results method."""

    def test_format_empty_results(self, tmp_path: Path):
        """Test formatting empty results list."""
        reporter = _make_reporter(tmp_path)

        result = reporter._format_execution_results([])

        assert result == ""

    def test_format_single_success_result(self, tmp_path: Path):
        """Test formatting a single successful result."""
        reporter = _make_reporter(tmp_path)

        results = [
            {
                "success": True,
                "command": "echo test",
                "stdout": "test output",
                "stderr": "",
            }
        ]

        result = reporter._format_execution_results(results)

        assert "步骤 1：成功" in result
        assert "`echo test`" in result
        assert "test output" in result

    def test_format_single_failure_result(self, tmp_path: Path):
        """Test formatting a single failed result."""
        reporter = _make_reporter(tmp_path)

        results = [
            {
                "success": False,
                "command": "false",
                "stdout": "",
                "stderr": "Command failed",
            }
        ]

        result = reporter._format_execution_results(results)

        assert "步骤 1：失败" in result
        assert "Command failed" in result

    def test_format_multiple_results(self, tmp_path: Path):
        """Test formatting multiple results."""
        reporter = _make_reporter(tmp_path)

        results = [
            {"success": True, "command": "cmd1", "stdout": "out1", "stderr": ""},
            {"success": False, "command": "cmd2", "stdout": "", "stderr": "err2"},
        ]

        result = reporter._format_execution_results(results)

        assert "步骤 1：成功" in result
        assert "步骤 2：失败" in result

    def test_format_result_without_stdout(self, tmp_path: Path):
        """Test formatting result without stdout."""
        reporter = _make_reporter(tmp_path)

        results = [{"success": True, "command": "cmd", "stdout": "", "stderr": ""}]

        result = reporter._format_execution_results(results)

        # Should not include stdout section
        assert "输出：" not in result

    def test_format_result_without_stderr(self, tmp_path: Path):
        """Test formatting result without stderr."""
        reporter = _make_reporter(tmp_path)

        results = [{"success": True, "command": "cmd", "stdout": "output", "stderr": ""}]

        result = reporter._format_execution_results(results)

        # Should not include stderr section
        assert "错误：" not in result


class TestGenerate:
    """Test generate method."""

    def test_generate_returns_path(self, tmp_path: Path):
        """Test that generate returns a Path object."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()

        result = reporter.generate(context)

        assert isinstance(result, Path)
        assert result.exists()

    def test_generate_creates_markdown_file(self, tmp_path: Path):
        """Test that generate creates a Markdown file."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()

        result = reporter.generate(context)

        assert result.suffix == ".md"
        content = result.read_text(encoding="utf-8")
        assert "# 视频到行动助手 - 执行报告" in content

    def test_generate_includes_video_info(self, tmp_path: Path):
        """Test that generate includes video information."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        assert "https://www.douyin.com/video/123456" in content
        assert "douyin" in content
        assert "douyin-downloader" in content

    def test_generate_includes_plan_info(self, tmp_path: Path):
        """Test that generate includes plan information."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        assert "Python环境配置" in content
        assert "本视频介绍了如何配置Python环境" in content

    def test_generate_includes_tools_info(self, tmp_path: Path):
        """Test that generate includes tools information."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        assert "pyenv" in content
        assert "Python版本管理" in content
        assert "https://github.com/pyenv/pyenv" in content
        assert "需要设置环境变量" in content

    def test_generate_includes_execution_results(self, tmp_path: Path):
        """Test that generate includes execution results."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        assert "pyenv install 3.11.0" in content
        assert "Installation successful" in content
        assert "ERROR: Not a git repository" in content

    def test_generate_calculates_success_failure(self, tmp_path: Path):
        """Test that generate correctly calculates success/failure counts."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        assert "总步骤数：2" in content
        assert "成功：1" in content
        assert "失败：1" in content
        assert "部分成功" in content

    def test_generate_all_success(self, tmp_path: Path):
        """Test generate with all successful results."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()
        context["execution_results"] = [
            {"success": True, "command": "cmd1", "stdout": "out1", "stderr": ""},
            {"success": True, "command": "cmd2", "stdout": "out2", "stderr": ""},
        ]

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        assert "成功：2" in content
        assert "失败：0" in content
        assert "**成功**" in content

    def test_generate_all_failure(self, tmp_path: Path):
        """Test generate with all failed results."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()
        context["execution_results"] = [
            {"success": False, "command": "cmd1", "stdout": "", "stderr": "err1"},
            {"success": False, "command": "cmd2", "stdout": "", "stderr": "err2"},
        ]

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        assert "成功：0" in content
        assert "失败：2" in content
        assert "**失败**" in content

    def test_generate_without_plan(self, tmp_path: Path):
        """Test generate without plan in context."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()
        del context["plan"]

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        # Should not crash, should use default values
        assert "# 视频到行动助手 - 执行报告" in content

    def test_generate_without_execution_results(self, tmp_path: Path):
        """Test generate without execution_results in context."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()
        context["execution_results"] = []

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        # Should not crash
        assert "总步骤数：0" in content
        assert "成功：0" in content

    def test_generate_with_empty_tools(self, tmp_path: Path):
        """Test generate with empty tools list."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()
        context["plan"]["tools"] = []

        result = reporter.generate(context)

        content = result.read_text(encoding="utf-8")
        # Should not crash
        assert "# 视频到行动助手 - 执行报告" in content

    def test_generate_uses_timestamp_in_filename(self, tmp_path: Path):
        """Test that generate uses timestamp in filename."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()

        with patch("time.strftime", return_value="20240101_120000"):
            result = reporter.generate(context)

        assert "report_20240101_120000.md" in str(result)

    def test_generate_file_encoding_utf8(self, tmp_path: Path):
        """Test that generated file is UTF-8 encoded."""
        reporter = _make_reporter(tmp_path)
        context = _make_context()
        context["plan"]["theme"] = "中文主题测试"

        result = reporter.generate(context)

        # Read raw bytes to check encoding
        raw_content = result.read_bytes()
        # Should be valid UTF-8
        content = raw_content.decode("utf-8")
        assert "中文主题测试" in content
