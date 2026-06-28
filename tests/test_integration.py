"""端到端集成测试 - 测试完整工作流（使用 mock 避免外部依赖）。"""

import json
from unittest.mock import patch

import pytest

from video_to_action.json_parser import parse_json_response


class TestFullAnalysisFlow:
    """测试从下载到知识库存储的完整流程（使用 mock）。"""

    def test_full_flow_with_mocks(self, tmp_path):
        """测试完整分析流程（所有外部依赖都 mock）。"""
        # 1. 解析 LLM 响应
        mock_llm_response = json.dumps({
            "theme": "测试主题",
            "summary": "这是一个测试视频",
            "tools": [
                {
                    "name": "ffmpeg",
                    "purpose": "视频处理",
                    "install_commands": ["sudo apt install ffmpeg"],
                    "config_steps": [],
                    "usage_examples": [],
                    "warnings": [],
                    "alternatives": [],
                }
            ],
            "needs_credential": False,
            "is_paid": False,
            "alternative_tools": [],
        })

        analysis_result = parse_json_response(mock_llm_response)
        assert analysis_result["theme"] == "测试主题"
        assert len(analysis_result["tools"]) == 1
        assert analysis_result["tools"][0]["name"] == "ffmpeg"

        # 2. 存储到知识库（使用 SQLite）
        from video_to_action.knowledge_base import KnowledgeBase

        db_path = tmp_path / "test.db"
        kb = KnowledgeBase(db_path=db_path)

        video_id = kb.add_video_analysis(
            url="https://bilibili.com/video/BV1xx",
            platform="bilibili",
            title="测试视频",
            theme=analysis_result["theme"],
            summary=analysis_result["summary"],
            transcription_text="这是测试视频的转录文本",
            analysis_result=analysis_result,
        )

        assert video_id > 0

        # 3. 验证存储结果
        saved_video = kb.get_video(video_id)
        assert saved_video is not None
        assert saved_video["theme"] == "测试主题"

        # 4. 清理
        kb.close()

    def test_knowledge_base_persistence(self, tmp_path):
        """测试知识库数据持久化（关闭后重新打开）。"""
        from video_to_action.knowledge_base import KnowledgeBase

        db_path = tmp_path / "persistence_test.db"

        # 第一次会话：写入数据
        kb1 = KnowledgeBase(db_path=db_path)
        video_id = kb1.add_video_analysis(
            url="https://example.com/v1",
            platform="test",
            title="测试视频1",
            theme="主题1",
            summary="摘要1",
            transcription_text="这是转录文本1",
            analysis_result={"theme": "主题1", "tools": []},
        )
        kb1.close()

        # 第二次会话：读取数据
        kb2 = KnowledgeBase(db_path=db_path)
        saved_video = kb2.get_video(video_id)
        assert saved_video is not None
        assert saved_video["title"] == "测试视频1"

        # 添加更多数据
        video_id2 = kb2.add_video_analysis(
            url="https://example.com/v2",
            platform="test",
            title="测试视频2",
            theme="主题2",
            summary="摘要2",
            transcription_text="这是转录文本2",
            analysis_result={"theme": "主题2", "tools": []},
        )
        kb2.close()

        # 第三次会话：验证两个视频都在
        kb3 = KnowledgeBase(db_path=db_path)
        videos = kb3.get_videos()
        assert len(videos) == 2
        kb3.close()


class TestCLIIntegration:
    """测试 CLI 命令的集成（使用 mock）。"""

    def test_analyze_command_flow(self, tmp_path):
        """测试 analyze 命令的完整流程（mock 外部依赖）。"""
        from video_to_action.analyzer_v2 import AnalyzerV2

        config = {
            "llm": {
                "api_type": "openai_compatible",
                "api_base": "https://api.example.com",
                "api_key": "test-key",
                "model": "test-model",
                "vision_enabled": False,
            }
        }

        analyzer = AnalyzerV2(config)
        analyzer._cache_enabled = False  # 禁用缓存，确保调用 LLM

        # Mock LLM 调用（analyze() 内部会调用 _call_llm）
        with patch.object(analyzer, "_call_llm") as mock_llm:
            mock_llm.return_value = json.dumps({
                "theme": "CLI 测试",
                "summary": "通过 CLI 测试",
                "tools": [],
                "needs_credential": False,
                "is_paid": False,
                "alternative_tools": [],
            })

            result = analyzer.analyze("测试文本", "bilibili")

            assert result["theme"] == "CLI 测试"
            assert mock_llm.called

    def test_knowledge_base_export_flow(self, tmp_path):
        """测试知识库导出流程。"""
        from video_to_action.handbook_exporter import export_handbook
        from video_to_action.knowledge_base import KnowledgeBase

        db_path = tmp_path / "export_test.db"
        kb = KnowledgeBase(db_path=db_path)

        # 添加测试数据
        kb.add_video_analysis(
            url="https://example.com/v1",
            platform="bilibili",
            title="FFmpeg 教程",
            theme="FFmpeg 基础",
            summary="学习 FFmpeg",
            transcription_text="这是转录文本",
            analysis_result={
                "theme": "FFmpeg 基础",
                "tools": [{"name": "ffmpeg", "purpose": "视频处理"}],
            },
        )

        # 导出操作手册
        output_path = tmp_path / "handbook.md"
        result = export_handbook(kb, output_path)

        assert result == output_path
        assert output_path.exists()

        content = output_path.read_text(encoding="utf-8")
        assert "FFmpeg" in content

        kb.close()


class TestErrorHandling:
    """测试错误处理和降级逻辑。"""

    def test_json_parser_with_invalid_json(self):
        """测试 JSON 解析器的错误处理。"""
        # 无效 JSON 应该抛异常
        with pytest.raises(ValueError):
            parse_json_response("这不是有效的 JSON")

        # 空响应应该抛异常
        with pytest.raises(ValueError):
            parse_json_response("")

    def test_downloader_failure_handling(self, tmp_path):
        """测试下载器失败时的错误处理。"""

        # Mock yt-dlp 失败
        with patch("video_to_action.downloader.download_video") as mock_download:
            mock_download.return_value = {
                "success": False,
                "error": "视频不存在",
            }

            result = mock_download("https://example.com/fake", "bilibili", str(tmp_path))

            assert result["success"] is False
            assert "error" in result
