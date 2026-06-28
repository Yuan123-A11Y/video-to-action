#!/usr/bin/env python3
"""
Video-to-Action 生产环境部署脚本。

功能：
1. 检查系统依赖（Python、ffmpeg）
2. 创建虚拟环境
3. 安装 Python 依赖
4. 安装 Playwright 浏览器
5. 初始化数据库
6. 运行测试
7. 启动服务（可选）

使用方法：
    python scripts/deploy.py [--prod|--dev] [--skip-tests]
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path


def check_python_version() -> bool:
    """检查 Python 版本。"""
    print("🐍 检查 Python 版本...")
    version = sys.version_info
    if version < (3, 12):
        print(f"❌ Python 版本过低：{version.major}.{version.minor}")
        print("   需要 Python >= 3.12")
        return False
    print(f"✅ Python 版本：{version.major}.{version.minor}.{version.micro}")
    return True


def check_ffmpeg() -> bool:
    """检查 ffmpeg 是否安装。"""
    print("🎬 检查 ffmpeg...")
    if shutil.which("ffmpeg") is None:
        print("❌ 未找到 ffmpeg")
        print("   请安装 ffmpeg：")
        print("   - Ubuntu/Debian: sudo apt-get install -y ffmpeg")
        print("   - macOS: brew install ffmpeg")
        print("   - Windows: https://ffmpeg.org/download.html")
        return False
    print("✅ ffmpeg 已安装")
    return True


def create_virtual_env(prod: bool = False) -> Path:
    """创建虚拟环境。"""
    print("📦 创建虚拟环境...")
    venv_path = Path("venv")
    
    if venv_path.exists():
        print(f"⚠️  虚拟环境已存在：{venv_path}")
        return venv_path
    
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
        )
        print(f"✅ 虚拟环境已创建：{venv_path}")
        return venv_path
    except subprocess.CalledProcessError as e:
        print(f"❌ 创建虚拟环境失败：{e}")
        raise


def get_venv_python(venv_path: Path) -> Path:
    """获取虚拟环境中的 Python 路径。"""
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def get_venv_pip(venv_path: Path) -> Path:
    """获取虚拟环境中的 pip 路径。"""
    if sys.platform == "win32":
        return venv_path / "Scripts" / "pip.exe"
    else:
        return venv_path / "bin" / "pip"


def install_dependencies(venv_path: Path, prod: bool = False) -> bool:
    """安装 Python 依赖。"""
    print("📥 安装 Python 依赖...")
    pip_path = get_venv_pip(venv_path)
    
    try:
        # 升级 pip
        subprocess.run(
            [str(pip_path), "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
        )
        
        # 安装依赖
        cmd = [str(pip_path), "install", "-r", "requirements.txt"]
        if prod:
            cmd.append("--no-dev")
        
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
        )
        print("✅ Python 依赖已安装")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装依赖失败：{e}")
        return False


def install_playwright(venv_path: Path) -> bool:
    """安装 Playwright 浏览器。"""
    print("🌐 安装 Playwright 浏览器...")
    python_path = get_venv_python(venv_path)
    
    try:
        subprocess.run(
            [str(python_path), "-m", "playwright", "install"],
            check=True,
            capture_output=True,
        )
        print("✅ Playwright 浏览器已安装")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装 Playwright 失败：{e}")
        return False


def init_database() -> bool:
    """初始化数据库。"""
    print("🗄️  初始化数据库...")
    python_path = get_venv_python(venv_path) if "venv_path" in locals() else Path(sys.executable)
    
    try:
        # 运行数据库迁移脚本
        result = subprocess.run(
            [str(python_path), "database/migrate.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✅ 数据库已初始化")
            return True
        else:
            print(f"⚠️  数据库初始化失败：{result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 数据库初始化异常：{e}")
        return False


def run_tests(skip_tests: bool = False) -> bool:
    """运行单元测试。"""
    if skip_tests:
        print("⚠️  跳过测试（--skip-tests）")
        return True
    
    print("🧪 运行单元测试...")
    python_path = get_venv_python(venv_path) if "venv_path" in locals() else Path(sys.executable)
    
    try:
        result = subprocess.run(
            [str(python_path), "-m", "pytest", "video_to_action/tests/", "-v"],
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode == 0:
            print("✅ 所有测试通过")
            return True
        else:
            print(f"❌ 测试失败：{result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 运行测试异常：{e}")
        return False


def create_directories():
    """创建必要的目录。"""
    print("📁 创建目录...")
    dirs = ["outputs", "data", "logs", "cache"]
    for dir_name in dirs:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        print(f"   ✅ {dir_path}")


def print_success_message(prod: bool = False):
    """打印部署成功消息。"""
    print("\n" + "=" * 60)
    print("🎉 部署完成！")
    print("=" * 60)
    print("\n📝 后续步骤：")
    print("\n1. 激活虚拟环境：")
    if sys.platform == "win32":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    
    print("\n2. 配置 LLM（交互式）：")
    print("   python -m video_to_action.cli setup")
    
    print("\n3. 处理单个视频：")
    print('   python -m video_to_action.cli process "https://www.bilibili.com/video/BV1xx411c7mD"')
    
    print("\n4. 批量处理视频：")
    print("   python -m video_to_action.cli batch videos.txt --output outputs")
    
    if not prod:
        print("\n5. 运行测试：")
        print("   python -m pytest video_to_action/tests/ -v")
    
    print("\n📖 详细文档：")
    print("   查看 DEPLOYMENT_GUIDE.md")
    print("=" * 60)


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(description="Video-to-Action 部署脚本")
    parser.add_argument("--prod", action="store_true", help="生产环境部署（跳过开发依赖）")
    parser.add_argument("--skip-tests", action="store_true", help="跳过测试")
    args = parser.parse_args()
    
    print("🚀 Video-to-Action 部署脚本")
    print("=" * 60)
    
    # 1. 检查系统依赖
    if not check_python_version():
        sys.exit(1)
    if not check_ffmpeg():
        sys.exit(1)
    
    # 2. 创建虚拟环境
    venv_path = create_virtual_env(prod=args.prod)
    
    # 3. 安装依赖
    if not install_dependencies(venv_path, prod=args.prod):
        sys.exit(1)
    
    # 4. 安装 Playwright
    if not install_playwright(venv_path):
        sys.exit(1)
    
    # 5. 创建目录
    create_directories()
    
    # 6. 初始化数据库
    if not init_database():
        print("⚠️  数据库初始化失败，请手动检查")
    
    # 7. 运行测试
    if not args.skip_tests:
        if not run_tests(skip_tests=args.skip_tests):
            print("⚠️  测试失败，请检查")
    
    # 8. 打印成功消息
    print_success_message(prod=args.prod)


if __name__ == "__main__":
    main()
