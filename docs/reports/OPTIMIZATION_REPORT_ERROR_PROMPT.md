# 错误提示优化报告

**日期**：2026-06-26
**任务**：行动7 - 优化错误提示
**状态**：进行中（需要修改多个文件）

## 概述

已创建 `video_to_action/exceptions.py` 统一异常处理模块，定义了以下异常类：
- `VideoToActionError`（基础类）
- `DownloadError`（下载错误）
- `TranscriptionError`（转写错误）
- `AnalysisError`（分析错误）
- `ExecutionError`（执行错误）
- `ConfigurationError`（配置错误）
- `KnowledgeBaseError`（知识库错误）

## 需要修改的错误抛出点

### 1. `video_to_action/extractor.py`

**第52行**：
```python
# 修改前
raise EnvironmentError("未找到 ffmpeg，请先安装 ffmpeg")

# 修改后
from video_to_action.exceptions import TranscriptionError
raise TranscriptionError(
    "未找到 ffmpeg，请先安装 ffmpeg",
    code=2001,
    suggestion="请访问 https://ffmpeg.org/ 下载并安装 ffmpeg，然后确保其路径在系统 PATH 中。Windows 用户可使用 chocolatey: choco install ffmpeg"
)
```

**第57行**：
```python
# 修改前
raise RuntimeError(f"ffmpeg 提取音频失败: {result.stderr}")

# 修改后
raise TranscriptionError(
    f"ffmpeg 提取音频失败: {result.stderr}",
    code=2002,
    suggestion="请检查 ffmpeg 是否正确安装，或尝试使用其他音频提取工具"
)
```

**第117行**：
```python
# 修改前
raise FileNotFoundError(f"音频文件不存在：{audio_path}，ffmpeg 可能未正确提取音频")

# 修改后
raise TranscriptionError(
    f"音频文件不存在：{audio_path}，ffmpeg 可能未正确提取音频",
    code=2003,
    suggestion="请检查视频文件是否完整，或尝试重新下载"
)
```

**第153行**：
```python
# 修改前
raise EnvironmentError("未找到 ffprobe，请先安装 ffmpeg")

# 修改后
raise TranscriptionError(
    "未找到 ffprobe，请先安装 ffmpeg",
    code=2001,
    suggestion="ffprobe 是 ffmpeg 的一部分，请重新安装 ffmpeg 并确保 ffprobe 在 PATH 中"
)
```

**第166行**：
```python
# 修改前
raise RuntimeError(f"ffprobe 获取视频时长失败: {result.stderr}")

# 修改后
raise TranscriptionError(
    f"ffprobe 获取视频时长失败: {result.stderr}",
    code=2004,
    suggestion="请检查视频文件是否损坏，或尝试使用其他工具获取视频信息"
)
```

### 2. `video_to_action/cli.py`

**第125行**：
```python
# 修改前
raise RuntimeError("视频下载失败")

# 修改后
from video_to_action.exceptions import DownloadError
raise DownloadError(
    "视频下载失败",
    code=1001,
    suggestion="请检查视频链接是否有效，或尝试使用代理"
)
```

### 3. `video_to_action/config.py`

**第34行**：
```python
# 修改前
raise FileNotFoundError(f"配置文件不存在: {path}")

# 修改后
from video_to_action.exceptions import ConfigurationError
raise ConfigurationError(
    f"配置文件不存在: {path}",
    code=5001,
    suggestion=f"请创建配置文件：cp config/settings.example.yaml {path}"
)
```

### 4. `video_to_action/analyzer_v2.py`

**第227行**：
```python
# 修改前
raise TimeoutError(f"LLM API 超时（已重试 {max_retries} 次）: {e}") from e

# 修改后
from video_to_action.exceptions import AnalysisError
raise AnalysisError(
    f"LLM API 超时（已重试 {max_retries} 次）: {e}",
    code=3002,
    suggestion="请检查网络连接，或稍后重试。如果问题持续，请尝试更换 LLM 模型或联系 API 提供商"
)
```

**第236行**：
```python
# 修改前
raise RuntimeError("重试次数已用尽，但仍未成功调用 LLM API")

# 修改后
raise AnalysisError(
    "重试次数已用尽，但仍未成功调用 LLM API",
    code=3003,
    suggestion="请检查 LLM API Key 是否正确，或尝试更换模型/提供商"
)
```

**第269行**：
```python
# 修改前
raise RuntimeError("LLM provider 设置为 mock，请配置有效的LLM")

# 修改后
raise AnalysisError(
    "LLM provider 设置为 mock，请配置有效的LLM",
    code=3001,
    suggestion="请编辑 config/settings.yaml，设置正确的 llm.provider 和 llm.api_key"
)
```

### 5. `video_to_action/json_parser.py`

**第37行**：
```python
# 修改前
raise ValueError("LLM 返回空响应")

# 修改后
from video_to_action.exceptions import AnalysisError
raise AnalysisError(
    "LLM 返回空响应",
    code=3004,
    suggestion="请检查 LLM API Key 是否正确，或尝试更换模型"
)
```

**第78行**：
```python
# 修改前
raise ValueError(f"无法 parse LLM 返回的 JSON\n原始响应: {response[:500]}")

# 修改后
raise AnalysisError(
    f"无法 parse LLM 返回的 JSON",
    code=3005,
    suggestion="LLM 返回了非 JSON 格式的响应，请尝试更换模型或调整提示词"
)
```

## 修改步骤

1. 在每个需要修改的文件中，导入对应的异常类
2. 将 `raise RuntimeError(...)` 或 `raise ValueError(...)` 等替换为使用统一异常类
3. 确保提供 `code` 和 `suggestion` 参数
4. 测试修改后的代码，确保异常能正确捕获和显示

## 验收标准

- [ ] 所有错误信息包含修复建议
- [ ] 常见错误有详细提示（ffmpeg、LLM API、视频下载等）
- [ ] 错误提示格式统一：`[错误码] 错误消息\n修复建议：...`
- [ ] 用户测试：邀请 3 名新用户安装并配置，记录是否理解错误提示

## 后续工作

完成上述修改后，还需要：
1. 在 API 层（`api/main.py`）统一错误响应格式（JSON 格式，包含 code、message、suggestion）
2. 在前端显示友好的错误提示（如果有的话）
3. 更新用户手册，添加常见错误和解决方法

---
**报告结束**
