"""错误诊断与自动修复模块。"""

import re
from pathlib import Path


class Resolver:
    """错误修复器，根据命令和错误输出给出修复建议。"""

    def __init__(self, config: dict, output_dir: Path):
        """初始化错误修复器。

        Args:
            config: 项目配置字典。
            output_dir: 项目输出目录路径。
        """
        self.config = config
        self.output_dir = output_dir

    def suggest_fix(self, command: str, error_output: str) -> str | None:
        """根据执行的命令和错误输出，给出对应的修复建议。

        Args:
            command: 触发错误的原始命令。
            error_output: 命令执行后返回的错误信息。

        Returns:
            修复建议字符串；若无法识别则返回 None。
        """
        error_lower = error_output.lower()

        # pip 命令未找到
        if "command not found: pip" in error_lower or "pip 不是内部或外部命令" in error_lower:
            return "请确保 Python 和 pip 已安装，并将 Python Scripts 目录添加到 PATH"

        # 网络超时，切换到华为云镜像
        if any(keyword in error_lower for keyword in ["timed out", "timeout", "connection", "connect timeout"]):
            if command.startswith("pip"):
                return command + " -i https://mirrors.huaweicloud.com/repository/pypi/simple/"

        # 权限不足（Linux/macOS）
        if "permission denied" in error_lower:
            return f"尝试使用 sudo 执行：sudo {command}"

        # npm 命令未找到
        if "command not found: npm" in error_lower:
            return "请安装 Node.js 和 npm"

        # git 命令未找到
        if "command not found: git" in error_lower:
            return "请安装 Git"

        # ffmpeg 未找到
        if "ffmpeg" in error_lower and ("not found" in error_lower or "不是内部或外部命令" in error_lower):
            return "请安装 ffmpeg 并添加到 PATH"

        # yt-dlp 未找到
        if "yt-dlp" in error_lower and ("not found" in error_lower or "不是内部或外部命令" in error_lower):
            return "请安装 yt-dlp：pip install yt-dlp -i https://mirrors.huaweicloud.com/repository/pypi/simple/"

        return None

    def _extract_executable_command(self, suggestion: str) -> str | None:
        """从建议文本中提取可执行的命令。

        Args:
            suggestion: suggest_fix 返回的修复建议字符串。

        Returns:
            可执行命令字符串；若建议不可执行则返回 None。
        """
        if not suggestion:
            return None

        suggestion_stripped = suggestion.strip()

        # 直接以常见命令开头的建议可整体执行
        direct_prefixes = ("pip ", "npm ", "git ", "ffmpeg ", "yt-dlp ")
        if any(suggestion_stripped.startswith(prefix) for prefix in direct_prefixes):
            return suggestion_stripped

        # 提取 "尝试使用 sudo 执行：sudo xxx" 中的实际命令部分
        sudo_match = re.search(r"[：:]\s*(sudo\s+.+)", suggestion_stripped)
        if sudo_match:
            return sudo_match.group(1).strip()

        return None

    def resolve(self, command: str, error_output: str, attempt: int = 1) -> dict:
        """尝试诊断错误并返回修复结果。

        Args:
            command: 触发错误的原始命令。
            error_output: 命令执行后返回的错误信息。
            attempt: 当前修复尝试次数，默认为 1。

        Returns:
            包含修复状态、新命令（如有）和提示消息的字典。
        """
        suggestion = self.suggest_fix(command, error_output)
        if suggestion is None:
            return {
                "resolved": False,
                "executable": False,
                "new_command": None,
                "message": "无法自动诊断该错误，需要进一步排查。",
            }

        new_command = self._extract_executable_command(suggestion)
        if new_command:
            return {
                "resolved": True,
                "executable": True,
                "new_command": new_command,
                "message": f"检测到问题，建议执行修复命令：{new_command}",
            }

        return {
            "resolved": True,
            "executable": False,
            "new_command": None,
            "message": f"检测到问题，建议修复方案：{suggestion}",
        }
