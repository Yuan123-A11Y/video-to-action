"""视频内容分析模块 - 向后兼容层。

实际实现已迁移到 analyzer_v2.py（AnalyzerV2），
本模块保留旧接口别名以确保向后兼容。
"""

from video_to_action.analyzer_v2 import AnalyzerV2


class Analyzer(AnalyzerV2):
    """Analyzer 类 - 向后兼容包装器。

    保留旧接口名称（如 _create_prompt）以确保现有代码和测试兼容。
    """

    def _create_prompt(self, text: str, platform: str) -> str:
        """旧接口别名 -> _create_text_prompt。"""
        return self._create_text_prompt(text, platform)


__all__ = ["Analyzer", "AnalyzerV2"]
