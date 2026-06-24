# Video-to-Action 视频到行动助手

把抖音、B站、YouTube 上的教程视频自动变成可用的工具和配置。

## 功能

- 自动下载视频（支持 douyin-downloader / yt-dlp / GreenVideo 备选方案）
- 提取关键帧截图
- 语音转写（faster-whisper）
- 识别视频中介绍的工具、安装命令和配置步骤
- 自动执行安装和配置（可选，支持确认模式）
- 遇到错误自动搜索修复方案
- 生成中文操作笔记

## 环境依赖

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/)（用于音频提取）
- [git](https://git-scm.com/)
- （可选）Playwright Chromium（用于 GreenVideo 备选方案）

## 安装步骤

```bash
# 克隆项目
git clone https://github.com/你的用户名/video-to-action.git
cd video-to-action

# 创建虚拟环境（推荐）
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt -i https://mirrors.huaweicloud.com/repository/pypi/simple/

# 安装 Playwright 浏览器（如需使用 GreenVideo 备选方案）
playwright install chromium
```

## 配置

复制配置模板并填写真实值：

```bash
cp config/settings.example.yaml config/settings.yaml
```

编辑 `config/settings.yaml`，按需修改：

```yaml
# 自动化级别: observe(仅分析), confirm(每步确认), auto(自动执行)
automation_level: confirm

# LLM 配置（可选，未配置时返回占位结果）
llm:
  provider: openai
  api_key: ${AGNES_API_KEY}   # 推荐用环境变量，避免硬编码
  base_url: https://apihub.agnes-ai.com/v1
  model: agnes-2.0-flash
```

> **注意**：Cookie 等敏感信息请放入 `config/douyin_cookies.txt`，该文件已被 `.gitignore` 忽略，不会上传到 GitHub。

## 使用方法

### 命令行

```bash
# 提取模式（下载视频 + 转写文本 + 关键帧，无需 LLM API Key）
python -m video_to_action.cli "https://v.douyin.com/abc123" --level extract

# 自动模式（需要配置 LLM）
python -m video_to_action.cli "https://v.douyin.com/abc123"

# 确认模式（每步执行前询问）
python -m video_to_action.cli "https://www.bilibili.com/video/BV1xx411c7mD" --level confirm

# 观察模式（只分析不执行）
python -m video_to_action.cli "https://www.youtube.com/watch?v=abc123" --level observe
```

### Trae Skill

将 `skill/SKILL.md` 安装到 Trae 后，直接在对话中发送视频链接即可。

## 输出

所有输出保存在 `outputs/` 目录：

| 文件 | 说明 |
|------|------|
| `douyin_*.mp4` | 下载的视频 |
| `*.wav` | 提取的音频 |
| `*.txt` | 转写文本 |
| `frames/*_frame_*.jpg` | 关键帧截图 |
| `reports/report_*.md` | 中文操作笔记 |

## 常见问题

**Q：抖音视频下载失败？**
> 需要在 `config/douyin_cookies.txt` 中放入有效的抖音 Cookie（Netscape 格式），或用浏览器登录后导出。

**Q：转写报 Hugging Face 连接超时？**
> 设置国内镜像：`set HF_ENDPOINT=https://hf-mirror.com`（Windows）或 `export HF_ENDPOINT=https://hf-mirror.com`（macOS/Linux）。

**Q：如何只下载视频不执行命令？**
> 使用 `--level extract` 参数，只做下载、截图和转写，不调用 LLM 也不执行任何命令。

## License

MIT
