# g:\trae\video-to-action\video_to_action\cli.py
"""命令行入口，串联视频下载、内容提取、分析、执行与报告全流程。"""

import argparse
import json
import logging
import sys
from pathlib import Path

import httpx

from video_to_action.analyzer_v2 import AnalyzerV2
from video_to_action.config import get_output_dir, load_config
from video_to_action.downloader import download_video
from video_to_action.executor import Executor
from video_to_action.extractor import Extractor
from video_to_action.knowledge_base import KnowledgeBase
from video_to_action.reporter import Reporter
from video_to_action.resolver import Resolver
from video_to_action.utils import setup_logging

logger = logging.getLogger(__name__)


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。

    Args:
        argv: 命令行参数列表，默认为 None 时解析 sys.argv。

    Returns:
        解析后的命令行参数命名空间。
    """
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

    # 如果不使用子命令，兼容旧版用法（直接跟URL）
    parser.add_argument("url_positional", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument(
        "--level",
        choices=["extract", "observe", "confirm", "auto"],
        default="auto",
        help="自动化级别",
    )
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--output", default="outputs", help="输出目录")
    parser.add_argument("--save-to-kb", action="store_true", help="保存分析结果到知识库")
    parser.add_argument("--verbose", action="store_true", help="输出详细调试信息")

    args = parser.parse_args(argv)

    # 兼容旧版：如果第一个位置参数是URL，则设置为process命令
    if args.command is None and args.url_positional:
        args.command = "process"
        args.url = args.url_positional
        del args.url_positional

    return args


def _get_local_or_download(url: str, config: dict, output_dir: Path) -> tuple[dict, Path]:
    """根据输入 URL 下载视频或直接使用本地文件。

    Returns:
        (download_result, video_path) 元组。
    """
    local_path = Path(url)
    if local_path.exists() and local_path.is_file():
        video_path = local_path.resolve()
        print(f"使用本地视频：{video_path}")
        download_result = {
            "success": True,
            "platform": "local",
            "method": "local",
            "output_path": str(video_path),
            "stdout": "",
            "stderr": "",
        }
        return download_result, video_path

    print("[1/5] 正在下载视频...")
    download_result = download_video(url, config, output_dir)
    if not download_result["success"]:
        print(f"下载失败：{download_result['stderr']}")
        raise RuntimeError("视频下载失败")
    print(f"下载成功：{download_result['output_path']}")
    return download_result, Path(download_result["output_path"])


def _extract_content(video_path: Path, config: dict, output_dir: Path) -> dict:
    """提取视频音频、转写文本和关键帧。"""
    print("[2/5] 正在提取音频和转写文本...")
    extractor = Extractor(config, output_dir)
    extracted = extractor.process(video_path)
    print(f"转写完成，共 {len(extracted.get('segments', []))} 个片段")
    print(f"关键帧已保存：{len(extracted.get('frames', []))} 张")
    return extracted


def _format_trae_prompt(extracted: dict, platform: str) -> str:
    """生成供 Trae 自身大模型分析的 Prompt。"""
    text = extracted.get("text", "")
    frames = "\n".join(f"- {path}" for path in extracted.get("frames", []))
    return f"""请根据以下从{platform}视频提取的内容，分析视频中介绍的工具、软件或方法，并给出结构化的行动计划。

## 视频转录文本
{text}

## 关键帧截图路径
{frames if frames else "无"}

请输出 JSON 格式，包含以下字段：
- theme: 视频主题（中文）
- summary: 视频内容摘要（中文，200字以内）
- tools: 工具列表，每个工具包含：
  - name: 工具名称
  - purpose: 工具用途（中文）
  - links: 相关链接列表（GitHub、官网等）
  - install_commands: 安装命令列表
  - config_steps: 配置步骤列表
  - warnings: 注意事项列表
- needs_credential: 是否需要密码/密钥/Token（true/false）
- is_paid: 是否需要付费（true/false）
- alternative_tools: 如果主工具失效，可替代的开源免费工具列表

只输出 JSON，不要输出其他解释文字。"""


def main(argv: list[str] | None = None) -> int:
    """主入口函数，按顺序执行视频处理流水线或知识库操作。

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

    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error("❌ 加载配置失败：%s", e)
        logger.error("建议：请检查配置文件路径和内容格式是否正确")
        return 1

    # 初始化知识库
    try:
        kb = KnowledgeBase()
    except Exception as e:
        logger.warning("⚠️ 知识库初始化失败：%s", e)
        kb = None

    # 处理子命令
    if args.command == "search":
        if kb is None:
            logger.error("❌ 知识库不可用，无法执行搜索")
            return 1
        print(f"搜索：{args.query} (类型：{args.type})")
        try:
            if args.type == "video":
                results = kb.search_videos(args.query, limit=args.limit)
                for r in results:
                    print(f"  - [{r['platform']}] {r.get('title') or r['theme']}")
            else:
                results = kb.search_tools(args.query, limit=args.limit)
                for r in results:
                    print(f"  - {r['name']}: {r['purpose']}")
        except Exception as e:
            logger.error("❌ 搜索失败：%s", e)
            return 1
        return 0

    if args.command == "export-handbook":
        if kb is None:
            logger.error("❌ 知识库不可用，无法导出手册")
            return 1
        try:
            output_path = Path(args.output) if args.output else None
            path = kb.export_handbook(output_path)
            print(f"操作手册已导出：{path}")
        except Exception as e:
            logger.error("❌ 导出手册失败：%s", e)
            return 1
        return 0

    if args.command == "kb-stats":
        if kb is None:
            logger.error("❌ 知识库不可用，无法查看统计")
            return 1
        try:
            stats = kb.get_statistics()
            print(f"视频数量：{stats['video_count']}")
            print(f"工具数量：{stats['tool_count']}")
            print("平台分布：")
            for platform in stats["platform_stats"]:
                print(f"  - {platform['platform']}: {platform['count']} 个")
        except Exception as e:
            logger.error("❌ 获取统计信息失败：%s", e)
            return 1
        return 0

    # 主命令：处理视频
    if args.command == "process" or hasattr(args, "url"):
        # 命令行 --output 参数优先于配置文件
        if hasattr(args, "output") and args.output:
            config["output_dir"] = args.output
        output_dir = get_output_dir(config)

        print(f"开始处理：{args.url}")
        logger.info("处理 URL：%s", args.url)

        try:
            # 步骤 1：获取视频
            download_result, video_path = _get_local_or_download(args.url, config, output_dir)
            logger.info("视频获取成功：%s", video_path)

            # 步骤 2：提取内容
            extracted = _extract_content(video_path, config, output_dir)
            logger.info("内容提取完成，共 %d 个片段", len(extracted.get("segments", [])))

            # extract 模式：输出转录文本和 Trae Prompt，不调用 LLM
            if args.level == "extract":
                print("\n=== 提取模式：以下内容可复制给 Trae 进行深度分析 ===\n")
                print("【视频转录文本】")
                print(extracted["text"])
                print("\n【供 Trae 分析的 Prompt】")
                print(_format_trae_prompt(extracted, download_result["platform"]))
                return 0

            # 步骤 3：分析内容
            print("[3/5] 正在分析视频内容...")
            logger.info("开始分析视频内容")
            analyzer = AnalyzerV2(config)
            frames = extracted.get("frames", [])
            plan = analyzer.analyze(
                extracted.get("text", ""),
                download_result["platform"],
                frames=frames if frames else None,
            )

            print(f"分析完成，主题：{plan.get('theme', '未知')}")
            logger.info("分析完成，主题：%s", plan.get("theme", "未知"))

            # 保存到知识库
            if kb is not None and hasattr(args, "save_to_kb") and args.save_to_kb:
                print("正在保存到知识库...")
                try:
                    video_id = kb.add_video_analysis(
                        url=args.url,
                        platform=download_result["platform"],
                        title=None,  # 可以从下载结果中获取
                        theme=plan.get("theme", ""),
                        summary=plan.get("summary", ""),
                        transcription_text=extracted.get("text", ""),
                        analysis_result=plan,
                    )
                    print(f"已保存到知识库，视频ID：{video_id}")
                    logger.info("已保存到知识库，视频ID：%s", video_id)
                except Exception as e:
                    logger.warning("⚠️ 保存到知识库失败：%s", e)

            # 观察模式不执行
            if args.level == "observe":
                print("\n观察模式：仅输出分析结果")
                print(json.dumps(plan, ensure_ascii=False, indent=2))
                return 0

            # 步骤 4：执行计划
            print("[4/5] 正在执行安装/配置...")
            logger.info("开始执行行动计划")
            executor = Executor(config, output_dir)
            confirm_all = args.level == "confirm"
            execution_results = executor.execute_plan(plan, confirm_all=confirm_all)

            # 自动修复失败的步骤
            resolver = Resolver(config, output_dir)
            for result in execution_results:
                if not result["success"]:
                    try:
                        fix = resolver.resolve(result["command"], result["stderr"])
                        if fix["resolved"]:
                            if fix.get("executable") and fix.get("new_command"):
                                print(f"尝试修复：{fix['message']}")
                                logger.info("尝试修复命令：%s", fix["message"])
                                fixed_result = executor.execute(fix["new_command"], confirm=confirm_all)
                                result["fixed_result"] = fixed_result
                            else:
                                print(f"修复建议（未自动执行）：{fix['message']}")
                                logger.info("修复建议：%s", fix["message"])
                    except Exception as e:
                        logger.warning("⚠️ 自动修复失败：%s", e)

            # 步骤 5：生成报告
            print("[5/5] 正在生成中文操作笔记...")
            logger.info("开始生成报告")
            reporter = Reporter(config, output_dir)
            context = {
                "video_url": args.url,
                "platform": download_result["platform"],
                "download_method": download_result["method"],
                "video_path": str(video_path),
                "plan": plan,
                "execution_results": execution_results,
            }
            report_path = reporter.generate(context)
            print(f"报告已生成：{report_path}")
            logger.info("报告已生成：%s", report_path)
            return 0

        except RuntimeError as e:
            logger.error("❌ 视频下载失败：%s", e)
            logger.error("建议：请检查视频链接是否有效，或尝试使用代理")
            return 1
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 500:
                logger.error("❌ LLM API 返回 500 错误，可能是文本过长")
                logger.error("建议：1) 缩短视频长度 2) 升级 LLM 模型 3) 联系 API 提供商")
            else:
                logger.error("❌ HTTP 错误：%s", e)
            return 1
        except Exception as e:
            logger.error("❌ 处理过程中出现错误：%s", e)
            logger.debug("错误详情：", exc_info=True)
            logger.error("请查看日志文件或联系开发者")
            return 1

    # 如果没有匹配的子命令，显示帮助
    print("请使用子命令：process, search, export-handbook, kb-stats")
    return 1


if __name__ == "__main__":
    sys.exit(main())
