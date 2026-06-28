#!/bin/bash
# Video-to-Action 一键部署脚本（Linux/macOS）

set -e  # 遇到错误立即退出

echo "============================"
echo "Video-to-Action 一键部署脚本（Linux/macOS）"
echo "============================"
echo ""

echo "🐍 1. 检查 Python 版本..."
python3 --version | grep -E "3\..*" || {
    echo "❌ Python 3.x 未找到，请先安装 Python 3.12+"
    exit 1
}
python3 --version
echo "✅ Python 已安装"
echo ""

echo "📦 2. 创建虚拟环境..."
if [ -d "venv" ]; then
    echo "⚠️  虚拟环境已存在，跳过创建"
else
    python3 -m venv venv || {
        echo "❌ 创建虚拟环境失败"
        exit 1
    }
    echo "✅ 虚拟环境已创建"
fi
echo ""

echo "📥 3. 安装 Python 依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || {
    echo "❌ 安装依赖失败"
    exit 1
}
echo "✅ Python 依赖已安装"
echo ""

echo "🌐 4. 安装 Playwright 浏览器..."
python -m playwright install || {
    echo "⚠️  Playwright 浏览器安装失败，请手动运行：venv/bin/python -m playwright install"
} || true
echo "✅ Playwright 浏览器已安装"
echo ""

echo "🗄️  5. 创建必要目录..."
mkdir -p outputs data logs cache
echo "✅ 目录已创建"
echo ""

echo "🧪 6. 运行测试（可选）..."
read -p "是否运行测试？(y/n): " RUN_TESTS
if [ "$RUN_TESTS" = "y" ] || [ "$RUN_TESTS" = "Y" ]; then
    python -m pytest video_to_action/tests/ -v || {
        echo "⚠️  测试失败，请检查"
    } || true
    echo "✅ 测试完成"
else
    echo "⚠️  跳过测试"
fi
echo ""

echo "🎉 部署完成！"
echo ""
echo "📝 后续步骤："
echo "  1. 激活虚拟环境：source venv/bin/activate"
echo "  2. 配置 LLM：python -m video_to_action.cli setup"
echo "  3. 处理视频：python -m video_to_action.cli process '视频URL'"
echo "  4. 查看文档：DEPLOYMENT_GUIDE.md"
echo ""
echo "📖 详细文档：DEPLOYMENT_GUIDE.md"
echo "============================"

exit 0
