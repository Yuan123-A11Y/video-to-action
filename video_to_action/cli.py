# g:\trae\video-to-action\video_to_action\cli.py
"""命令行入口，串联视频下载、内容提取、分析、执行与报告全流程。"""

import argparse
import sys
from pathlib import Path

from video_to_action.analyzer import Analyzer
from video_to_action.config import get_output_dir, load_config
from video_to_action.downloader import download_video
from video_to_action.executor import Executor
from video_to_action.extractor import Extractor
from video_to_action.reporter import Reporter
from video_to_action.resolver import Resolver


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。

    Args:
        argv: 命令行参数列表，默认为 None 时解析 sys.argv。

    Returns:
        解析后的命令行参数命名空间。
    """
    parser = argparse.ArgumentParser(description="视频到行动助手")
    parser.add_argument("url", help="视频链接或本地视频路径")
    parser.add_argument(
        "--level",
        choices=["observe", "confirm", "auto"],
        default="auto",
        help="自动化级别：observe 仅观察分析结果，confirm 全部确认后执行，auto 自动执行",
    )
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--output", default="outputs", help="输出目录")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """主入口函数，按顺序执行视频处理流水线。

    Args:
        argv: 命令行参数列表，为 None 时解析 sys.argv。

    Returns:
        程序退出码，0 表示成功，1 表示失败。
    """
    args = parse_arguments(argv)

    config = load_config(args.config)
    output_dir = get_output_dir(config)

    print(f"开始处理视频：{args.url}")

    # 步骤 1：下载视频
    print("[1/5] 正在下载视频...")
    download_result = download_video(args.url, config, output_dir)
    if not download_result["success"]:
        print(f"下载失败：{download_result['stderr']}")
        return 1
    print(f"下载成功：{download_result['output_path']}")

    video_path = Path(download_result["output_path"])

    # 步骤 2：提取内容
    print("[2/5] 正在提取音频和转写文本...")
    extractor = Extractor(config, output_dir)
    extracted = extractor.process(video_path)
    print(f"转写完成，共 {len(extracted['segments'])} 个片段")

    # 步骤 3：分析内容
    print("[3/5] 正在分析视频内容...")
    analyzer = Analyzer(config)
    plan = analyzer.analyze(extracted["text"], download_result["platform"])
    print(f"分析完成，主题：{plan.get('theme', '未知')}")

    # 观察模式不执行
    if args.level == "observe":
        print("\n观察模式：仅输出分析结果")
        print(plan)
        return 0

    # 步骤 4：执行计划
    print("[4/5] 正在执行安装/配置...")
    executor = Executor(config, output_dir)
    confirm_all = args.level == "confirm"
    execution_results = executor.execute_plan(plan, confirm_all=confirm_all)

    # 自动修复失败的步骤
    resolver = Resolver(config, output_dir)
    for result in execution_results:
        if not result["success"]:
            fix = resolver.resolve(result["command"], result["stderr"])
            if fix["resolved"]:
                print(f"尝试修复：{fix['message']}")
                fixed_result = executor.execute(fix["new_command"], confirm=confirm_all)
                result["fixed_result"] = fixed_result

    # 步骤 5：生成报告
    print("[5/5] 正在生成中文操作笔记...")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
