"""操作手册导出模块 - 将知识库数据导出为 Markdown 格式。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from video_to_action.base_knowledge_base import BaseKnowledgeBase


def _safe_json_loads(value, default=None):
    """安全解析 JSON，失败则返回默认值。"""
    if not value:
        return default if default is not None else []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def export_handbook(kb: BaseKnowledgeBase, output_path: Optional[Path] = None) -> Path:
    """导出操作手册（Markdown 格式）。

    Args:
        kb: BaseKnowledgeBase 实例（支持 SQLite 和 MySQL）
        output_path: 输出文件路径，默认为 outputs/handbook.md

    Returns:
        输出文件路径
    """
    if output_path is None:
        output_path = Path("outputs") / "handbook.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 调用知识库方法获取数据（数据库无关）
    data = kb.get_tools_with_videos()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 视频知识库操作手册\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        for item in data:
            tool = item["tool"]
            videos = item["videos"]

            f.write(f"## {tool['name']}\n\n")
            f.write(f"**用途**：{tool['purpose']}\n\n")

            if tool["install_commands"]:
                install_cmds = _safe_json_loads(tool["install_commands"], default=[])
                if install_cmds:
                    f.write("**安装命令**：\n")
                    for cmd in install_cmds:
                        f.write(f"- `{cmd}`\n")
                    f.write("\n")

            if tool["config_steps"]:
                config_steps = _safe_json_loads(tool["config_steps"], default=[])
                if config_steps:
                    f.write("**配置步骤**：\n")
                    for step in config_steps:
                        f.write(f"- {step}\n")
                    f.write("\n")

            if tool["warnings"]:
                warnings = _safe_json_loads(tool["warnings"], default=[])
                if warnings:
                    f.write("**注意事项**：\n")
                    for warning in warnings:
                        f.write(f"- ⚠️ {warning}\n")
                    f.write("\n")

            if tool["alternatives"]:
                alternatives = _safe_json_loads(tool["alternatives"], default=[])
                if alternatives:
                    f.write(f"**替代工具**：{', '.join(alternatives)}\n\n")

            if videos:
                f.write("**相关视频**：\n")
                for video in videos:
                    f.write(f"- [{video['platform']}] {video['title'] or video['theme']}\n")
                f.write("\n")

            f.write("---\n\n")

    return output_path
