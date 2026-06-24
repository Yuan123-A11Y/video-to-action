from video_to_action.analyzer import Analyzer


def test_parse_json_response_valid():
    analyzer = Analyzer({})
    data = analyzer._parse_json_response('{"theme": "test"}')
    assert data["theme"] == "test"


def test_parse_json_response_with_markdown():
    analyzer = Analyzer({})
    data = analyzer._parse_json_response('```json\n{"theme": "test"}\n```')
    assert data["theme"] == "test"


def test_create_analysis_prompt():
    analyzer = Analyzer({})
    prompt = analyzer._create_prompt("这是一个测试视频", "抖音")
    assert "测试视频" in prompt
    assert "抖音" in prompt


def test_analyze_with_llm_uses_callable():
    analyzer = Analyzer({})

    def fake_llm(prompt: str) -> str:
        return '{"theme": "测试主题", "summary": "测试摘要", "tools": [], "needs_credential": false, "is_paid": false, "alternative_tools": []}'

    result = analyzer.analyze_with_llm("文本", "B站", fake_llm)
    assert result["theme"] == "测试主题"


def test_analyze_fallback_to_mock_without_llm_config():
    analyzer = Analyzer({})
    result = analyzer.analyze("这是一个测试视频", "抖音")
    assert result["theme"] == "待分析"
    assert "_llm_error" in result
