"""视频内容分析模块，使用 LLM 理解视频并生成行动计划。"""

import json
import re


class Analyzer:
    """视频内容分析器。"""

    def __init__(self, config: dict):
        """初始化分析器，加载 LLM 配置。"""
        self.config = config
        self.llm_config = config.get("llm", {})

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

    def _build_mock_response(self, text: str) -> dict:
        """构建未接入 LLM 时的默认回退响应。"""
        return {
            "theme": "待分析",
            "summary": "当前未配置有效的 LLM 服务，仅返回占位结果。请配置 llm 部分后重新分析。",
            "tools": [],
            "needs_credential": False,
            "is_paid": False,
            "alternative_tools": [],
        }

    def _call_llm(self, prompt: str) -> str:
        """调用配置的 LLM 服务获取响应。

        当前支持 OpenAI 兼容接口，通过 config/settings.yaml 中的 llm 字段配置。
        """
        provider = self.llm_config.get("provider", "mock")
        if provider == "mock":
            raise RuntimeError("LLM provider 设置为 mock")

        if provider != "openai":
            raise RuntimeError(f"不支持的 LLM provider: {provider}")

        api_key = self.llm_config.get("api_key")
        if not api_key:
            raise RuntimeError("未配置 LLM API Key")

        base_url = self.llm_config.get("base_url", "https://api.openai.com/v1")
        model = self.llm_config.get("model", "gpt-4o-mini")
        max_tokens = self.llm_config.get("max_tokens", 2048)
        temperature = self.llm_config.get("temperature", 0.3)

        # 延迟导入 httpx，避免在测试环境中强制依赖
        import httpx

        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个 helpful 的视频内容分析助手。",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=self.llm_config.get("timeout", 120),
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def analyze(self, text: str, platform: str) -> dict:
        """分析视频内容并返回结构化计划。

        优先调用真实 LLM；未配置或调用失败时回退到 mock 结果。
        """
        prompt = self._create_prompt(text, platform)
        try:
            response = self._call_llm(prompt)
            return self._parse_json_response(response)
        except Exception as e:
            # LLM 调用失败时返回回退结果，避免整个流程中断
            fallback = self._build_mock_response(text)
            fallback["_llm_error"] = str(e)
            return fallback

    def analyze_with_llm(self, text: str, platform: str, llm_callable) -> dict:
        """使用外部 LLM 可调用对象分析内容。"""
        prompt = self._create_prompt(text, platform)
        response = llm_callable(prompt)
        return self._parse_json_response(response)
