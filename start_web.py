"""
启动脚本 - 同时启动 FastAPI 后端和 Web 前端。
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# 获取项目根目录
ROOT_DIR = Path(__file__).parent
API_DIR = ROOT_DIR / "api"
WEB_DIR = ROOT_DIR / "web"
OUTPUTS_DIR = ROOT_DIR / "outputs"


def check_dependencies():
    """检查依赖是否已安装。"""
    print("检查 Python 依赖...")
    try:
        import fastapi
        import uvicorn
        import requests
        import httpx
        import yaml
        print("✅ Python 依赖已安装")
        return True
    except ImportError as e:
        print(f"❌ Python 依赖缺失: {e}")
        print("请运行: pip install -r requirements.txt")
        print("以及: pip install fastapi uvicorn")
        return False


def start_api_server():
    """启动 FastAPI 后端服务器。"""
    print("\n启动 FastAPI 后端服务器...")
    api_app = API_DIR / "main.py"
    
    if not api_app.exists():
        print(f"❌ 找不到 API 主文件: {api_app}")
        return None
    
    process = subprocess.Popen(
        [sys.executable, str(api_app)],
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    print(f"✅ FastAPI 服务器已启动 (PID: {process.pid})")
    print("   访问地址: <ADDRESS_REMOVED>")
    
    # 等待服务器启动
    time.sleep(2)
    
    return process


def start_web_server():
    """启动 Web 前端服务器（简单 HTTP 服务器）。"""
    print("\n启动 Web 前端服务器...")
    web_index = WEB_DIR / "index.html"
    
    if not web_index.exists():
        print(f"❌ 找不到 Web 入口文件: {web_index}")
        return None
    
    # 使用 Python 内置 HTTP 服务器
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3000", "--directory", str(WEB_DIR)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    print(f"✅ Web 服务器已启动 (PID: {process.pid})")
    print("   访问地址: <ADDRESS_REMOVED>")
    
    return process


def main():
    """主函数。"""
    print("=" * 60)
    print("Video-to-Action Web UI 启动脚本")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 创建输出目录
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 启动服务器
    api_process = start_api_server()
    if api_process is None:
        sys.exit(1)
    
    web_process = start_web_server()
    if web_process is None:
        api_process.terminate()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ 所有服务已启动！")
    print("=" * 60)
    print("\n📡 API 后端: <ADDRESS_REMOVED>")
    print("🌐 Web 前端: <ADDRESS_REMOVED>")
    print("\n⚡ 使用说明:")
    print("   1. 在浏览器中打开 <ADDRESS_REMOVED>")
    print("   2. 输入视频 URL 并处理")
    print("   3. 查看视频库、工具库和统计数据")
    print("\n⏹  按 Ctrl+C 停止所有服务")
    print("=" * 60 + "\n")
    
    try:
        # 等待用户中断
        api_process.wait()
    except KeyboardInterrupt:
        print("\n\n正在停止服务...")
        api_process.terminate()
        web_process.terminate()
        print("✅ 所有服务已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
