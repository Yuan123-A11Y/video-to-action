"""JSON 响应解析工具 - 从 LLM 响应中稳健地提取 JSON。

提供多层解析策略：
1. 直接 json.loads
2. json5 解析（支持 trailing comma）
3. 保守的 trailing comma 修复
4. 提取最外层 {} / [] 片段
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


def parse_json_response(response: str) -> dict:
    """从 LLM 响应中解析 JSON（增强版，处理更多边界情况）。

    解析策略（按优先级）：
    1. 提取 markdown 代码块中的 json
    2. 直接 json.loads
    3. json5.loads（如已安装）
    4. 保守修复 trailing comma
    5. 提取最外层 {} / [] 片段

    Args:
        response: LLM 返回的原始文本

    Returns:
        解析后的字典

    Raises:
        ValueError: 所有解析策略均失败时
    """
    if not response or not response.strip():
        raise ValueError("LLM 返回空响应")

    # 尝试提取 markdown 代码块中的 json
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
    if match:
        response = match.group(1)

    # 清理可能的非法字符
    response = response.strip()

    # 策略 1：优先尝试直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 策略 2：尝试使用 json5 解析（支持 trailing comma）
    try:
        import json5

        return json5.loads(response)
    except ImportError:
        pass  # json5 未安装，继续后续处理
    except Exception:
        pass

    # 策略 3：尝试修复常见的 JSON 格式问题（保守方式）
    # 只修复明显的 trailing comma（在 } 或 ] 前的逗号）
    try:
        fixed = re.sub(r",\s*(\}|\])", r"\1", response)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 策略 4：提取最长的 JSON 片段（最外层 {} 或 []）
    try:
        fragment = _extract_outer_json(response)
        if fragment:
            return json.loads(fragment)
    except json.JSONDecodeError:
        pass

    raise ValueError(f"无法 parse LLM 返回的 JSON\n原始响应: {response[:500]}")


def _extract_outer_json(text: str) -> str | None:
    """从文本中提取最外层的 JSON 对象或数组。

    找到第一个未匹配的左括号 { 或 [，然后找到对应的右括号 } 或 ]，
    同时正确处理嵌套。

    Returns:
        最外层 JSON 字符串，或 None（未找到时）
    """
    stack = []
    start = None
    for i, ch in enumerate(text):
        if ch == "{" or ch == "[":
            if not stack:
                start = i
            stack.append(ch)
        elif ch == "}" or ch == "]":
            if stack:
                opening = stack.pop()
                if (ch == "}" and opening == "{") or (ch == "]" and opening == "["):
                    if not stack and start is not None:
                        return text[start : i + 1]
    return None


def repair_json(json_str: str) -> str:
    """尝试修复常见 JSON 格式问题。

    修复项目：
    - trailing commas（对象/数组末尾多余逗号）
    - 单引号字符串 → 双引号
    - 未加引号的键名 → 加双引号

    注意：此函数使用保守策略，避免破坏字符串内容。

    Args:
        json_str: 可能不合法的 JSON 字符串

    Returns:
        修复后的 JSON 字符串
    """
    # 修复 trailing commas（在 } 或 ] 前的逗号及空白）
    repaired = re.sub(r",\s*(\}|\])", r"\1", json_str)

    # 可选：如果 json5 可用，用 json5 做更强大的修复
    try:
        import json5

        parsed = json5.loads(repaired)
        return json.dumps(parsed, ensure_ascii=False)
    except ImportError:
        return repaired
    except Exception:
        return repaired
