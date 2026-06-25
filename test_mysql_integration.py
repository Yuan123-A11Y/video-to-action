"""
测试脚本 - 验证 MySQL 集成和 API 功能。
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

print("=" * 60)
print("Video-to-Action MySQL 集成测试")
print("=" * 60)

# 测试 1: 导入模块
print("\n测试 1: 导入模块...")
try:
    from video_to_action.mysql_knowledge_base import MySQLKnowledgeBase
    print("✅ 模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

# 测试 2: MySQL 连接
print("\n测试 2: MySQL 连接...")
try:
    kb = MySQLKnowledgeBase()
    if kb.use_mysql:
        print("✅ MySQL 连接成功")
    else:
        print("⚠️ 使用 SQLite (MySQL 未启用)")
except Exception as e:
    print(f"❌ MySQL 连接失败: {e}")
    sys.exit(1)

# 测试 3: 数据库操作
print("\n测试 3: 数据库操作...")

# 3.1 获取统计信息
try:
    stats = kb.get_statistics()
    print(f"✅ 统计信息获取成功:")
    print(f"   - 视频总数: {stats.get('video_count', 0)}")
    print(f"   - 工具总数: {stats.get('tool_count', 0)}")
    print(f"   - 平台统计: {len(stats.get('platform_stats', []))} 个平台")
except Exception as e:
    print(f"❌ 统计信息获取失败: {e}")

# 3.2 获取视频列表
try:
    videos = kb.get_videos(limit=5)
    print(f"✅ 视频列表获取成功: {len(videos)} 条记录")
except Exception as e:
    print(f"❌ 视频列表获取失败: {e}")

# 3.3 获取工具列表
try:
    tools = kb.get_tools(limit=5)
    print(f"✅ 工具列表获取成功: {len(tools)} 条记录")
except Exception as e:
    print(f"❌ 工具列表获取失败: {e}")

# 测试 4: 搜索功能
print("\n测试 4: 搜索功能...")
try:
    results = kb.search_videos("test", limit=5)
    print(f"✅ 视频搜索成功: {len(results)} 条结果")
except Exception as e:
    print(f"❌ 视频搜索失败: {e}")

try:
    results = kb.search_tools("test", limit=5)
    print(f"✅ 工具搜索成功: {len(results)} 条结果")
except Exception as e:
    print(f"❌ 工具搜索失败: {e}")

print("\n" + "=" * 60)
print("✅ 所有测试完成！")
print("=" * 60)
