@echo off
echo ========================================
echo Video-to-Action 代码审查工具配置
echo ========================================
echo.

echo [1/4] 安装 Python 依赖...
pip install black isort flake8 mypy pytest pytest-cov pre-commit bandit detect-secrets -i https://mirrors.huaweicloud.com/repository/pypi/simple/

echo.
echo [2/4] 初始化 pre-commit hooks...
pre-commit install

echo.
echo [3/4] 运行代码格式化（Black + isort）...
black video_to_action/ tests/ --line-length=120
isort video_to_action/ tests/ --profile=black --line-length=120

echo.
echo [4/4] 运行代码质量检查...
echo.
echo --- Flake8 检查 ---
flake8 video_to_action/ tests/ --max-line-length=120 --extend-ignore=E203,W503

echo.
echo --- MyPy 类型检查 ---
mypy video_to_action/ --ignore-missing-imports

echo.
echo --- 运行测试 ---
pytest tests/ -v --cov=video_to_action --cov-report=term-missing

echo.
echo ========================================
echo 配置完成！
echo.
echo 后续使用：
echo   - 每次提交自动检查：git commit 时会自动运行
echo   - 手动运行所有检查：pre-commit run --all-files
echo   - 仅格式化代码：black video_to_action/ tests/
echo ========================================
pause
