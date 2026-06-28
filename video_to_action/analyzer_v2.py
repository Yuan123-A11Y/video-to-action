"""视频内容分析模块 V2 - 优化版，支持多模态分析和本地LLM。"""

import asyncio
import base64
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional


from video_to_action.exceptions import AnalysisError
from video_to_action.json_parser import parse_json_response

logger = logging.getLogger(__name__)


class AnalyzerV2:
    """视频内容分析器 V2 - 支持多模态分析和本地LLM。"""

    # 类级别缓存（所有实例共享）
    _cache = {}
    _cache_file = Path("outputs/cache/analysis_cache.json")
    _cache_enabled = True  # 默认启用缓存
    _cache_ttl = 7 * 24 * 3600  # 7天过期
    _video_context = {}  # 存储视频上下文（URL、路径等）

    def __init__(self, config: dict):
        """初始化分析器，加载LLM配置。"""
        self.config = config
        self.llm_config = config.get("llm", {})
        self.vision_enabled = self.llm_config.get("vision_enabled", False)
        self._load_cache()
        self._video_url = None  # 当前分析的视频 URL
        self._video_path = None  # 当前分析的视频路径

    def _load_cache(self):
        """从文件加载缓存。"""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    self.__class__._cache = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("缓存加载失败，将使用空缓存: %s", e)
            self.__class__._cache = {}

    def set_video_context(self, video_url: str = None, video_path: str = None):
        """设置视频上下文，用于生成更精确的缓存键。

        当提供 video_url 时，缓存键会基于 URL 生成，这样同一个视频的多次分析会命中缓存。
        当提供 video_path 时，会使用文件内容的哈希作为缓存键的一部分。

        Args:
            video_url: 视频 URL（如 B站、YouTube 链接）
            video_path: 本地视频文件路径
        """
        self._video_url = video_url
        self._video_path = video_path

    def _save_cache(self):
        """保存缓存到文件。"""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(self.__class__._cache, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning("缓存保存失败（不影响主流程）: %s", e)

    def _get_cache_key(self, text: str, platform: str) -> str:
        """生成缓存键。

        缓存键生成策略（按优先级）：
        1. 如果有 video_url，使用 URL 的哈希（同一个视频多次分析命中缓存）
        2. 如果有 video_path，使用文件内容的哈希（同一个文件多次分析命中缓存）
        3. 否则，使用文本的哈希（默认行为，保持向后兼容）

        Returns:
            str: 格式为 "platform:hash" 的缓存键
        """
        # 策略 1：基于视频 URL（最精确，同一个视频无论转写结果如何都命中缓存）
        if self._video_url:
            url_hash = hashlib.sha256(self._video_url.encode()).hexdigest()
            return f"{platform}:url:{url_hash}"

        # 策略 2：基于视频文件路径（同一文件多次分析命中缓存）
        if self._video_path:
            try:
                file_path = Path(self._video_path)
                if file_path.exists():
                    # 使用文件大小和修改时间生成哈希（快速且唯一）
                    stat = file_path.stat()
                    file_signature = f"{file_path.name}:{stat.st_size}:{stat.st_mtime}"
                    file_hash = hashlib.sha256(file_signature.encode()).hexdigest()
                    return f"{platform}:file:{file_hash}"
            except OSError:
                pass  # 文件不存在或无法访问，回退到策略 3

        # 策略 3：基于文本内容（默认行为，相同文本命中缓存）
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"{platform}:{text_hash}"

    def _is_cache_valid(self, cache_entry: dict) -> bool:
        """检查缓存条目是否有效（未过期）。"""
        if not isinstance(cache_entry, dict):
            return False
        timestamp = cache_entry.get("_cached_at", 0)
        return (time.time() - timestamp) < self._cache_ttl

    def _encode_image(self, image_path: str) -> str:
        """将图片编码为 base64。"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _create_text_prompt(self, text: str, platform: str, metadata: Optional[dict] = None) -> str:
        """构建纯文本分析提示（优化版，含few-shot示例）。"""
        max_text_len = 8000
        if len(text) > max_text_len:
            text = text[:max_text_len] + "\n\n[文本已截断]"

        # 构建元数据上下文
        metadata_context = ""
        if metadata:
            metadata_context = "\n\n【视频元数据】\n"
            if metadata.get("title"):
                metadata_context += f"标题：{metadata['title']}\n"
            if metadata.get("description"):
                desc = metadata['description'][:500]  # 限制描述长度
                metadata_context += f"简介：{desc}\n"
            if metadata.get("tags"):
                tags = ", ".join(metadata['tags'][:10])  # 最多10个标签
                metadata_context += f"标签：{tags}\n"
            if metadata.get("view_count"):
                metadata_context += f"播放量：{metadata['view_count']}\n"
            if metadata.get("like_count"):
                metadata_context += f"点赞数：{metadata['like_count']}\n"
            if metadata.get("danmaku_count"):
                metadata_context += f"弹幕数：{metadata['danmaku_count']}\n"

        few_shot_example = {
            "theme": "Python环境配置",
            "summary": "介绍如何使用pyenv在macOS上安装和管理多版本Python",
            "tools": [
                {
                    "name": "pyenv",
                    "purpose": "Python版本管理工具",
                    "links": ["https://github.com/pyenv/pyenv"],
                    "install_commands": ["curl https://pyenv.run | bash"],
                    "config_steps": [
                        "echo 'export PATH=\"$HOME/.pyenv/bin:$PATH\"' >> ~/.bashrc",
                        "echo 'eval \"$(pyenv init -)\"' >> ~/.bashrc",
                    ],
                    "run_commands": [],
                    "warnings": ["需要gcc等编译工具"],
                }
            ],
            "needs_credential": False,
            "is_paid": False,
            "alternative_tools": ["conda", "virtualenv"],
        }

        return f"""你是一位资深技术教程分析专家。请分析以下从{platform}视频提取的内容，识别视频中介绍的工具、软件或方法，并输出结构化的行动计划。
        
视频转录文本：
{text}
{metadata_context}
请输出严格的JSON格式（不要有注释、不要有trailing comma），包含以下字段：
- theme: 视频主题（中文，10字以内）
- summary: 视频内容摘要（中文，200字以内，简洁明了）
- tools: 工具列表（数组），每个工具包含：
  - name: 工具名称
  - purpose: 工具用途（中文）
  - links: 相关链接列表（GitHub、官网等，无则空数组）
  - install_commands: 安装命令列表（仅包含安装/下载命令，如 npm install -g、pip install 等；无则空数组）
  - config_steps: 配置步骤列表（安装后的配置命令，无则空数组）
  - run_commands: 启动/运行命令列表（安装完成后如何启动或使用该工具，如 claude --help、code . 等；无则空数组）
  - warnings: 注意事项列表（无则空数组）
- needs_credential: 是否需要密码/密钥/Token（布尔值）
- is_paid: 是否付费（布尔值）
- alternative_tools: 替代工具列表（无则空数组）

【关键区别】：
- install_commands：用来"安装"工具的命令（如 npm install -g pkg、pip install pkg）
- run_commands：用来"启动/使用"工具的命令（如 claude、code .、npx pkg --help）
- 如果视频只介绍了如何启动一个工具（如 Claude Code），请将启动命令放在 run_commands，不要放在 install_commands

【示例输出】
{json.dumps(few_shot_example, ensure_ascii=False, indent=2)}

重要要求：
1. 只输出JSON，不要输出```json```包裹
2. 确保JSON格式合法（可用json.loads解析）
3. 如果视频不涉及工具安装，tools为空数组
4. 所有文本字段使用中文
5. 严格区分 install_commands 和 run_commands
6. 参考视频元数据（如有），结合标题、简介、标签等信息，更准确地理解视频内容

开始分析："""

    def _create_multimodal_prompt(self, text: str, platform: str, frames: list, metadata: Optional[dict] = None) -> list:
        """构建多模态分析提示（文本+关键帧图片）。"""
        max_text_len = 6000
        if len(text) > max_text_len:
            text = text[:max_text_len] + "\n\n[文本已截断]"

        # 构建元数据上下文
        metadata_context = ""
        if metadata:
            metadata_context = "\n\n【视频元数据】\n"
            if metadata.get("title"):
                metadata_context += f"标题：{metadata['title']}\n"
            if metadata.get("description"):
                desc = metadata['description'][:500]
                metadata_context += f"简介：{desc}\n"
            if metadata.get("tags"):
                tags = ", ".join(metadata['tags'][:10])
                metadata_context += f"标签：{tags}\n"
            if metadata.get("view_count"):
                metadata_context += f"播放量：{metadata['view_count']}\n"
            if metadata.get("like_count"):
                metadata_context += f"点赞数：{metadata['like_count']}\n"

        text_prompt = f"""你是一位资深技术教程分析专家。请结合以下视频转录文本和关键帧图片，分析视频中介绍的工具、软件或方法，并输出结构化的行动计划。

视频转录文本：
{text}
{metadata_context}
请输出严格的JSON格式（不要有注释、不要有trailing comma），包含以下字段：
- theme: 视频主题（中文，10字以内）
- summary: 视频内容摘要（中文，200字以内）
- tools: 工具列表（数组），每个工具包含：
  - name: 工具名称
  - purpose: 工具用途（中文）
  - links: 相关链接列表
  - install_commands: 安装命令列表
  - config_steps: 配置步骤列表
  - warnings: 注意事项列表
- needs_credential: 是否需要密码/密钥/Token（布尔值）
- is_paid: 是否付费（布尔值）
- alternative_tools: 替代工具列表

重要：只输出JSON，确保格式合法。参考视频元数据以更准确理解视频内容。"""

        content = [{"type": "text", "text": text_prompt}]

        # 添加关键帧图片（最多3张）
        for i, frame_path in enumerate(frames[:3]):
            try:
                base64_image = self._encode_image(frame_path)
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    }
                )
            except Exception:
                continue  # 跳过无法读取的图片

        return content

    def _call_openai_compatible(self, messages: list) -> str:
        """调用OpenAI兼容接口（支持OpenAI、Ollama、LM Studio等），含指数退避重试。"""
        api_key = self.llm_config.get("api_key")
        base_url = self.llm_config.get("base_url", "https://api.openai.com/v1")
        model = self.llm_config.get("model", "gpt-4o-mini")
        max_tokens = self.llm_config.get("max_tokens", 2048)
        temperature = self.llm_config.get("temperature", 0.3)

        # 对于本地LLM（如Ollama），api_key可以为空
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        import httpx

        # 指数退避重试配置
        max_retries = 3
        base_delay = 2  # 秒
        for attempt in range(max_retries + 1):
            try:
                response = httpx.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=self.llm_config.get("timeout", 120),
                )
                if response.status_code == 429:
                    # 限流：指数退避重试
                    if attempt < max_retries:
                        delay = base_delay * (2**attempt)
                        logger.warning("LLM API 限流(429)，第 %d 次重试，等待 %d 秒", attempt + 1, delay)
                        time.sleep(delay)
                        continue
                    else:
                        response.raise_for_status()  # 最后一次直接抛异常
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.TimeoutException as e:
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    logger.warning("LLM API 超时，第 %d 次重试，等待 %d 秒", attempt + 1, delay)
                    time.sleep(delay)
                    continue
                raise AnalysisError(f"LLM API 超时（已重试 {max_retries} 次）: {e}") from e
            except Exception as e:
                if attempt < max_retries and isinstance(e, (httpx.RequestError, httpx.HTTPStatusError)):
                    delay = base_delay * (2**attempt)
                    logger.warning("LLM API 请求失败，第 %d 次重试，等待 %d 秒: %s", attempt + 1, delay, e)
                    time.sleep(delay)
                    continue
                raise

        raise AnalysisError("重试次数已用尽，但仍未成功调用 LLM API")

    async def _call_openai_compatible_async(self, messages: list) -> str:
        """[异步版本] 调用OpenAI兼容接口，含指数退避重试。"""
        api_key = self.llm_config.get("api_key")
        base_url = self.llm_config.get("base_url", "https://api.openai.com/v1")
        model = self.llm_config.get("model", "gpt-4o-mini")
        max_tokens = self.llm_config.get("max_tokens", 2048)
        temperature = self.llm_config.get("temperature", 0.3)

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        import httpx

        max_retries = 3
        base_delay = 2
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json={
                            "model": model,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                        },
                        timeout=self.llm_config.get("timeout", 120),
                    )
                    if response.status_code == 429:
                        if attempt < max_retries:
                            delay = base_delay * (2**attempt)
                            logger.warning("LLM API 限流(429)，第 %d 次重试，等待 %d 秒", attempt + 1, delay)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            response.raise_for_status()
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except httpx.TimeoutException as e:
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    logger.warning("LLM API 超时，第 %d 次重试，等待 %d 秒", attempt + 1, delay)
                    await asyncio.sleep(delay)
                    continue
                raise AnalysisError(f"LLM API 异步调用超时（已重试 {max_retries} 次）: {e}") from e
            except Exception as e:
                if attempt < max_retries and isinstance(e, (httpx.RequestError, httpx.HTTPStatusError)):
                    delay = base_delay * (2**attempt)
                    logger.warning("LLM API 异步请求失败，第 %d 次重试，等待 %d 秒: %s", attempt + 1, delay, e)
                    await asyncio.sleep(delay)
                    continue
                raise

        raise AnalysisError("异步重试次数已用尽，但仍未成功调用 LLM API")

    def _call_ollama(self, prompt: str) -> str:
        """调用Ollama本地LLM。"""
        base_url = self.llm_config.get("base_url", "http://localhost:11434")
        model = self.llm_config.get("model", "llama3")

        import httpx

        response = httpx.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=self.llm_config.get("timeout", 120),
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    async def _call_ollama_async(self, messages: list) -> str:
        """[异步版本] 调用Ollama本地LLM。"""
        base_url = self.llm_config.get("base_url", "http://localhost:11434")
        model = self.llm_config.get("model", "llama3")

        # 提取最后一条消息的内容
        prompt = messages[-1]["content"]
        if isinstance(prompt, list):
            # 多模态输入，提取文本内容
            text_parts = [p["text"] for p in prompt if p["type"] == "text"]
            prompt = "\n".join(text_parts)

        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=self.llm_config.get("timeout", 120),
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    def _call_llm(self, messages: list) -> str:
        """调用配置的LLM服务获取响应。

        支持多种provider：
        - openai: OpenAI API（及兼容接口）
        - ollama: Ollama本地LLM
        - lm_studio: LM Studio本地LLM（OpenAI兼容模式）
        """
        provider = self.llm_config.get("provider", "mock")

        if provider == "mock":
            raise AnalysisError("LLM provider 设置为 mock，请配置有效的LLM")

        if provider == "ollama":
            # Ollama使用不同的API格式
            prompt = messages[-1]["content"]
            if isinstance(prompt, list):
                # 多模态输入，提取文本内容
                text_parts = [p["text"] for p in prompt if p["type"] == "text"]
                prompt = "\n".join(text_parts)
            return self._call_ollama(prompt)

        # OpenAI兼容接口（包括LM Studio、远程OpenAI等）
        return self._call_openai_compatible(messages)

    def analyze(self, text: str, platform: str = "未知平台", frames: Optional[list] = None, metadata: Optional[dict] = None) -> dict:
        """分析视频内容并返回结构化计划。

        Args:
            text: 视频转录文本
            platform: 视频平台名称
            frames: 关键帧图片路径列表（可选，用于多模态分析）
            metadata: 视频元数据（可选，包含标题、描述、标签等）

        Returns:
            包含分析结果的结构化字典
        """
        # 检查缓存
        if self._cache_enabled:
            cache_key = self._get_cache_key(text, platform)
            if cache_key in self.__class__._cache:
                cache_entry = self.__class__._cache[cache_key]
                if self._is_cache_valid(cache_entry):
                    # 返回缓存结果（移除内部元数据）
                    result = dict(cache_entry)
                    result.pop("_cached_at", None)
                    return result

        # 根据是否启用视觉分析，选择不同的prompt构建方式
        if self.vision_enabled and frames:
            content = self._create_multimodal_prompt(text, platform, frames, metadata)
            messages = [
                {
                    "role": "system",
                    "content": "你是一位资深技术教程分析专家，擅长从视频内容中提取可执行的行动计划。",
                },
                {"role": "user", "content": content},
            ]
        else:
            prompt = self._create_text_prompt(text, platform, metadata)
            messages = [
                {
                    "role": "system",
                    "content": "你是一位资深技术教程分析专家，擅长从视频内容中提取可执行的行动计划。",
                },
                {"role": "user", "content": prompt},
            ]

        try:
            response = self._call_llm(messages)
            result = parse_json_response(response)
            # 添加分析元数据
            result["_metadata"] = {
                "platform": platform,
                "vision_enabled": self.vision_enabled and frames is not None,
                "text_length": len(text),
                "frame_count": len(frames) if frames else 0,
                "has_metadata": metadata is not None,
            }
            # 保存到缓存
            if self._cache_enabled:
                cache_key = self._get_cache_key(text, platform)
                result_with_timestamp = dict(result)
                result_with_timestamp["_cached_at"] = time.time()
                self.__class__._cache[cache_key] = result_with_timestamp
                self._save_cache()
            return result
        except Exception as e:
            logger.warning("LLM 调用失败，返回回退结果：%s", e)
            fallback = self._build_mock_response(text)
            fallback["_llm_error"] = str(e)
            return fallback

    async def analyze_async(self, text: str, platform: str = "未知平台", frames: Optional[list] = None, metadata: Optional[dict] = None) -> dict:
        """异步分析视频内容（真正异步，不阻塞事件循环）。

        Args:
            text: 视频转录文本
            platform: 视频平台名称
            frames: 关键帧图片路径列表（可选，用于多模态分析）
            metadata: 视频元数据（可选，包含标题、描述、标签等）

        Returns:
            包含分析结果的结构化字典
        """
        # 检查缓存
        if self._cache_enabled:
            cache_key = self._get_cache_key(text, platform)
            if cache_key in self.__class__._cache:
                cache_entry = self.__class__._cache[cache_key]
                if self._is_cache_valid(cache_entry):
                    result = dict(cache_entry)
                    result.pop("_cached_at", None)
                    return result

        # 构建消息
        if self.vision_enabled and frames:
            content = self._create_multimodal_prompt(text, platform, frames, metadata)
            messages = [
                {"role": "system", "content": "你是一位资深技术教程分析专家，擅长从视频内容中提取可执行的行动计划。"},
                {"role": "user", "content": content},
            ]
        else:
            prompt = self._create_text_prompt(text, platform, metadata)
            messages = [
                {"role": "system", "content": "你是一位资深技术教程分析专家，擅长从视频内容中提取可执行的行动计划。"},
                {"role": "user", "content": prompt},
            ]

        try:
            # 根据 provider 调用对应的异步方法
            provider = self.llm_config.get("provider", "mock")
            if provider == "mock":
                raise AnalysisError("LLM provider 设置为 mock，请配置有效的LLM")
            elif provider == "ollama":
                response = await self._call_ollama_async(messages)
            else:
                response = await self._call_openai_compatible_async(messages)

            result = parse_json_response(response)
            result["_metadata"] = {
                "platform": platform,
                "vision_enabled": self.vision_enabled and frames is not None,
                "text_length": len(text),
                "frame_count": len(frames) if frames else 0,
                "has_metadata": metadata is not None,
            }
            # 保存到缓存
            if self._cache_enabled:
                cache_key = self._get_cache_key(text, platform)
                result_with_timestamp = dict(result)
                result_with_timestamp["_cached_at"] = time.time()
                self.__class__._cache[cache_key] = result_with_timestamp
                self._save_cache()
            return result
        except Exception as e:
            logger.warning("LLM 异步调用失败，返回回退结果：%s", e)
            fallback = self._build_mock_response(text)
            fallback["_llm_error"] = str(e)
            return fallback

    def _build_mock_response(self, text: str) -> dict:
        """构建未接入LLM时的默认回退响应。"""
        return {
            "theme": "待分析",
            "summary": "当前未配置有效的LLM服务，仅返回占位结果。请配置llm部分后重新分析。",
            "tools": [],
            "needs_credential": False,
            "is_paid": False,
            "alternative_tools": [],
        }

    def analyze_with_llm(self, text: str, platform: str, llm_callable) -> dict:
        """使用外部LLM可调用对象分析内容（兼容旧接口）。"""
        prompt = self._create_text_prompt(text, platform)
        response = llm_callable(prompt)
        return parse_json_response(response)
