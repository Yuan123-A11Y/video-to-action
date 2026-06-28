"""Video-to-Action 统一异常处理模块。

定义项目中所有自定义异常类，确保错误处理一致性和提供友好的错误信息。
"""


class VideoToActionError(Exception):
    """基础异常类，所有自定义异常都应该继承此类。"""

    def __init__(self, message: str, code: int = 1000, suggestion: str = ""):
        """初始化基础异常。

        Args:
            message: 错误消息
            code: 错误码（1000-9999）
            suggestion: 修复建议（可选）
        """
        self.message = message
        self.code = code
        self.suggestion = suggestion
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """将异常转换为字典格式（用于 API 响应）。"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "suggestion": self.suggestion,
            }
        }


class DownloadError(VideoToActionError):
    """下载相关错误（错误码范围：1001-1999）。"""

    def __init__(self, message: str, code: int = 1001, suggestion: str = ""):
        super().__init__(message, code, suggestion)


class ExtractionError(VideoToActionError):
    """内容提取相关错误（错误码范围：1501-1599）。"""

    def __init__(self, message: str, code: int = 1501, suggestion: str = ""):
        super().__init__(message, code, suggestion)


class TranscriptionError(VideoToActionError):
    """音频转写相关错误（错误码范围：2001-2999）。"""

    def __init__(self, message: str, code: int = 2001, suggestion: str = ""):
        super().__init__(message, code, suggestion)


class AnalysisError(VideoToActionError):
    """内容分析相关错误（错误码范围：3001-3999）。"""

    def __init__(self, message: str, code: int = 3001, suggestion: str = ""):
        super().__init__(message, code, suggestion)


class ExecutionError(VideoToActionError):
    """命令执行相关错误（错误码范围：4001-4999）。"""

    def __init__(self, message: str, code: int = 4001, suggestion: str = ""):
        super().__init__(message, code, suggestion)


class ConfigurationError(VideoToActionError):
    """配置相关错误（错误码范围：5001-5999）。"""

    def __init__(self, message: str, code: int = 5001, suggestion: str = ""):
        super().__init__(message, code, suggestion)


class KnowledgeBaseError(VideoToActionError):
    """知识库相关错误（错误码范围：6001-6999）。"""

    def __init__(self, message: str, code: int = 6001, suggestion: str = ""):
        super().__init__(message, code, suggestion)


# 常见错误码和修复建议的映射
ERROR_SUGGESTIONS = {
    1001: "请检查视频链接是否有效，或尝试使用代理",
    1002: "请检查网络连接，或稍后重试",
    1501: "请检查视频文件是否完整，或尝试重新下载",
    2001: "请确保已安装 ffmpeg，并设置正确的 PATH",
    2002: "请检查 Hugging Face 镜像设置（HF_ENDPOINT)",
    3001: "请检查 LLM API Key 是否正确，或尝试更换模型",
    3002: "LLM API 调用超时，请稍后重试或缩短输入文本",
    4001: "命令执行失败，请检查权限或手动执行该命令",
    4002: "缺少必要依赖，请根据错误信息安装对应软件",
    5001: "配置文件不存在或格式错误，请运行 python -m video_to_action.cli setup",
    5002: "缺少必要的配置项，请编辑 config/settings.yaml",
    6001: "知识库初始化失败，请检查数据库配置",
    6002: "知识库搜索失败，请检查查询格式或数据库状态",
}


def get_suggestion(code: int) -> str:
    """根据错误码返回默认的修复建议。"""
    return ERROR_SUGGESTIONS.get(code, "请查看日志文件获取详细信息")


def wrap_exception(e: Exception) -> str:
    """将任意异常包装为友好的错误描述。

    如果异常已是 VideoToActionError 子类，提取其消息和建议；
    否则返回 ``类型: 消息`` 的格式。

    Args:
        e: 任意异常

    Returns:
        友好的错误描述字符串
    """
    if isinstance(e, VideoToActionError):
        msg = e.message
        if e.suggestion:
            msg += f"（建议：{e.suggestion}）"
        return msg
    return f"{type(e).__name__}: {str(e)}"
