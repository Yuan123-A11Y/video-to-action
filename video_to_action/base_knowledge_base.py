"""知识库抽象基类 - 定义统一接口。"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BaseKnowledgeBase(ABC):
    """视频知识库抽象基类。

    定义所有知识库实现必须提供的一致接口。
    SQLite 和 MySQL 实现均需继承此类。
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        """初始化知识库。"""

    @abstractmethod
    def add_video_analysis(
        self,
        url: str,
        platform: str,
        title: Optional[str],
        theme: str,
        summary: str,
        transcription_text: str,
        analysis_result: dict,
    ) -> int:
        """添加视频分析结果到知识库。

        Args:
            url: 视频URL
            platform: 平台名称
            title: 视频标题
            theme: 视频主题
            summary: 视频摘要
            transcription_text: 转录文本
            analysis_result: 分析结果字典

        Returns:
            插入的视频ID
        """

    @abstractmethod
    def search_videos(self, query: str, limit: int = 10) -> list[dict]:
        """搜索视频（基于模糊匹配）。"""

    @abstractmethod
    def search_tools(self, query: str, limit: int = 10) -> list[dict]:
        """搜索工具（基于模糊匹配）。"""

    @abstractmethod
    def get_video_by_url(self, url: str) -> Optional[dict]:
        """根据URL获取视频分析结果。"""

    @abstractmethod
    def get_tool_by_name(self, name: str) -> Optional[dict]:
        """根据工具名称获取工具信息。"""

    @abstractmethod
    def get_video_tools(self, video_id: int) -> list[dict]:
        """获取视频关联的工具列表。"""

    @abstractmethod
    def get_statistics(self) -> dict:
        """获取知识库统计信息。"""

    @abstractmethod
    def get_videos(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """获取视频列表（分页）。"""

    @abstractmethod
    def get_video(self, video_id: int) -> Optional[dict]:
        """获取视频详情（包含关联工具）。"""

    @abstractmethod
    def get_tools(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """获取工具列表（分页）。"""

    @abstractmethod
    def get_tool(self, tool_id: int) -> Optional[dict]:
        """获取工具详情（包含使用该工具的视频）。"""

    @abstractmethod
    def get_videos_count(self) -> int:
        """获取视频总数。"""

    @abstractmethod
    def get_tools_count(self) -> int:
        """获取工具总数。"""

    @abstractmethod
    def delete_video(self, video_id: int) -> bool:
        """删除视频（同时删除关联记录）。"""

    @abstractmethod
    def update_video(self, video_id: int, **kwargs) -> bool:
        """更新视频信息。"""

    @abstractmethod
    def delete_tool(self, tool_id: int) -> bool:
        """删除工具（同时删除关联记录）。"""

    @abstractmethod
    def update_tool(self, tool_id: int, **kwargs) -> bool:
        """更新工具信息。"""

    @abstractmethod
    def close(self):
        """关闭数据库连接（兼容接口）。"""

    def get_tools_with_videos(self) -> list[dict]:
        """获取所有工具及其关联视频（用于导出操作手册）。

        返回格式：
            [
                {
                    "tool": {"id": ..., "name": ..., "purpose": ..., ...},
                    "videos": [{"id": ..., "platform": ..., "title": ..., "theme": ...}, ...]
                },
                ...
            ]

        Returns:
            工具列表，每个工具包含其关联视频
        """
        raise NotImplementedError("get_tools_with_videos 需要子类实现")

    # 非抽象方法（可选实现）
    def export_handbook(self, output_path: Optional[Path] = None) -> Path:
        """导出操作手册（Markdown格式）。

        默认实现，子类可选择重写。
        """
        raise NotImplementedError("export_handbook 需要子类实现")
