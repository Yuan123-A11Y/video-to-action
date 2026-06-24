"""中文操作笔记生成模块。"""

import time
from pathlib import Path


class Reporter:
    """报告生成器。"""

    def __init__(self, config: dict, output_dir: Path):
        """初始化报告生成器。

        Args:
            config: 全局配置字典。
            output_dir: 输出目录路径。
        """
        self.config = config
        self.output_dir = output_dir
        self.reports_dir = output_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    def _format_execution_results(self, results: list[dict]) -> str:
        """格式化执行结果为 Markdown 字符串。

        Args:
            results: 执行结果列表，每个结果包含 success、command、stdout、stderr。

        Returns:
            格式化后的 Markdown 字符串。
        """
        lines = []
        for idx, result in enumerate(results, 1):
            status = "成功" if result["success"] else "失败"
            lines.append(f"### 步骤 {idx}：{status}")
            lines.append(f"- 命令：`{result['command']}`")
            if result["stdout"]:
                lines.append(f"- 输出：\n```\n{result['stdout']}\n```")
            if result["stderr"]:
                lines.append(f"- 错误：\n```\n{result['stderr']}\n```")
        return "\n\n".join(lines)

    def generate(self, context: dict) -> Path:
        """生成 Markdown 格式中文报告。

        Args:
            context: 执行上下文，包含视频信息、计划、执行结果等。

        Returns:
            生成的报告文件路径。
        """
        plan = context.get("plan", {})
        tools = plan.get("tools", [])
        results = context.get("execution_results", [])

        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        if failed == 0 and len(results) > 0:
            final_status = "成功"
        elif successful > 0:
            final_status = "部分成功"
        else:
            final_status = "失败"

        lines = [
            "# 视频到行动助手 - 执行报告",
            "",
            "## 视频信息",
            f"- 视频链接：{context.get('video_url', '')}",
            f"- 视频平台：{context.get('platform', '')}",
            f"- 下载方式：{context.get('download_method', '')}",
            f"- 本地视频：{context.get('video_path', '')}",
            "",
            "## 视频内容摘要",
            f"- 主题：{plan.get('theme', '')}",
            "",
            f"{plan.get('summary', '')}",
            "",
            "## 涉及工具",
        ]
        for tool in tools:
            lines.append(f"### {tool.get('name', '未命名')}")
            lines.append(f"- 用途：{tool.get('purpose', '')}")
            if tool.get("links"):
                lines.append(f"- 链接：{', '.join(tool['links'])}")
            if tool.get("warnings"):
                lines.append(f"- 注意：{'；'.join(tool['warnings'])}")

        lines.extend([
            "",
            "## 执行过程",
            self._format_execution_results(results),
            "",
            "## 执行结果",
            f"- 总步骤数：{len(results)}",
            f"- 成功：{successful}",
            f"- 失败：{failed}",
            f"- 最终状态：**{final_status}**",
            "",
            "## 后续建议",
            "- 请检查上述输出，确认工具已按预期安装",
            "- 如果某步骤失败，可根据错误信息手动修复或重新运行",
        ])

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"report_{timestamp}.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path
