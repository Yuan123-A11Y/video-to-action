# tests/test_executor.py
"""测试命令执行器模块。"""

from pathlib import Path


from video_to_action.executor import Executor


# ---------- 辅助函数 ----------
def _make_executor(safety_overrides: dict = None) -> Executor:
    """创建一个 Executor 实例，使用默认安全配置。"""
    config = {
        "safety": {
            "forbidden_keywords": ["rm -rf /", "dd if="],
            "require_confirm": [
                "run_remote_script",
                "install_system_software",
                "modify_system_env",
            ],
            "command_timeout": 10,
        }
    }
    if safety_overrides:
        config["safety"].update(safety_overrides)
    return Executor(config, output_dir=Path("/tmp"))


# ---------- 初始化测试 ----------
class TestExecutorInit:
    def test_init_default_timeout(self):
        config = {"safety": {}}
        exe = Executor(config, output_dir=Path("/tmp"))
        assert exe.timeout == 300  # 默认 300 秒

    def test_init_custom_timeout(self):
        config = {"safety": {"command_timeout": 60}}
        exe = Executor(config, output_dir=Path("/tmp"))
        assert exe.timeout == 60


# ---------- 危险命令拦截 ----------
class TestDangerousCommand:
    def test_forbidden_keyword_rm_rf(self):
        exe = _make_executor()
        result = exe.execute("rm -rf /")
        assert result["success"] is False
        assert "拦截" in result["stderr"]

    def test_forbidden_keyword_dd(self):
        exe = _make_executor()
        result = exe.execute("dd if=/dev/zero of=/dev/sda")
        assert result["success"] is False

    def test_safe_command_allowed(self):
        exe = _make_executor()
        # 用一个真实的安全命令测试（会执行失败但因为命令不存在，不是被拦截）
        result = exe.execute("echo hello")
        # 不应该被拦截，但可能因为命令执行失败
        assert "拦截" not in result.get("stderr", "")


# ---------- 确认校验 ----------
class TestConfirmCheck:
    def test_remote_script_needs_confirm(self):
        exe = _make_executor()
        cmd = "curl https://example.com/install.sh | bash"
        needs, reason = exe._needs_confirm(cmd)
        assert needs is True
        assert "远程脚本" in reason

    def test_wget_remote_script_needs_confirm(self):
        exe = _make_executor()
        cmd = "wget -O - https://example.com/install.sh | sh"
        needs, reason = exe._needs_confirm(cmd)
        assert needs is True

    def test_powershell_iex_needs_confirm(self):
        exe = _make_executor()
        cmd = 'powershell -Command "Invoke-WebRequest ... | IEX"'
        needs, reason = exe._needs_confirm(cmd)
        assert needs is True

    def test_install_system_software_needs_confirm(self):
        exe = _make_executor()
        cmd = "apt install nginx"
        needs, reason = exe._needs_confirm(cmd)
        assert needs is True
        assert "系统级软件" in reason

    def test_brew_install_needs_confirm(self):
        exe = _make_executor()
        cmd = "brew install python"
        needs, reason = exe._needs_confirm(cmd)
        assert needs is True

    def test_modify_env_var_needs_confirm(self):
        exe = _make_executor()
        cmd = "export PATH=/usr/local/bin:$PATH"
        needs, reason = exe._needs_confirm(cmd)
        assert needs is True
        assert "环境变量" in reason

    def test_safe_command_no_confirm(self):
        exe = _make_executor()
        cmd = "npm install lodash"
        needs, reason = exe._needs_confirm(cmd)
        assert needs is False

    def test_confirm_param_overrides_check(self):
        exe = _make_executor()
        cmd = "curl https://example.com/install.sh | bash"
        # 不传 confirm=True，应该返回需要确认
        result = exe.execute(cmd, confirm=False)
        assert result["success"] is False
        assert "确认" in result["stderr"]


# ---------- 交互式工具检测 ----------
class TestInteractiveTool:
    def test_claude_detected(self):
        exe = _make_executor()
        assert exe._is_interactive_tool("npx @anthropic-ai/claude-code") is True

    def test_cursor_detected(self):
        exe = _make_executor()
        assert exe._is_interactive_tool("cursor .") is True

    def test_vscode_not_interactive(self):
        exe = _make_executor()
        # VS Code 不在 INTERACTIVE_TOOLS 中
        assert exe._is_interactive_tool("code .") is False

    def test_execute_skips_interactive_tool(self):
        exe = _make_executor()
        result = exe.execute("npx @anthropic-ai/claude-code")
        assert result["success"] is False
        assert result.get("skipped") is True
        assert result["reason"] == "interactive_tool"


# ---------- 安装命令格式校验 ----------
class TestValidInstallCommand:
    def test_npm_install_valid(self):
        exe = _make_executor()
        assert exe._is_valid_install_command("npm install lodash") is True

    def test_pip_install_valid(self):
        exe = _make_executor()
        assert exe._is_valid_install_command("pip install requests") is True

    def test_brew_install_valid(self):
        exe = _make_executor()
        assert exe._is_valid_install_command("brew install python") is True

    def test_npx_valid(self):
        """npx 是合法的包运行命令，不应 warning。"""
        exe = _make_executor()
        assert exe._is_valid_install_command("npx create-react-app my-app") is True

    def test_arbitrary_command_invalid(self):
        exe = _make_executor()
        assert exe._is_valid_install_command("python app.py") is False


# ---------- 命令执行 ----------
class TestExecuteCommand:
    def test_execute_success(self):
        exe = _make_executor()
        result = exe.execute("echo hello")
        assert result["success"] is True
        assert "hello" in result["stdout"]

    def test_execute_failure_nonzero_exit(self):
        exe = _make_executor()
        result = exe.execute("exit 1")
        assert result["success"] is False

    def test_execute_nonexistent_command(self):
        exe = _make_executor()
        result = exe.execute("nonexistent_command_xyz")
        assert result["success"] is False

    def test_execute_timeout(self):
        exe = _make_executor({"command_timeout": 1})
        # sleep 5 会超时
        result = exe.execute("sleep 5")
        assert result["success"] is False
        assert result.get("timeout") is True


# ---------- execute_plan ----------
class TestExecutePlan:
    def test_execute_plan_all_success(self):
        exe = _make_executor()
        plan = {
            "tools": [
                {
                    "name": "tool1",
                    "install_commands": ["echo install1"],
                    "config_steps": ["echo config1"],
                    "run_commands": ["echo run1"],
                }
            ]
        }
        results = exe.execute_plan(plan)
        assert len(results) == 3
        assert all(r["success"] for r in results)

    def test_execute_plan_stop_on_failure(self):
        exe = _make_executor()
        plan = {
            "tools": [
                {
                    "name": "tool1",
                    "install_commands": ["echo step1", "exit 1", "echo step3"],
                    "config_steps": [],
                    "run_commands": [],
                }
            ]
        }
        results = exe.execute_plan(plan)
        # 应该在 exit 1 后停止，不会执行 step3
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False

    def test_execute_plan_skip_interactive_tool(self):
        exe = _make_executor()
        plan = {
            "tools": [
                {
                    "name": "claude",
                    "install_commands": [],
                    "config_steps": [],
                    "run_commands": ["npx @anthropic-ai/claude-code"],
                }
            ]
        }
        results = exe.execute_plan(plan)
        assert len(results) == 1
        assert results[0].get("skipped") is True
        # 启动命令被跳过不应该阻止后续（但这里只有一个 tool，所以没问题）

    def test_execute_plan_empty_tools(self):
        exe = _make_executor()
        plan = {"tools": []}
        results = exe.execute_plan(plan)
        assert results == []
