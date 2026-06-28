# g:\trae\video-to-action\video_to_action\cli_kb.py
"""知识库相关子命令：search、export-handbook、kb-stats、clear-cache。"""

import logging
from pathlib import Path

from video_to_action.analyzer_v2 import AnalyzerV2

logger = logging.getLogger(__name__)


def handle_search(args, kb) -> int:
    """处理 search 子命令：搜索知识库。"""
    if kb is None:
        logger.error("❌ 知识库不可用，无法执行搜索")
        return 1

    print(f"搜索：{args.query} (类型：{args.type})")
    try:
        if args.type == "video":
            results = kb.search_videos(args.query, limit=args.limit)
            for r in results:
                print(f"  - [{r['platform']}] {r.get('title') or r['theme']}")
        else:
            results = kb.search_tools(args.query, limit=args.limit)
            for r in results:
                print(f"  - {r['name']}: {r['purpose']}")
    except Exception as e:
        logger.error("❌ 搜索失败：%s", e)
        return 1
    return 0


def handle_export_handbook(args, kb) -> int:
    """处理 export-handbook 子命令：导出操作手册。"""
    if kb is None:
        logger.error("❌ 知识库不可用，无法导出手册")
        return 1

    try:
        output_path = Path(args.output) if args.output else None
        path = kb.export_handbook(output_path)
        print(f"操作手册已导出：{path}")
    except Exception as e:
        logger.error("❌ 导出手册失败：%s", e)
        return 1
    return 0


def handle_kb_stats(args, kb) -> int:
    """处理 kb-stats 子命令：显示知识库统计信息。"""
    if kb is None:
        logger.error("❌ 知识库不可用，无法查看统计")
        return 1

    try:
        stats = kb.get_statistics()
        print(f"视频数量：{stats['video_count']}")
        print(f"工具数量：{stats['tool_count']}")
        print("平台分布：")
        for platform in stats["platform_stats"]:
            print(f"  - {platform['platform']}: {platform['count']} 个")
    except Exception as e:
        logger.error("❌ 获取统计信息失败：%s", e)
        return 1
    return 0


def handle_clear_cache() -> int:
    """处理 clear-cache 子命令：清除分析器缓存。"""
    try:
        cache_file = AnalyzerV2._cache_file
        if cache_file.exists():
            cache_file.unlink()
            print(f"✅ 缓存文件已删除：{cache_file}")
        AnalyzerV2._cache = {}
        print("✅ 内存缓存已清空")
        logger.info("缓存已清除")
    except Exception as e:
        logger.error("❌ 清除缓存失败：%s", e)
        return 1
    return 0
