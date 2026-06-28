@echo off
chcp 65001 >nul
echo ====================
echo Video-to-Action 一键部署脚本（Windows）
echo ====================
echo.

echo 🐍 1. 检查 Python 版本...
python --version | findstr /R "3\..*" >nul
if errorlevel 1 (
    echo ❌ Python 3.x 未找到，请先安装 Python 3.12+
    pause
    exit /b 1
)
python --version
echo ✅ Python 已安装
echo.

echo 📦 2. 创建虚拟环境...
if exist venv (
    echo ⚠️  虚拟环境已存在，跳过创建
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo ✅ 虚拟环境已创建
)
echo.

echo 📥 3. 安装 Python 依赖...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 安装依赖失败
    pause
    exit /b 1
)
echo ✅ Python 依赖已安装
echo.

echo 🌐 4. 安装 Playwright 浏览器...
python -m playwright install
if errorlevel 1 (
    echo ⚠️  Playwright 浏览器安装失败，请手动运行：venv\Scripts\python.exe -m playwright install
) else (
    echo ✅ Playwright 浏览器已安装
)
echo.

echo 🗄️  5. 创建必要目录...
if not exist outputs mkdir outputs
if not exist data mkdir data
if not exist logs mkdir logs
if not exist cache mkdir cache
echo ✅ 目录已创建
echo.

echo 🧪 6. 运行测试（可选）...
set /p RUN_TESTS=是否运行测试？(y/n):
if /i "%RUN_TESTS%"=="y" (
    python -m pytest video_to_action/tests/ -v
    if errorlevel 1 (
        echo ⚠️  测试失败，请检查
    ) else (
        echo ✅ 所有测试通过
    )
) else (
    echo ⚠️  跳过测试
)
echo.

echo 🎉 部署完成！
echo.
echo 📝 后续步骤：
echo   1. 激活虚拟环境：venv\Scripts\activate.bat
echo   2. 配置 LLM：python -m video_to_action.cli setup
echo   3. 处理视频：python -m video_to_action.cli process "视频URL"
echo   4. 查看文档：DEPLOYMENT_GUIDE.md
echo.
echo 📖 详细文档：DEPLOYMENT_GUIDE.md
echo ====================
pause
