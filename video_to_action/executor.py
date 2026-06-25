"""命令执行与安装模块。"""

import re
import subprocess
from pathlib import Path

from video_to_action.utils import is_dangerous_command


class Executor:
    """命令执行器，负责按行动计划执行安装和配置。"""

    def __init__(self, config: dict, output_dir: Path):
        """初始化执行器，加载安全配置与输出目录。"""
        self.config = config
        self.output_dir = output_dir
        self.safety = config.get("safety", {})

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
            # 匹配修改系统环境变量的命令
            if re.search(r"setx|setenv|export\s+PATH|修改环境变量", command_lower):
                return True, "修改系统环境变量"

        return False, ""

    def execute(self, command: str, confirm: bool = False) -> dict:
        """执行单条命令，先进行危险命令拦截与确认校验。"""
        forbidden = self.safety.get("forbidden_keywords", [])
        if is_dangerous_command(command, forbidden):
            return {
                "success": False,
                "stdout": "",
                "stderr": "命令被拦截：包含危险操作关键词",
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

        # 使用 GBK 编码读取输出（兼容中文 Windows）
        # 如果解码失败，使用 UTF-8 并忽略错误
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore"
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
        }

    def execute_plan(self, plan: dict, confirm_all: bool = False) -> list[dict]:
        """执行完整的行动计划，按顺序运行安装命令与配置步骤。"""
        results = []
        tools = plan.get("tools", [])
        for tool in tools:
            for command in tool.get("install_commands", []):
                result = self.execute(command, confirm=confirm_all)
                results.append(result)
                if not result["success"]:
                    return results
            for step in tool.get("config_steps", []):
                result = self.execute(step, confirm=confirm_all)
                results.append(result)
                if not result["success"]:
                    return results
        return results
