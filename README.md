# Video-to-Action 视频到行动助手

把抖音、B站、YouTube 上的教程视频变成可用的工具和配置。

## 功能

- 自动下载视频（支持 yt-dlp 和 GreenVideo 备选方案）
- 语音转写并理解视频内容
- 识别视频中介绍的工具、安装命令和配置步骤
- 自动执行安装和配置
- 遇到错误自动搜索修复方案
- 生成中文操作笔记

## 安装

```bash
# 克隆项目
cd g:\trae\video-to-action

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt -i https://mirrors.huaweicloud.com/repository/pypi/simple/

# 安装 Playwright 浏览器
playwright install chromium
```

## 依赖

- Python 3.10+
- ffmpeg
- git
- yt-dlp

## 使用方法

### 命令行

```bash
# 自动模式
python -m video_to_action.cli "https://v.douyin.com/abc123"

# 确认模式
python -m video_to_action.cli "https://www.bilibili.com/video/BV1xx411c7mD" --level confirm

# 观察模式（只分析不执行）
python -m video_to_action.cli "https://www.youtube.com/watch?v=abc123" --level observe
```

### Trae Skill

将 `skill/SKILL.md` 安装到 Trae 后，直接在对话中发送视频链接即可。

## 配置

编辑 `config/settings.yaml`：

```yaml
automation_level: auto
max_retries: 3
```

## 输出

所有输出保存在 `outputs/` 目录：
- 下载的视频
- 提取的音频
- 转写文本
- 关键帧截图
- 中文操作笔记（`outputs/reports/report_*.md`）
