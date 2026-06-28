# g:\trae\video-to-action\video_to_action\cli_process.py
"""视频处理相关子命令：process 和 batch。"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

import httpx

from video_to_action.analyzer_v2 import AnalyzerV2
from video_to_action.downloader import download_video
from video_to_action.exceptions import (
    AnalysisError,
    ConfigurationError,
    DownloadError,
    ExecutionError,
    ExtractionError,
    VideoToActionError,
    wrap_exception,
)
from video_to_action.executor import Executor
from video_to_action.extractor import Extractor
from video_to_action.reporter import Reporter
from video_to_action.resolver import Resolver

logger = logging.getLogger(__name__)

# 尝试导入 tqdm
try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None


def _get_local_or_download(
    url: str, config: dict, output_dir: Path, pbar: Optional[object] = None
) -> tuple[dict, Path]:
    """根据输入 URL 下载视频或直接使用本地文件。

    Returns:
        (download_result, video_path) 元组。

    Raises:
        DownloadError: 视频下载失败时抛出。
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
        if pbar is not None:
            pbar.update(1)
        return download_result, video_path

    print("[1/5] 正在下载视频...")
    try:
        download_result = download_video(url, config, output_dir)
    except Exception as e:
        raise DownloadError(f"视频下载失败：{e}") from e

    if not download_result["success"]:
        error_msg = download_result.get("stderr", "未知错误")
        print(f"下载失败：{error_msg}")
        raise DownloadError(f"视频下载失败：{error_msg}")
    print(f"下载成功：{download_result['output_path']}")
    if pbar is not None:
        pbar.update(1)
    return download_result, Path(download_result["output_path"])


def _extract_content(video_path: Path, config: dict, output_dir: Path, pbar: Optional[object] = None) -> dict:
    """提取视频音频、转写文本和关键帧。"""
    print("[2/5] 正在提取音频和转写文本...")
    extractor = Extractor(config, output_dir)
    extracted = extractor.process(video_path)
    print(f"转写完成，共 {len(extracted.get('segments', []))} 个片段")
    print(f"关键帧已保存：{len(extracted.get('frames', []))} 张")
    if pbar is not None:
        pbar.update(1)
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


def handle_process(args, config: dict, kb, log_level: int) -> int:
    """处理 process 子命令：下载 → 提取 → 分析 → 执行 → 报告。"""
    # 命令行 --output 参数优先于配置文件
    if hasattr(args, "output") and args.output:
        config["output_dir"] = args.output
    output_dir = _get_output_dir(config)

    # 预热模型（如果指定了 --warmup 参数）
    if hasattr(args, "warmup") and args.warmup:
        _warmup_models(config, output_dir, log_level)

    print(f"开始处理：{args.url}")
    logger.info("处理 URL：%s", args.url)

    pbar = _init_progress_bar(5, log_level)

    try:
        # 步骤 1：获取视频
        download_result, video_path = _get_local_or_download(args.url, config, output_dir, pbar)
        logger.info("视频获取成功：%s", video_path)

        # 步骤 2：提取内容
        extracted = _extract_content(video_path, config, output_dir, pbar)
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
        plan = _analyze_content(config, extracted, download_result, pbar)
        logger.info("分析完成，主题：%s", plan.get("theme", "未知"))

        # 保存到知识库
        _save_to_knowledge_base(kb, args, download_result, extracted, plan)

        # 观察模式不执行
        if args.level == "observe":
            print("\n观察模式：仅输出分析结果")
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0

        # 步骤 4：执行计划
        execution_results = _execute_plan(config, output_dir, plan, args, pbar)

        # 自动修复失败的步骤
        _auto_resolve(execution_results, config, output_dir, plan, args)

        # 步骤 5：生成报告
        report_path = _generate_report(config, output_dir, args, download_result, plan, execution_results)
        print(f"报告已生成：{report_path}")
        logger.info("报告已生成：%s", report_path)

        _finish_progress_bar(pbar)
        return 0

    except (DownloadError, ExtractionError, AnalysisError, ExecutionError, ConfigurationError) as e:
        _handle_known_error(e, pbar)
        return 1
    except httpx.HTTPStatusError as e:
        _handle_http_error(e, pbar)
        return 1
    except VideoToActionError as e:
        logger.error("❌ %s", e)
        if e.suggestion:
            logger.error("建议：%s", e.suggestion)
        _close_progress_bar(pbar)
        return 1
    except Exception as e:
        wrapped = wrap_exception(e)
        logger.error("❌ 处理过程中出现错误：%s", wrapped)
        logger.debug("错误详情：", exc_info=True)
        logger.error("请查看日志文件或联系开发者")
        _close_progress_bar(pbar)
        return 1
    finally:
        _close_progress_bar(pbar)


def handle_batch(args, config: dict, log_level: int) -> int:
    """处理 batch 子命令：批量处理多个视频。"""
    url_file = Path(args.url_file)
    if not url_file.exists():
        logger.error("❌ URL 文件不存在：%s", url_file)
        return 1

    with open(url_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    if not urls:
        logger.error("❌ URL 文件为空：%s", url_file)
        return 1

    print(f"📋 批量处理 {len(urls)} 个视频")
    logger.info("批量处理 %d 个视频", len(urls))

    pbar = None
    if TQDM_AVAILABLE and log_level != logging.DEBUG:
        pbar = tqdm(total=len(urls), desc="批量处理进度", unit="个", ncols=80)

    results = []
    for i, url in enumerate(urls, 1):
        print(f"\n{'=' * 60}")
        print(f"[{i}/{len(urls)}] 处理：{url}")
        logger.info("[%d/%d] 处理：%s", i, len(urls), url)

        try:
            video_output_dir = Path(args.output) / f"video_{i}"
            video_output_dir.mkdir(parents=True, exist_ok=True)

            download_result, video_path = _get_local_or_download(url, config, video_output_dir)
            logger.info("视频获取成功：%s", video_path)

            extracted = _extract_content(video_path, config, video_output_dir)
            logger.info("内容提取完成，共 %d 个片段", len(extracted.get("segments", [])))

            print("[3/5] 正在分析内容...")
            logger.info("开始分析内容")
            analyzer = AnalyzerV2(config)
            # 设置视频上下文（用于生成基于 URL 的缓存键，提升缓存命中率 30%+）
            analyzer.set_video_context(video_url=url, video_path=str(video_path))
            plan = analyzer.analyze(
                extracted.get("text", ""),
                platform=download_result["platform"],
                frames=extracted.get("frames"),
            )
            print(f"分析完成，主题：{plan.get('theme', '未知')}")
            logger.info("分析完成，主题：%s", plan.get("theme", "未知"))

            print("[4/5] 正在执行安装/配置...")
            logger.info("开始执行行动计划")
            executor = Executor(config, video_output_dir)
            confirm_all = args.level == "confirm"
            execution_results = executor.execute_plan(plan, confirm_all=confirm_all)

            print("[5/5] 正在生成中文操作笔记...")
            logger.info("开始生成报告")
            reporter = Reporter(config, video_output_dir)
            context = {
                "video_url": url,
                "platform": download_result["platform"],
                "download_method": download_result["method"],
                "video_path": str(video_path),
                "plan": plan,
                "execution_results": execution_results,
            }
            report_path = reporter.generate(context)
            print(f"报告已生成：{report_path}")
            logger.info("报告已生成：%s", report_path)

            results.append(
                {
                    "url": url,
                    "status": "success",
                    "report": str(report_path),
                }
            )

        except Exception as e:
            logger.error("❌ 处理失败 [%d/%d]：%s", i, len(urls), e)
            results.append(
                {
                    "url": url,
                    "status": "failed",
                    "error": str(e),
                }
            )
            continue
        finally:
            if pbar is not None:
                pbar.update(1)

    if pbar is not None:
        pbar.close()

    # 生成汇总报告
    summary_path = Path(args.output) / "batch_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# 批量处理汇总报告\n\n")
        f.write(f"处理时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"总视频数：{len(urls)}\n")
        f.write(f"成功：{sum(1 for r in results if r['status'] == 'success')}\n")
        f.write(f"失败：{sum(1 for r in results if r['status'] == 'failed')}\n\n")
        f.write("## 详细结果\n\n")
        for i, result in enumerate(results, 1):
            f.write(f"### {i}. {result['url']}\n\n")
            f.write(f"- 状态：{result['status']}\n")
            if result["status"] == "success":
                f.write(f"- 报告：{result['report']}\n")
            else:
                f.write(f"- 错误：{result['error']}\n")
            f.write("\n")

    print(f"\n✅ 批量处理完成！汇总报告：{summary_path}")
    logger.info("批量处理完成，汇总报告：%s", summary_path)
    return 0


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _get_output_dir(config: dict) -> Path:
    from video_to_action.config import get_output_dir as _get

    return _get(config)


def _init_progress_bar(total: int, log_level: int) -> Optional[object]:
    if TQDM_AVAILABLE and log_level != logging.DEBUG:
        return tqdm(total=total, desc="处理进度", unit="步", ncols=80)
    return None


def _finish_progress_bar(pbar: Optional[object]) -> None:
    if pbar is not None:
        pbar.update(1)
        pbar.close()


def _close_progress_bar(pbar: Optional[object]) -> None:
    if pbar is not None:
        pbar.close()


def _warmup_models(config: dict, output_dir: Path, log_level: int) -> None:
    """预热 LLM 和转写模型（减少首次处理延迟）。"""
    print("🔥 正在预热模型...")
    logger.info("开始预热模型")

    warmup_state_file = output_dir / ".warmup_state.json"
    skip_warmup = False
    if warmup_state_file.exists():
        try:
            with open(warmup_state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            if state.get("warmup_done") and (time.time() - state.get("timestamp", 0)) < 3600:
                skip_warmup = True
                print(f"✅ 模型已预热（{(time.time() - state['timestamp']) / 60:.1f} 分钟前），跳过预热")
                logger.info("模型已预热，跳过预热")
        except Exception:
            pass

    if not skip_warmup:
        try:
            analyzer = AnalyzerV2(config)
            test_messages = [{"role": "user", "content": "Hello"}]
            import asyncio

            if asyncio.iscoroutinefunction(analyzer._call_openai_compatible_async):
                asyncio.run(analyzer._call_openai_compatible_async(test_messages))
            else:
                analyzer._call_openai_compatible(test_messages)
            print("✅ LLM 模型预热完成")
            logger.info("LLM 模型预热完成")

            warmup_state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(warmup_state_file, "w", encoding="utf-8") as f:
                json.dump({"warmup_done": True, "timestamp": time.time()}, f, indent=2)
            print("✅ 预热状态已保存")
            logger.info("预热状态已保存")
        except Exception as e:
            logger.warning("⚠️ LLM 模型预热失败：%s", e)


def _analyze_content(config: dict, extracted: dict, download_result: dict, pbar: Optional[object]) -> dict:
    """步骤 3：分析视频内容。"""
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
    if pbar is not None:
        pbar.update(1)
    return plan


def _save_to_knowledge_base(kb, args, download_result: dict, extracted: dict, plan: dict) -> None:
    """保存分析结果到知识库（可选）。"""
    if kb is not None and hasattr(args, "save_to_kb") and args.save_to_kb:
        print("正在保存到知识库...")
        try:
            video_id = kb.add_video_analysis(
                url=args.url,
                platform=download_result["platform"],
                title=None,
                theme=plan.get("theme", ""),
                summary=plan.get("summary", ""),
                transcription_text=extracted.get("text", ""),
                analysis_result=plan,
            )
            print(f"已保存到知识库，视频ID：{video_id}")
            logger.info("已保存到知识库，视频ID：%s", video_id)
        except Exception as e:
            logger.warning("⚠️ 保存到知识库失败：%s", e)


def _execute_plan(config: dict, output_dir: Path, plan: dict, args, pbar: Optional[object]) -> list:
    """步骤 4：执行行动计划。"""
    print("[4/5] 正在执行安装/配置...")
    logger.info("开始执行行动计划")
    executor = Executor(config, output_dir)
    confirm_all = args.level == "confirm"
    execution_results = executor.execute_plan(plan, confirm_all=confirm_all)
    if pbar is not None:
        pbar.update(1)
    return execution_results


def _auto_resolve(execution_results: list, config: dict, output_dir: Path, plan: dict, args) -> None:
    """自动修复失败的执行步骤。"""
    resolver = Resolver(config, output_dir)
    confirm_all = args.level == "confirm"
    for result in execution_results:
        if not result["success"]:
            try:
                fix = resolver.resolve(result["command"], result["stderr"])
                if fix["resolved"]:
                    if fix.get("executable") and fix.get("new_command"):
                        print(f"尝试修复：{fix['message']}")
                        logger.info("尝试修复命令：%s", fix["message"])
                        fixed_result = Executor(config, output_dir).execute(fix["new_command"], confirm=confirm_all)
                        result["fixed_result"] = fixed_result
                    else:
                        print(f"修复建议（未自动执行）：{fix['message']}")
                        logger.info("修复建议：%s", fix["message"])
            except Exception as e:
                logger.warning("⚠️ 自动修复失败：%s", e)


def _generate_report(
    config: dict, output_dir: Path, args, download_result: dict, plan: dict, execution_results: list
) -> Path:
    """步骤 5：生成中文操作笔记。"""
    print("[5/5] 正在生成中文操作笔记...")
    logger.info("开始生成报告")
    reporter = Reporter(config, output_dir)
    context = {
        "video_url": args.url,
        "platform": download_result["platform"],
        "download_method": download_result["method"],
        "video_path": str(download_result["output_path"]),
        "plan": plan,
        "execution_results": execution_results,
    }
    return reporter.generate(context)


def _handle_known_error(e: Exception, pbar: Optional[object]) -> None:
    """处理已知的业务异常，输出日志。"""
    from video_to_action.exceptions import (
        AnalysisError,
        ConfigurationError,
        DownloadError,
        ExecutionError,
        ExtractionError,
    )

    _close_progress_bar(pbar)

    if isinstance(e, DownloadError):
        logger.error("❌ 视频下载失败：%s", e)
        logger.error("建议：请检查视频链接是否有效，或尝试使用代理")
    elif isinstance(e, ExtractionError):
        logger.error("❌ 内容提取失败：%s", e)
        logger.error("建议：请检查视频文件是否完整，或尝试重新下载")
    elif isinstance(e, AnalysisError):
        logger.error("❌ 内容分析失败：%s", e)
        logger.error("建议：1) 检查 LLM API 配置 2) 缩短视频长度 3) 联系 API 提供商")
    elif isinstance(e, ExecutionError):
        logger.error("❌ 命令执行失败：%s", e)
        logger.error("建议：请查看错误详情，或尝试手动执行命令")
    elif isinstance(e, ConfigurationError):
        logger.error("❌ 配置错误：%s", e)
        logger.error("建议：请运行 `video-to-action setup` 重新配置")


def _handle_http_error(e: httpx.HTTPStatusError, pbar: Optional[object]) -> None:
    """处理 HTTP 错误（如 LLM API 500）。"""
    _close_progress_bar(pbar)
    if e.response.status_code == 500:
        logger.error("❌ LLM API 返回 500 错误，可能是文本过长")
        logger.error("建议：1) 缩短视频长度 2) 升级 LLM 模型 3) 联系 API 提供商")
    else:
        logger.error("❌ HTTP 错误：%s", e)
