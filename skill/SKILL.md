---
name: video-to-action
description: 接收抖音/B站/YouTube视频链接，自动下载、提取内容，由 Trae 自身模型分析并生成操作方案
---

# 视频到行动助手

自动分析视频链接中的工具/方法，并尝试完成安装或配置。

## 触发方式

用户发送视频链接，例如：

```
帮我安装这个视频里的工具：https://v.douyin.com/abc123
```

## 处理流程

1. 识别视频平台（抖音/B站/YouTube）
2. 下载视频（yt-dlp 主方案，GreenVideo 备选）
3. 提取音频并转写文字
4. **由 Trae 自身大模型分析转录文本**，生成安装/配置计划
5. 根据分析结果，在对话中指导或自动执行安装/配置
6. 生成中文操作笔记

## 标准操作步骤

当用户发送视频链接时，请按以下步骤执行：

1. 运行提取命令，获取视频转录文本和 Trae 分析 Prompt：

   ```bash
   python -m video_to_action.cli "<视频链接>" --level extract
   ```

2. 读取命令输出的【视频转录文本】和【供 Trae 分析的 Prompt】。
3. 使用你的大模型能力分析转录文本，识别视频中介绍的工具、安装命令和配置步骤。
4. 将分析结果以结构化 JSON 形式输出，包含：
   - theme: 视频主题
   - summary: 摘要
   - tools: 工具列表（含 install_commands、config_steps、warnings）
   - needs_credential: 是否需要凭证
   - is_paid: 是否付费
   - alternative_tools: 替代工具
5. 根据分析结果，在对话中帮助用户执行安装或配置；危险操作必须请求用户确认。
6. 如需自动生成完整报告，可运行：

   ```bash
   python -m video_to_action.cli "<视频链接>" --level auto
   ```

   注意：auto 模式需要在 `config/settings.yaml` 中配置外部 LLM，否则分析步骤会回退到占位结果。

## 自动化级别

- `extract`：仅下载并提取文本，由 Trae 自身模型分析（无需外部 LLM API Key）
- `observe`：只分析视频并输出计划，不执行
- `confirm`：每步执行前询问
- `auto`：自动执行，仅在运行远程脚本/需要凭证/危险操作/连续失败时询问

默认推荐先用 `extract` 模式，再由你（Trae）进行内容理解和操作。

## 安全边界

以下操作会自动暂停并请求用户确认：
- 运行远程脚本（curl | bash 等）
- 输入密码/API Key/Token
- 修改系统环境变量
- 安装系统级软件
- 检测到危险命令
- 连续 3 次自动修复失败

## 输出

- 安装/配置后的可用工具
- Markdown 格式中文操作笔记（保存在 `outputs/reports/`）
