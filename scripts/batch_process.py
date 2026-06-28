"""
批量处理多个视频。

使用方法：
    python scripts/batch_process.py --input videos.txt --level confirm

功能：
  1. 从文本文件读取视频 URL 列表
  2. 按顺序处理每个视频
  3. 显示整体进度
  4. 错误恢复（某个视频失败时不中断整个批次）
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

# 尝试导入 tqdm（进度条支持）
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None

# 导入 video_to_action 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from video_to_action.cli import main as process_video
from video_to_action.utils import setup_logging


def load_video_list(input_file: str) -> list[str]:
    """加载视频列表。

    Args:
        input_file: 输入文件路径（支持 .txt、.csv）

    Returns:
        视频 URL 列表
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_file}")
        sys.exit(1)

    videos = []
    if input_path.suffix == ".txt":
        # 每行一个 URL
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    videos.append(line)
    elif input_path.suffix == ".csv":
        # CSV 格式：第一列是 URL
        with open(input_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    url = row[0].strip()
                    if not url.startswith("#"):
                        videos.append(url)
    else:
        print(f"[ERROR] Unsupported file format: {input_path.suffix}")
        sys.exit(1)

    return videos


def save_results(results: list[dict], output_file: str = None):
    """保存处理结果。

    Args:
        results: 处理结果列表
        output_file: 输出文件路径（JSON 格式）
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"outputs/batch_results_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Results saved to: {output_file}")


def batch_process(video_list: list[str], level: str = "confirm", max_workers: int = 1):
    """批量处理视频。

    Args:
        video_list: 视频 URL 列表
        level: 自动化级别（extract/observe/confirm/auto）
        max_workers: 最大并行数（当前未实现并行）
    """
    total = len(video_list)
    print(f"\n{'=' * 60}")
    print(f"Batch Processing: {total} videos")
    print(f"Level: {level}")
    print(f"Max workers: {max_workers}")
    print(f"{'=' * 60}\n")

    results = []
    failed = []

    # 创建进度条
    if TQDM_AVAILABLE:
        pbar = tqdm(total=total, desc="Processing", unit="video")
    else:
        pbar = None

    for i, url in enumerate(video_list, 1):
        print(f"\n[{i}/{total}] Processing: {url}")

        # 构造命令行参数
        argv = ["process", url, "--level", level]

        # 调用 video_to_action 处理视频
        try:
            # 重定向标准输出和标准错误（避免干扰进度条）
            # 这里简化为直接调用 main 函数
            # 实际应该导入相关模块并调用
            ret = process_video(argv)
            if ret == 0:
                results.append({
                    "url": url,
                    "status": "success",
                    "index": i,
                })
                print(f"[OK] Video {i} processed successfully")
            else:
                results.append({
                    "url": url,
                    "status": "failed",
                    "index": i,
                    "return_code": ret,
                })
                failed.append(url)
                print(f"[ERROR] Video {i} processing failed (return code: {ret})")
        except Exception as e:
            results.append({
                "url": url,
                "status": "error",
                "index": i,
                "error": str(e),
            })
            failed.append(url)
            print(f"[ERROR] Video {i} processing error: {e}")

        # 更新进度条
        if pbar is not None:
            pbar.update(1)
        else:
            print(f"Progress: {i}/{total} ({i/total*100:.1f}%)")

    if pbar is not None:
        pbar.close()

    # 打印总结
    print(f"\n{'=' * 60}")
    print(f"Batch Processing Completed")
    print(f"Total: {total}")
    print(f"Success: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")
    if failed:
        print(f"\nFailed videos:")
        for url in failed:
            print(f"  - {url}")
    print(f"{'=' * 60}\n")

    # 保存结果
    save_results(results)

    return results


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(description="Batch process multiple videos")
    parser.add_argument(
        "--input",
        required=True,
        help="Input file containing video URLs (.txt or .csv)",
    )
    parser.add_argument(
        "--level",
        choices=["extract", "observe", "confirm", "auto"],
        default="confirm",
        help="Automation level",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Maximum number of parallel workers (currently not implemented)",
    )
    parser.add_argument(
        "--output",
        help="Output file for results (JSON format)",
    )

    args = parser.parse_args()

    # 加载视频列表
    videos = load_video_list(args.input)
    if not videos:
        print("[ERROR] No videos found in input file")
        sys.exit(1)

    print(f"[INFO] Loaded {len(videos)} videos from {args.input}")

    # 批量处理
    batch_process(videos, args.level, args.max_workers)

    print("[OK] Batch processing completed!")


if __name__ == "__main__":
    main()
