"""
启动脚本 - 同时启动 FastAPI 后端和 Web 前端。

支持两种模式：
  - 开发模式（默认）：启动 Vite dev server + FastAPI backend
  - 生产模式：使用 uvicorn 静态文件托管 + FastAPI backend
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# 获取项目根目录
ROOT_DIR = Path(__file__).parent
API_DIR = ROOT_DIR / "api"
FRONTEND_DIR = ROOT_DIR / "frontend"
OUTPUTS_DIR = ROOT_DIR / "outputs"

# 检测运行模式
DEV_MODE = os.getenv("V2A_MODE", "dev") == "dev"


def check_dependencies():
    """检查依赖是否已安装。"""
    print("检查 Python 依赖...")
    try:
        import fastapi
        import uvicorn
        import requests
        import httpx
        import yaml
        print("  Python 依赖已安装")
    except ImportError as e:
        print(f"  Python 依赖缺失: {e}")
        print("  请运行: pip install -r requirements.txt")
        return False

    if DEV_MODE:
        # 检查 Node.js 是否可用
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            print(f"  Node.js {result.stdout.strip()}")
            # 检查前端依赖是否已安装
            node_modules = FRONTEND_DIR / "node_modules"
            if not node_modules.exists():
                print("  前端依赖未安装，正在安装...")
                subprocess.run(
                    ["npm", "install"],
                    cwd=str(FRONTEND_DIR),
                    check=True,
                    timeout=300,
                )
                print("  前端依赖已安装")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("  Node.js 未找到或超时")
            print("  请安装 Node.js 或设置 V2A_MODE=prod 使用生产模式")
            return False

    return True


def start_api_server():
    """启动 FastAPI 后端服务器。"""
    print("启动 FastAPI 后端服务器...")

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app",
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    time.sleep(2)

    # 检查进程是否还在运行
    if process.poll() is not None:
        print("  FastAPI 启动失败")
        output = process.stdout.read()
        print(output)
        return None

    print(f"  FastAPI 已启动 (PID: {process.pid})")
    print("  API 地址: http://localhost:8000")

    return process


def start_frontend_dev():
    """启动 Vite 开发服务器。"""
    print("启动 Vite 前端开发服务器...")

    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3000"],
        cwd=str(FRONTEND_DIR / "dist"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    time.sleep(1)

    if process.poll() is not None:
        print("  前端服务器启动失败")
        return None

    print(f"  前端已启动 (PID: {process.pid})")
    print("  前端地址: http://localhost:3000")

    return process


def main():
    """主函数。"""
    print("=" * 60)
    print("Video-to-Action Web UI 启动脚本")
    print(f"模式: {'开发' if DEV_MODE else '生产'}")
    print("=" * 60)

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 创建输出目录
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # 构建前端（如果需要）
    dist_dir = FRONTEND_DIR / "dist"
    if not dist_dir.exists() or not (dist_dir / "index.html").exists():
        print("\n构建前端...")
        result = subprocess.run(
            ["npx", "vite", "build"],
            cwd=str(FRONTEND_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"前端构建失败:\n{result.stderr}")
            sys.exit(1)
        print("  前端构建完成")

    # 启动后端
    print()
    api_process = start_api_server()
    if api_process is None:
        sys.exit(1)

    # 启动前端
    web_process = start_frontend_dev()
    if web_process is None:
        api_process.terminate()
        sys.exit(1)

    print()
    print("=" * 60)
    print(" 所有服务已启动！")
    print("=" * 60)
    print()
    print(" API 后端:   http://localhost:8000")
    print(" Web 前端:   http://localhost:3000")
    print(" API 文档:   http://localhost:8000/docs")
    print()
    print(" 使用说明:")
    print("   1. 在浏览器中打开 http://localhost:3000")
    print("   2. 输入视频 URL 或上传视频文件")
    print("   3. 实时查看处理进度")
    print("   4. 查看分析结果、搜索知识库")
    print()
    print(" 按 Ctrl+C 停止所有服务")
    print("=" * 60 + "\n")

    try:
        api_process.wait()
    except KeyboardInterrupt:
        print("\n\n正在停止服务...")
        api_process.terminate()
        web_process.terminate()
        print(" 所有服务已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
