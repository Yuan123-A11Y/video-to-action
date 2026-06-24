"""视频内容分析模块，使用 LLM 理解视频并生成行动计划。"""

import json
import re


class Analyzer:
    """视频内容分析器。"""

    def __init__(self, config: dict):
        """初始化分析器。"""
        self.config = config

    def _create_prompt(self, text: str, platform: str) -> str:
        """构建发送给 LLM 的分析提示。"""
        return f"""你是一位视频内容分析专家。请分析以下从{platform}视频提取的内容，识别视频中介绍的工具、软件或方法，并输出结构化的行动计划。

视频转录文本：
{text}

请输出 JSON 格式，包含以下字段：
- theme: 视频主题（中文）
- summary: 视频内容摘要（中文，200字以内）
- tools: 工具列表，每个工具包含：
  - name: 工具名称
  - purpose: 工具用途（中文）
  - links: 相关链接列表（GitHub、官网等）
  - install_commands: 安装命令列表
  - config_steps: 配置步骤列表
  - warnings: 注意事项列表
- needs_credential: 是否需要密码/密钥/Token（true/false）
- is_paid: 是否需要付费（true/false）
- alternative_tools: 如果主工具失效，可替代的开源免费工具列表

只输出 JSON，不要输出其他解释文字。"""

    def _parse_json_response(self, response: str) -> dict:
        """从 LLM 响应中解析 JSON。"""
        # 尝试提取 markdown 代码块中的 json
        match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            response = match.group(1)
        return json.loads(response.strip())

    def analyze(self, text: str, platform: str) -> dict:
        """分析视频内容并返回结构化计划。"""
        # 在实际实现中，这里调用 LLM API
        # 当前版本先返回一个模拟结果，供后续替换为真实 LLM 调用
        # TODO: 替换为真实 LLM 调用
        mock_response = {
            "theme": "待分析",
            "summary": "待 LLM 分析",
            "tools": [],
            "needs_credential": False,
            "is_paid": False,
            "alternative_tools": [],
        }
        return mock_response

    def analyze_with_llm(self, text: str, platform: str, llm_callable) -> dict:
        """使用外部 LLM 可调用对象分析内容。"""
        prompt = self._create_prompt(text, platform)
        response = llm_callable(prompt)
        return self._parse_json_response(response)
