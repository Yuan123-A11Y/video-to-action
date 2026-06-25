"""
Executor 模块单元测试。

测试命令执行器的核心功能：
- 危险命令拦截
- 交互式工具检测
- 安装命令校验
- 命令执行超时
"""

import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_to_action.executor import Executor, INTERACTIVE_TOOLS


class TestExecutorInit:
    """测试 Executor 初始化。"""

    def test_init_with_default_config(self):
        """测试使用默认配置初始化。"""
        config = {}
        executor = Executor(config, Path("outputs"))
        assert executor.timeout == 300  # 默认超时 300 秒
        assert executor.safety == {}

    def test_init_with_custom_timeout(self):
        """测试使用自定义超时配置初始化。"""
        config = {"safety": {"command_timeout": 60}}
        executor = Executor(config, Path("outputs"))
        assert executor.timeout == 60


class TestInteractiveToolDetection:
    """测试交互式工具检测。"""

    def setup_method(self):
        """每个测试前初始化 executor。"""
        self.executor = Executor({}, Path("outputs"))

    def test_detect_claude(self):
        """测试检测 claude 命令。"""
        assert self.executor._is_interactive_tool("npx @anthropic-ai/claude-code@latest") is True
        assert self.executor._is_interactive_tool("claude --help") is True

    def test_detect_cursor(self):
        """测试检测 cursor 命令。"""
        assert self.executor._is_interactive_tool("cursor .") is True

    def test_detect_codex(self):
        """测试检测 codex 命令。"""
        assert self.executor._is_interactive_tool("codex login") is True

    def test_non_interactive_tool(self):
        """测试非交互式工具返回 False。"""
        assert self.executor._is_interactive_tool("npm install express") is False
        assert self.executor._is_interactive_tool("pip install requests") is False

    def test_empty_command(self):
        """测试空命令返回 False。"""
        assert self.executor._is_interactive_tool("") is False


class TestInstallCommandValidation:
    """测试安装命令校验。"""

    def setup_method(self):
        self.executor = Executor({}, Path("outputs"))

    def test_valid_npm_install(self):
        """测试合法的 npm install 命令。"""
        assert self.executor._is_valid_install_command("npm install -g express") is True
        assert self.executor._is_valid_install_command("npm install express") is True

    def test_valid_pip_install(self):
        """测试合法的 pip install 命令。"""
        assert self.executor._is_valid_install_command("pip install requests") is True
        assert self.executor._is_valid_install_command("pip3 install numpy") is True

    def test_valid_brew_install(self):
        """测试合法的 brew install 命令。"""
        assert self.executor._is_valid_install_command("brew install git") is True

    def test_invalid_npx_run(self):
        """测试非法的 npx 运行命令（不是安装）。"""
        assert self.executor._is_valid_install_command("npx @anthropic-ai/claude-code@latest") is False
        assert self.executor._is_valid_install_command("npx express-generator") is False

    def test_invalid_empty_command(self):
        """测试空命令返回 False。"""
        assert self.executor._is_valid_install_command("") is False


class TestExecuteCommand:
    """测试命令执行功能。"""

    def setup_method(self):
        self.config = {"safety": {"forbidden_keywords": ["rm -rf /"]}}
        self.executor = Executor(self.config, Path("outputs"))

    @patch("subprocess.run")
    def test_execute_success(self, mock_run):
        """测试命令执行成功。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="success",
            stderr=""
        )
        result = self.executor.execute("echo test")
        assert result["success"] is True
        assert result["stdout"] == "success"

    @patch("subprocess.run")
    def test_execute_failure(self, mock_run):
        """测试命令执行失败。"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error message"
        )
        result = self.executor.execute("false")
        assert result["success"] is False
        assert result["stderr"] == "error message"

    def test_execute_dangerous_command(self):
        """测试危险命令被拦截。"""
        result = self.executor.execute("rm -rf /")
        assert result["success"] is False
        assert "拦截" in result["stderr"]

    @patch("subprocess.run")
    def test_execute_interactive_tool_skipped(self, mock_run):
        """测试交互式工具被跳过。"""
        result = self.executor.execute("npx @anthropic-ai/claude-code@latest")
        assert result["success"] is False
        assert result["skipped"] is True
        assert result["reason"] == "interactive_tool"
        # 命令不应该被执行
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_execute_timeout(self, mock_run):
        """测试命令执行超时。"""
        self.executor.timeout = 1  # 设置短超时
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)

        result = self.executor.execute("sleep 10")
        assert result["success"] is False
        assert result["timeout"] is True
        assert "超时" in result["stderr"]


class TestExecutePlan:
    """测试执行完整行动计划。"""

    def setup_method(self):
        self.executor = Executor({}, Path("outputs"))

    @patch.object(Executor, "execute")
    def test_execute_plan_all_success(self, mock_execute):
        """测试执行计划全部成功。"""
        mock_execute.return_value = {
            "success": True,
            "stdout": "installed",
            "stderr": "",
            "command": "npm install -g test"
        }
        plan = {
            "tools": [
                {
                    "name": "test-tool",
                    "install_commands": ["npm install -g test"],
                    "config_steps": []
                }
            ]
        }
        results = self.executor.execute_plan(plan)
        assert len(results) == 1
        assert results[0]["success"] is True

    @patch.object(Executor, "execute")
    def test_execute_plan_stop_on_failure(self, mock_execute):
        """测试执行计划在遇到失败时停止。"""
        mock_execute.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "failed",
            "command": "npm install -g test"
        }
        plan = {
            "tools": [
                {
                    "name": "test-tool",
                    "install_commands": ["npm install -g test", "npm install -g test2"],
                    "config_steps": []
                }
            ]
        }
        results = self.executor.execute_plan(plan)
        assert len(results) == 1  # 只执行了第一条命令
        mock_execute.assert_called_once()  # 第二条命令未执行


class TestCacheValidation:
    """测试下载器缓存验证逻辑。"""

    def test_extract_video_id_modal_id(self):
        """测试从 modal_id 参数提取视频 ID。"""
        from video_to_action.downloader import _extract_video_id_from_url

        url = "https://www.douyin.com/jingxuan/course?modal_id=7513843872540233023&type=general"
        video_id = _extract_video_id_from_url(url)
        assert video_id == "7513843872540233023"

    def test_extract_video_id_video_path(self):
        """测试从 /video/ 路径提取视频 ID。"""
        from video_to_action.downloader import _extract_video_id_from_url

        url = "https://www.douyin.com/video/7513843872540233023"
        video_id = _extract_video_id_from_url(url)
        assert video_id == "7513843872540233023"

    def test_extract_video_id_not_found(self):
        """测试无法提取视频 ID 时返回 None。"""
        from video_to_action.downloader import _extract_video_id_from_url

        url = "https://www.douyin.com/"
        video_id = _extract_video_id_from_url(url)
        assert video_id is None
