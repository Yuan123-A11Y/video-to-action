#!/usr/bin/env python3
"""测试 GreenVideo 方案下载 B站视频"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from video_to_action.config import load_config
from video_to_action.greenvideo_downloader import GreenVideoDownloader


def test_greenvideo_bilibili():
    """测试 GreenVideo 下载 B站视频"""
    # 加载配置
    config = load_config()

    # B站视频链接（清理分享参数）
    bilibili_url = "https://www.bilibili.com/video/BV1xuVC6AEbg/"

    # 输出目录
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"开始测试 GreenVideo 方案下载 B站视频...")
    print(f"视频链接: {bilibili_url}")
    print(f"输出目录: {output_dir.absolute()}")
    print("-" * 60)

    # 创建 GreenVideo 下载器
    downloader = GreenVideoDownloader(config, output_dir)

    # 执行下载
    result = downloader.download(bilibili_url)

    # 输出结果
    print("\n" + "=" * 60)
    print("下载结果:")
    print("=" * 60)
    print(f"成功: {result['success']}")
    print(f"平台: {result['platform']}")
    print(f"方法: {result['method']}")

    if result['success']:
        print(f"输出路径: {result['output_path']}")
        print(f"详细信息: {result['stdout']}")
    else:
        print(f"错误信息: {result['stderr']}")

    return result


if __name__ == "__main__":
    test_greenvideo_bilibili()
