"""
Analyzer V2 模块单元测试。

测试视频内容分析器的核心功能：
- 提示词构建（区分 install_commands 和 run_commands）
- JSON 响应解析
- 缓存机制
- 多模态分析
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_to_action.analyzer_v2 import AnalyzerV2


class TestAnalyzerV2Prompt:
    """测试 AnalyzerV2 提示词构建（区分安装和启动命令）。"""

    def setup_method(self):
        self.config = {"llm": {"vision_enabled": False}}
        self.analyzer = AnalyzerV2(self.config)

    def test_create_text_prompt_contains_run_commands_field(self):
        """测试提示词包含 run_commands 字段（区分安装和启动）。"""
        prompt = self.analyzer._create_text_prompt("测试文本", "B站")
        assert "install_commands" in prompt
        assert "run_commands" in prompt
        assert "安装/下载命令" in prompt
        assert "启动/使用" in prompt

    def test_create_text_prompt_distinguishes_install_vs_run(self):
        """测试提示词明确区分安装命令和启动命令。"""
        prompt = self.analyzer._create_text_prompt("测试文本", "B站")
        assert "npm install -g" in prompt
        assert "claude --help" in prompt

    def test_create_text_prompt_few_shot_example_has_run_commands(self):
        """测试 few-shot 示例包含 run_commands 字段。"""
        prompt = self.analyzer._create_text_prompt("测试文本", "B站")
        assert '"run_commands": []' in prompt

    def test_create_text_prompt_truncates_long_text(self):
        """测试长文本被截断到 8000 字符。"""
        long_text = "a" * 9000
        prompt = self.analyzer._create_text_prompt(long_text, "B站")
        # 检查文本部分被截断（提示词模板本身也很长）
        assert "文本已截断" in prompt
        # 提取文本部分，检查长度
        text_start = prompt.find("视频转录文本：")
        text_end = prompt.find("\n\n请输出严格的JSON")
        if text_start != -1 and text_end != -1:
            extracted_text = prompt[text_start + 7:text_end]
            assert len(extracted_text) <= 8000 + 20  # 8000 + 截断提示


class TestAnalyzerV2ParseJson:
    """测试 AnalyzerV2 JSON 解析功能。"""

    def setup_method(self):
        self.config = {"llm": {"vision_enabled": False}}
        self.analyzer = AnalyzerV2(self.config)

    def test_parse_valid_json(self):
        """测试解析合法 JSON。"""
        response = json.dumps({
            "theme": "测试",
            "summary": "测试摘要",
            "tools": [],
            "needs_credential": False,
            "is_paid": False,
            "alternative_tools": []
        })
        result = self.analyzer._parse_json_response(response)
        assert result["theme"] == "测试"
        assert result["summary"] == "测试摘要"

    def test_parse_json_with_code_block(self):
        """测试解析包含在 ```json ``` 中的 JSON。"""
        response = """```json
        {"theme": "测试", "summary": "摘要", "tools": [], "needs_credential": false, "is_paid": false, "alternative_tools": []}
        ```"""
        result = self.analyzer._parse_json_response(response)
        assert result["theme"] == "测试"

    def test_parse_json_with_trailing_comma(self):
        """测试解析包含 trailing comma 的 JSON（自动修复）。"""
        response = '{"theme": "测试", "tools": [{"name": "test"},],}'
        result = self.analyzer._parse_json_response(response)
        assert result["theme"] == "测试"

    def test_parse_empty_response(self):
        """测试解析空响应抛出异常。"""
        with pytest.raises(ValueError, match="空响应"):
            self.analyzer._parse_json_response("")

    def test_parse_invalid_json(self):
        """测试解析非法 JSON 抛出异常。"""
        with pytest.raises(ValueError, match="无法解析"):
            self.analyzer._parse_json_response("这不是 JSON")


class TestAnalyzerV2Cache:
    """测试 AnalyzerV2 缓存机制。"""

    def setup_method(self):
        self.config = {"llm": {"vision_enabled": False}}
        self.analyzer = AnalyzerV2(self.config)
        # 清空缓存
        AnalyzerV2._cache = {}
        AnalyzerV2._cache_enabled = False

    def test_cache_key_generation(self):
        """测试缓存键生成（基于文本哈希）。"""
        key1 = self.analyzer._get_cache_key("测试文本", "B站")
        key2 = self.analyzer._get_cache_key("测试文本", "B站")
        key3 = self.analyzer._get_cache_key("不同文本", "B站")
        assert key1 == key2  # 相同文本生成相同键
        assert key1 != key3  # 不同文本生成不同键

    def test_cache_disabled_by_default(self):
        """测试缓存默认禁用。"""
        assert AnalyzerV2._cache_enabled is False

    def test_cache_validation_expired(self):
        """测试过期缓存被视为无效。"""
        entry = {"_cached_at": time.time() - 8 * 24 * 3600}  # 8 天前
        assert self.analyzer._is_cache_valid(entry) is False

    def test_cache_validation_valid(self):
        """测试有效缓存被视为有效。"""
        entry = {"_cached_at": time.time() - 1 * 24 * 3600}  # 1 天前
        assert self.analyzer._is_cache_valid(entry) is True


class TestAnalyzerV2CallLLM:
    """测试 AnalyzerV2 LLM 调用功能。"""

    def setup_method(self):
        self.config = {
            "llm": {
                "provider": "openai",
                "vision_enabled": False,
                "api_url": "https://api.agnesai.top/v1/chat/completions",
                "model": "agnes-image-2.1-flash",
                "timeout": 30,
            }
        }
        self.analyzer = AnalyzerV2(self.config)

    @patch.object(AnalyzerV2, "_call_openai_compatible")
    def test_call_llm_success(self, mock_call_openai):
        """测试 LLM 调用成功。"""
        # _call_llm 返回 JSON 字符串（不是 dict）
        mock_call_openai.return_value = '{"theme": "测试", "summary": "摘要", "tools": [], "needs_credential": false, "is_paid": false, "alternative_tools": []}'

        messages = [{"role": "user", "content": "测试"}]
        result = self.analyzer._call_llm(messages)
        # _call_llm 返回字符串
        assert isinstance(result, str)
        assert "theme" in result

    @patch.object(AnalyzerV2, "_call_openai_compatible")
    def test_call_llm_http_error(self, mock_call_openai):
        """测试 LLM 调用 HTTP 错误。"""
        mock_call_openai.side_effect = RuntimeError("LLM 调用失败：HTTP 500")

        messages = [{"role": "user", "content": "测试"}]
        with pytest.raises(RuntimeError, match="LLM 调用失败"):
            self.analyzer._call_llm(messages)

    @patch.object(AnalyzerV2, "_call_openai_compatible")
    def test_call_llm_timeout(self, mock_call_openai):
        """测试 LLM 调用超时。"""
        mock_call_openai.side_effect = RuntimeError("LLM 调用失败：超时")

        messages = [{"role": "user", "content": "测试"}]
        with pytest.raises(RuntimeError, match="LLM 调用失败"):
            self.analyzer._call_llm(messages)


class TestAnalyzerV2Analyze:
    """测试 AnalyzerV2 分析功能（集成测试）。"""

    def setup_method(self):
        self.config = {
            "llm": {
                "provider": "openai",
                "vision_enabled": False,
            }
        }

    @patch.object(AnalyzerV2, "_call_llm")
    def test_analyze_success(self, mock_call_llm):
        """测试分析成功。"""
        # _call_llm 应该返回 JSON 字符串
        mock_call_llm.return_value = json.dumps({
            "theme": "Python环境配置",
            "summary": "介绍pyenv安装",
            "tools": [
                {
                    "name": "pyenv",
                    "purpose": "Python版本管理",
                    "links": [],
                    "install_commands": ["curl https://pyenv.run | bash"],
                    "config_steps": [],
                    "run_commands": [],
                    "warnings": [],
                }
            ],
            "needs_credential": False,
            "is_paid": False,
            "alternative_tools": [],
        })

        analyzer = AnalyzerV2(self.config)
        result = analyzer.analyze("介绍pyenv安装Python版本", "B站")

        assert result["theme"] == "Python环境配置"
        assert len(result["tools"]) == 1
        assert result["tools"][0]["name"] == "pyenv"
        assert result["tools"][0]["install_commands"] == ["curl https://pyenv.run | bash"]
        assert result["tools"][0]["run_commands"] == []

    @patch.object(AnalyzerV2, "_call_llm")
    def test_analyze_with_run_commands(self, mock_call_llm):
        """测试分析结果包含 run_commands（区分安装和启动）。"""
        mock_call_llm.return_value = json.dumps({
            "theme": "Claude Code使用",
            "summary": "介绍Claude Code安装和使用",
            "tools": [
                {
                    "name": "claude",
                    "purpose": "AI编程助手",
                    "links": [],
                    "install_commands": ["npm install -g @anthropic-ai/claude-code"],
                    "config_steps": [],
                    "run_commands": ["claude"],
                    "warnings": [],
                }
            ],
            "needs_credential": True,
            "is_paid": True,
            "alternative_tools": ["cursor", "codex"],
        })

        analyzer = AnalyzerV2(self.config)
        result = analyzer.analyze("介绍Claude Code", "B站")

        assert result["tools"][0]["install_commands"] == ["npm install -g @anthropic-ai/claude-code"]
        assert result["tools"][0]["run_commands"] == ["claude"]
        assert result["needs_credential"] is True


class TestAnalyzerV2Multimodal:
    """测试 AnalyzerV2 多模态分析功能。"""

    def setup_method(self):
        self.config = {"llm": {"vision_enabled": True}}
        self.analyzer = AnalyzerV2(self.config)

    def test_create_multimodal_prompt_structure(self):
        """测试多模态提示词结构（文本+图片）。"""
        text = "测试文本"
        frames = ["test1.jpg", "test2.jpg"]

        # Mock 图片编码
        with patch.object(self.analyzer, "_encode_image", return_value="base64mock"):
            content = self.analyzer._create_multimodal_prompt(text, "B站", frames)

        # content 是列表，包含文本部分和图片部分
        assert isinstance(content, list)
        assert len(content) >= 3  # 文本 + 2 张图片
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image_url"
        assert content[2]["type"] == "image_url"

    def test_create_multimodal_prompt_limits_frames(self):
        """测试多模态提示词限制图片数量（最多3张）。"""
        text = "测试文本"
        frames = [f"test{i}.jpg" for i in range(10)]  # 10 张图片

        with patch.object(self.analyzer, "_encode_image", return_value="base64mock"):
            content = self.analyzer._create_multimodal_prompt(text, "B站", frames)

        # 计算图片数量（content 中 type=image_url 的数量）
        image_count = sum(
            1 for item in content
            if item.get("type") == "image_url"
        )
        assert image_count <= 3
