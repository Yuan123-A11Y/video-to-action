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
        choices=["extract", "observe", "confirm", "auto"],
        default="auto",
        help="自动化级别：extract 仅提取文本供 Trae 分析，observe 仅观察分析结果，confirm 全部确认后执行，auto 自动执行",
    )
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--output", default="outputs", help="输出目录")
    return parser.parse_args(argv)


def _get_local_or_download(
    url: str, config: dict, output_dir: Path
) -> tuple[dict, Path]:
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
    print(f"转写完成，共 {len(extracted['segments'])} 个片段")
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
    """主入口函数，按顺序执行视频处理流水线。

    Args:
        argv: 命令行参数列表，为 None 时解析 sys.argv。

    Returns:
        程序退出码，0 表示成功，1 表示失败。
    """
    args = parse_arguments(argv)

    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"加载配置失败：{e}")
        return 1

    # 命令行 --output 参数优先于配置文件
    if args.output:
        config["output_dir"] = args.output
    output_dir = get_output_dir(config)

    print(f"开始处理：{args.url}")

    try:
        # 步骤 1：获取视频
        download_result, video_path = _get_local_or_download(
            args.url, config, output_dir
        )

        # 步骤 2：提取内容
        extracted = _extract_content(video_path, config, output_dir)

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
                    if fix.get("executable") and fix.get("new_command"):
                        print(f"尝试修复：{fix['message']}")
                        fixed_result = executor.execute(
                            fix["new_command"], confirm=confirm_all
                        )
                        result["fixed_result"] = fixed_result
                    else:
                        print(f"修复建议（未自动执行）：{fix['message']}")

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
    except Exception as e:
        print(f"处理过程中出现错误：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
