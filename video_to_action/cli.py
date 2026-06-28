# g:\trae\video-to-action\video_to_action\cli.py
"""命令行入口 — 薄分发层。

子命令处理逻辑已拆分到独立模块：
- cli_process.py : process / batch 命令
- cli_kb.py      : search / export-handbook / kb-stats / clear-cache 命令
"""

import argparse
import logging
import sys

from video_to_action.cli_kb import (
    handle_clear_cache,
    handle_export_handbook,
    handle_kb_stats,
    handle_search,
)
from video_to_action.cli_process import handle_batch, handle_process
from video_to_action.config import load_config
from video_to_action.knowledge_base_factory import create_knowledge_base
from video_to_action.utils import setup_logging

logger = logging.getLogger(__name__)


def parse_arguments(argv: list[str] | None = None) -> "argparse.Namespace":
    """解析命令行参数。

    Args:
        argv: 命令行参数列表，默认为 None 时解析 sys.argv。

    Returns:
        解析后的命令行参数命名空间。
    """
    import argparse

    parser = argparse.ArgumentParser(description="视频到行动助手")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 主命令：处理视频
    process_parser = subparsers.add_parser("process", help="处理视频并生成行动计划")
    process_parser.add_argument("url", help="视频链接或本地视频路径")
    process_parser.add_argument(
        "--level",
        choices=["extract", "observe", "confirm", "auto"],
        default="auto",
        help="自动化级别",
    )
    process_parser.add_argument("--config", default=None, help="配置文件路径")
    process_parser.add_argument("--output", default="outputs", help="输出目录")
    process_parser.add_argument("--save-to-kb", action="store_true", help="保存分析结果到知识库")
    process_parser.add_argument("--verbose", action="store_true", help="输出详细调试信息")
    process_parser.add_argument("--warmup", action="store_true", help="预热 LLM 和转写模型（减少首次处理延迟）")

    # 搜索命令
    search_parser = subparsers.add_parser("search", help="搜索知识库")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--type", choices=["video", "tool"], default="video", help="搜索类型")
    search_parser.add_argument("--limit", type=int, default=10, help="结果数量限制")

    # 导出手册命令
    export_parser = subparsers.add_parser("export-handbook", help="导出操作手册")
    export_parser.add_argument("--output", default=None, help="输出文件路径")

    # 统计命令
    stats_parser = subparsers.add_parser("kb-stats", help="显示知识库统计信息")  # noqa: F841

    # 清除缓存命令
    clear_cache_parser = subparsers.add_parser("clear-cache", help="清除分析器缓存")  # noqa: F841

    # 配置向导命令
    setup_parser = subparsers.add_parser("setup", help="交互式配置向导")  # noqa: F841

    # 批量处理命令
    batch_parser = subparsers.add_parser("batch", help="批量处理多个视频")
    batch_parser.add_argument("url_file", help="包含视频URL的文件路径（每行一个URL）")
    batch_parser.add_argument(
        "--level", choices=["extract", "observe", "confirm", "auto"], default="auto", help="自动化级别"
    )
    batch_parser.add_argument("--config", default=None, help="配置文件路径")
    batch_parser.add_argument("--output", default="outputs", help="输出目录")
    batch_parser.add_argument("--save-to-kb", action="store_true", help="保存分析结果到知识库")
    batch_parser.add_argument("--workers", type=int, default=1, help="并发工作数（暂未实现，保留参数）")
    batch_parser.add_argument("--verbose", action="store_true", help="输出详细调试信息")

    # 全局参数（适用于所有子命令）
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--verbose", action="store_true", help="输出详细调试信息")

    # 兼容旧版用法（直接跟URL）—— 在解析前预处理 argv
    if argv and len(argv) > 0:
        first_arg = argv[0]
        # 如果不以 "-" 开头，且不是已知的子命令，则认为是 URL
        known_commands = ["process", "search", "export-handbook", "kb-stats", "clear-cache", "setup", "batch"]
        if not first_arg.startswith("-") and first_arg not in known_commands:
            # 在开头插入 "process"
            argv = ["process"] + argv

    args = parser.parse_args(argv)

    return args


def main(argv: list[str] | None = None) -> int:
    """主入口函数 — 薄分发层，按子命令调用对应处理器。

    Args:
        argv: 命令行参数列表，为 None 时解析 sys.argv。

    Returns:
        程序退出码，0 表示成功，1 表示失败。
    """
    args = parse_arguments(argv)

    # 初始化日志系统
    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    setup_logging(level=log_level, log_file="outputs/video_to_action.log")
    logger.info("视频到行动助手启动")
    if log_level == logging.DEBUG:
        logger.debug("调试模式已启用")

    # 加载配置
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error("❌ 加载配置失败：%s", e)
        logger.error("建议：请检查配置文件路径和内容格式是否正确")
        return 1

    # 初始化知识库
    try:
        kb = create_knowledge_base()
    except Exception as e:
        logger.warning("⚠️ 知识库初始化失败：%s", e)
        kb = None

    # 按子命令分发
    if args.command == "search":
        return handle_search(args, kb)

    if args.command == "export-handbook":
        return handle_export_handbook(args, kb)

    if args.command == "kb-stats":
        return handle_kb_stats(args, kb)

    if args.command == "clear-cache":
        return handle_clear_cache()

    if args.command == "setup":
        return _handle_setup()

    if args.command == "batch":
        return handle_batch(args, config, log_level)

    if args.command == "process" or hasattr(args, "url"):
        return handle_process(args, config, kb, log_level)

    # 没有匹配的子命令，显示帮助
    print("请使用子命令：process, search, export-handbook, kb-stats, batch")
    return 1


def _handle_setup() -> int:
    """处理 setup 子命令：交互式配置向导。"""
    try:
        from video_to_action.config_wizard import run_wizard

        run_wizard()
        return 0
    except Exception as e:
        logger.error("❌ 配置向导失败：%s", e)
        return 1


if __name__ == "__main__":
    # Windows 下设置 stdout/stderr 为 UTF-8 编码，避免 emoji 显示错误
    if sys.platform == "win32":
        try:
            # 使用 reconfigure() 更安全（Python 3.7+）
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
                sys.stderr.reconfigure(encoding="utf-8")
            else:
                # 旧版本 Python 的回退方案
                import codecs
                sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
                sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
        except Exception:
            # 如果设置失败，继续执行（可能影响 emoji 显示）
            pass

    sys.exit(main())
