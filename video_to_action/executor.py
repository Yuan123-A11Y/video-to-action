"""命令执行与安装模块。"""

import logging
import re
import subprocess
from pathlib import Path

from video_to_action.utils import is_dangerous_command

logger = logging.getLogger(__name__)

# 已知的交互式工具（只安装，不自动执行）
INTERACTIVE_TOOLS = {
    "claude",
    "cursor",
    "codex",
    "windsurf",
    "github copilot",
    "tabnine",
    "codeium",
}

# 正确的安装命令前缀（用于校验 LLM 生成的命令是否合理）
INSTALL_PREFIXES = {
    "npm install",
    "pip install",
    "pip3 install",
    "brew install",
    "apt install",
    "yum install",
    "dnf install",
    "choco install",
    "winget install",
    "conda install",
    "cargo install",
    "go install",
    "curl",
    "wget",
    "git clone",
}


class Executor:
    """命令执行器，负责按行动计划执行安装和配置。"""

    def __init__(self, config: dict, output_dir: Path):
        """初始化执行器，加载安全配置与输出目录。"""
        self.config = config
        self.output_dir = output_dir
        self.safety = config.get("safety", {})
        # 命令执行超时（秒），可在 config 中覆盖
        self.timeout = self.safety.get("command_timeout", 300)

    def _needs_confirm(self, command: str) -> tuple[bool, str]:
        """检查命令是否需要用户确认，返回 (是否需要, 原因)。"""
        require_confirm = self.safety.get("require_confirm", [])
        command_lower = command.lower()

        if "run_remote_script" in require_confirm:
            # 匹配通过 curl/wget 下载并直接执行 shell 的远程脚本模式
            patterns = [
                r"curl\s+.*\|\s*(ba)?sh",
                r"wget\s+.*\|\s*sh",
                r"bash\s+<\s*\(curl",
                r"powershell\s+.*\|\s*iex",
            ]
            for pattern in patterns:
                if re.search(pattern, command_lower):
                    return True, "运行远程脚本"

        if "install_system_software" in require_confirm:
            # 匹配 Linux/macOS/Windows 下的系统软件安装命令
            if re.search(r"^(sudo\s+)?(apt|yum|dnf|brew|choco|winget)\s+install", command_lower):
                return True, "安装系统级软件"

        if "modify_system_env" in require_confirm:
            # 匹配修改系统环境变量的命令（command_lower 已转小写，用 path）
            if re.search(r"setx|setenv|export\s+path|修改环境变量", command_lower):
                return True, "修改系统环境变量"

        return False, ""

    def _is_interactive_tool(self, command: str) -> bool:
        """检测命令是否启动交互式工具（无法自动执行）。"""
        cmd_lower = command.lower()
        for tool in INTERACTIVE_TOOLS:
            if tool in cmd_lower:
                return True
        return False

    def _is_valid_install_command(self, command: str) -> bool:
        """校验命令是否是合理的安装命令，而非启动/运行命令。"""
        cmd_lower = command.lower().strip()
        # npx 用于临时运行包，不是安装命令，但也是合法命令，不应 warning
        if cmd_lower.startswith("npx "):
            return True
        for prefix in INSTALL_PREFIXES:
            if cmd_lower.startswith(prefix):
                return True
        return False

    def execute(self, command: str, confirm: bool = False) -> dict:
        """执行单条命令，先进行危险命令拦截与确认校验。

        改进点：
        - 添加命令执行超时（防止交互式工具挂起）
        - 检测交互式工具并跳过（返回清晰提示）
        - 校验安装命令格式（区分安装 vs 启动）
        """
        forbidden = self.safety.get("forbidden_keywords", [])
        if is_dangerous_command(command, forbidden):
            return {
                "success": False,
                "stdout": "",
                "stderr": (
                    "命令被拦截：包含危险操作关键词。\n"
                    "问题：命令中包含 forbidden_keywords 配置中的关键词。\n"
                    "建议：请检查命令是否包含 rm -rf /、dd if= 等危险操作。\n"
                    "如需允许该命令，请修改 config/safety.yaml 中的 forbidden_keywords。"
                ),
                "command": command,
            }

        needs_confirm, reason = self._needs_confirm(command)
        if needs_confirm and not confirm:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"命令需要用户确认：{reason}。请明确授权后再执行。",
                "command": command,
            }

        # 检测交互式工具（无法自动执行，跳过并给提示）
        if self._is_interactive_tool(command):
            tool_name = next(
                (t for t in INTERACTIVE_TOOLS if t in command.lower()),
                "未知工具",
            )
            return {
                "success": False,
                "skipped": True,
                "reason": "interactive_tool",
                "stdout": "",
                "stderr": (
                    f"跳过执行：{tool_name} 是交互式工具，"
                    f"无法在自动化流程中运行。\n"
                    f"请手动执行安装命令后，再启动 {tool_name}。"
                ),
                "command": command,
            }

        # 校验命令格式（警告但不阻止，LLM 可能生成不完美命令）
        if not self._is_valid_install_command(command):
            logger.warning("命令可能格式不正确（非标准安装命令）：%s", command)

        # 执行命令（使用 shell=False 避免命令注入，带超时）
        try:
            import shlex

            # shell=False 时需要将命令字符串拆分为参数列表
            args = shlex.split(command)
            result = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                encoding="utf-8",
                errors="ignore",
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": (
                    f"命令执行超时（{self.timeout}秒），已被终止。\n"
                    f"问题：命令在 {self.timeout} 秒内未完成执行。\n"
                    f"建议：1) 增加超时时间（修改 config/settings.yaml 中的 safety.command_timeout）\n"
                    f"      2) 检查命令是否需要交互式输入（如需，请手动执行）\n"
                    f"      3) 检查命令是否卡住（可手动运行该命令测试）"
                ),
                "command": command,
                "timeout": True,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": (
                    f"命令执行异常：{e}\n"
                    f"问题：命令执行过程中出现未预期的错误。\n"
                    f"建议：1) 检查命令格式是否正确（路径、参数等）\n"
                    f"      2) 检查命令是否需要安装依赖（如 pip install xxx）\n"
                    f"      3) 查看日志文件获取详细错误信息"
                ),
                "command": command,
                "exception": str(e),
            }

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
        }

    def execute_plan(self, plan: dict, confirm_all: bool = False) -> list[dict]:
        """执行完整的行动计划，按顺序运行安装命令、配置步骤和启动命令。

        执行顺序：
        1. install_commands（安装命令）
        2. config_steps（配置步骤）
        3. run_commands（启动/运行命令，交互式工具会自动跳过）
        """
        results = []
        tools = plan.get("tools", [])
        for tool in tools:
            # 1. 安装命令
            for command in tool.get("install_commands", []):
                result = self.execute(command, confirm=confirm_all)
                results.append(result)
                if not result["success"]:
                    return results

            # 2. 配置步骤
            for step in tool.get("config_steps", []):
                result = self.execute(step, confirm=confirm_all)
                results.append(result)
                if not result["success"]:
                    return results

            # 3. 启动命令（交互式工具会自动跳过）
            for command in tool.get("run_commands", []):
                result = self.execute(command, confirm=confirm_all)
                results.append(result)
                # 启动命令失败不阻止后续步骤（可能是交互式工具被跳过）
                if not result["success"] and not result.get("skipped"):
                    return results

        return results
