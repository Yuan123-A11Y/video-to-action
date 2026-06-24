import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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
