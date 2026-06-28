"""交互式配置向导模块。

使用 rich 库提供友好的交互式配置体验。
"""

import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from video_to_action.config import DEFAULT_CONFIG, save_config

console = Console()


def run_wizard():
    """运行交互式配置向导。"""
    console.print("\n[bold blue]=== Video-to-Action 配置向导 ===[/bold blue]\n")
    console.print("欢迎使用 Video-to-Action 配置向导！")
    console.print("将引导您完成基本配置，预计需要 2-3 分钟。\n")

    config = DEFAULT_CONFIG.copy()

    # 1. LLM 配置
    console.print("[bold]步骤 1/4：LLM 配置[/bold]")
    console.print("LLM（大型语言模型）用于分析视频内容。\n")

    provider = Prompt.ask("选择 LLM 提供商", choices=["openai", "ollama", "other"], default="openai")
    config["llm"]["provider"] = provider

    if provider in ["openai", "other"]:
        api_key = Prompt.ask("请输入 API Key（留空则使用环境变量）", default="")
        if api_key:
            config["llm"]["api_key"] = api_key
        else:
            console.print("  → 将使用环境变量获取 API Key")

        base_url = Prompt.ask("API Base URL（可选）", default="")
        if base_url:
            config["llm"]["base_url"] = base_url

        model = Prompt.ask("模型名称", default="gpt-4o-mini")
        config["llm"]["model"] = model
    else:
        # Ollama 本地模型
        console.print("  → 将使用本地 Ollama 运行模型")
        model = Prompt.ask("Ollama 模型名称", default="llama3.1:8b")
        config["llm"]["model"] = model
        config["llm"]["base_url"] = "http://localhost:11434/v1"

    console.print("")

    # 2. 自动化级别
    console.print("[bold]步骤 2/4：自动化级别[/bold]")
    console.print("控制命令执行的自动化程度：")
    console.print("  • extract  - 仅提取内容，不调用 LLM")
    console.print("  • observe  - 仅分析，不执行命令")
    console.print("  • confirm  - 每步执行前需要确认")
    console.print("  • auto     - 全自动执行\n")

    level = Prompt.ask("选择自动化级别", choices=["extract", "observe", "confirm", "auto"], default="confirm")
    config["automation_level"] = level
    console.print("")

    # 3. 知识库配置
    console.print("[bold]步骤 3/4：知识库配置[/bold]")
    console.print("知识库用于存储分析过的视频和工具信息。\n")

    use_mysql = Confirm.ask("是否使用 MySQL 数据库？（默认使用 SQLite）", default=False)

    if use_mysql:
        console.print("  → 将配置 MySQL 数据库连接")
        mysql_host = Prompt.ask("MySQL 主机", default="localhost")
        mysql_port = Prompt.ask("MySQL 端口", default="3306")
        mysql_user = Prompt.ask("MySQL 用户名", default="root")
        mysql_password = Prompt.ask("MySQL 密码（可选）", password=True, default="")
        mysql_database = Prompt.ask("MySQL 数据库名", default="video_to_action")

        config["mysql"] = {
            "host": mysql_host,
            "port": int(mysql_port),
            "user": mysql_user,
            "password": mysql_password,
            "database": mysql_database,
        }
        console.print("  → MySQL 配置已设置")
    else:
        console.print("  → 将使用 SQLite 数据库（无需额外配置）")

    console.print("")

    # 4. 其他配置
    console.print("[bold]步骤 4/4：其他配置[/bold]")

    output_dir = Prompt.ask("输出目录", default="./outputs")
    config["output_dir"] = output_dir

    console.print("")

    # 显示配置摘要
    console.print("[bold green]配置摘要：[/bold green]\n")
    table = Table(show_header=False, box=None)
    table.add_column("配置项", style="cyan")
    table.add_column("值", style="white")

    table.add_row("LLM 提供商", config["llm"]["provider"])
    table.add_row("LLM 模型", config["llm"]["model"])
    table.add_row("自动化级别", config["automation_level"])
    table.add_row("输出目录", config["output_dir"])
    table.add_row("知识库", "MySQL" if use_mysql else "SQLite")

    console.print(table)
    console.print("")

    # 确认并保存
    if Confirm.ask("确认保存配置？", default=True):
        config_path = Prompt.ask("配置文件路径", default="config/settings.yaml")

        # 确保目录存在
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)

        # 保存配置
        save_config(config, config_path)
        console.print(f"\n[bold green]✅ 配置已保存到：{config_path}[/bold green]")
        console.print("\n接下来您可以：")
        console.print("  1. 运行 `python -m video_to_action.cli process <视频URL>` 处理视频")
        console.print("  2. 运行 `python -m video_to_action.cli search <关键词>` 搜索知识库")
        console.print("  3. 编辑配置文件进行高级配置\n")
    else:
        console.print("\n[yellow]已取消保存[/yellow]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run_wizard())
