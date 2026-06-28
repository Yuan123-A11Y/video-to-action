#!/usr/bin/env python3
"""自动修复 video-to-action 项目的代码风格问题。"""

import subprocess
import sys
from pathlib import Path

def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    """运行命令并返回结果。"""
    print(f"\n{'='*60}")
    print(f"运行: {' '.join(cmd)}")
    print('='*60)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    if result.stdout:
        # 只打印前 50 行，避免输出过多
        lines = result.stdout.strip().split('\n')
        if len(lines) > 50:
            print('\n'.join(lines[:50]))
            print(f"... (共 {len(lines)} 行，仅显示前 50 行)")
        else:
            print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result

def main() -> None:
    """主函数。"""
    python = sys.executable
    project_root = Path(__file__).parent

    print("开始修复代码风格问题...")
    print(f"项目根目录: {project_root}")
    print(f"Python 解释器: {python}")

    # 1. 使用 black 格式化所有文件
    result1 = run([
        python, "-m", "black",
        "--line-length", "120",
        "video_to_action/",
        "tools/douyin-downloader/",
    ])

    # 2. 使用 isort 排序导入
    result2 = run([
        python, "-m", "isort",
        "--profile", "black",
        "video_to_action/",
        "tools/douyin-downloader/",
    ])

    # 3. 删除未使用的导入
    result3 = run([
        python, "-m", "autoflake",
        "--in-place",
        "--remove-all-unused-imports",
        "--recursive",
        "video_to_action/",
        "tools/douyin-downloader/",
    ])

    # 4. 使用 autopep8 修复 PEP 8 问题
    result4 = run([
        python, "-m", "autopep8",
        "--in-place",
        "--recursive",
        "--max-line-length", "120",
        "--ignore", "E203,W503,E501",  # E501 忽略行长度（black 会处理）
        "video_to_action/",
        "tools/douyin-downloader/",
    ])

    print(f"\n{'='*60}")
    print("修复完成！")
    print('='*60)

    # 5. 验证修复结果
    print("\n验证修复结果...")
    run([python, "-m", "black", "--check", "video_to_action/", "tools/douyin-downloader/"])
    run([python, "-m", "isort", "--check-only", "video_to_action/", "tools/douyin-downloader/"])
    run([
        python, "-m", "flake8",
        "video_to_action/",
        "tools/douyin-downloader/",
        "--max-line-length", "120",
        "--extend-ignore", "E203,W503",
        "--exclude", ".venv,__pycache__,*.pyc",
    ])

    print("\n✅ 请运行测试确保没有破坏现有功能：")
    print(f"   {python} -m pytest tests/ -v")

if __name__ == "__main__":
    main()
