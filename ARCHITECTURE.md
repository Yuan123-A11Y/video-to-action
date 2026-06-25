# Video-to-Action 系统架构设计文档

## 1. 项目概述

**Video-to-Action** 是一个智能视频内容分析与操作执行系统。该系统能够：
- 从抖音、B站、YouTube等平台自动下载视频
- 提取视频中的音频、转写文本、关键帧
- 通过LLM分析视频内容，识别工具/方法
- 自动生成安装/配置方案并执行

**核心价值**：将视频教程转化为可执行的行动方案，降低技术学习门槛。

---

## 2. 系统架构

### 2.1 架构分层

```
┌─────────────────────────────────────────────────┐
│              用户输入层                          │
│        视频URL + 命令行参数                      │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              CLI 命令行接口层                    │
│          cli.py - 参数解析与调度                 │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              核心处理层                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │Downloader│ │Extractor │ │Analyzer  │      │
│  │视频下载器 │ │内容提取器 │ │分析器     │      │
│  └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐                    │
│  │Resolver   │ │Executor  │                    │
│  │错误修复   │ │执行器     │                    │
│  └──────────┘ └──────────┘                    │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              配置与工具层                         │
│  ┌──────────┐ ┌──────────┐                    │
│  │ Config   │ │  Tools   │                    │
│  │配置文件   │ │工具函数库 │                    │
│  └──────────┘ └──────────┘                    │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              输出层                               │
│    outputs/ - 报告、转录、音频、图片             │
└─────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| **编程语言** | Python 3.12+ | 主开发语言 |
| **视频下载** | yt-dlp | 多平台视频下载 |
| **音频处理** | ffmpeg | 音频提取、关键帧截取 |
| **语音转写** | faster-whisper | 音频转文字（支持中文） |
| **LLM分析** | OpenAI API / 自定义 | 视频内容理解与方案生成 |
| **配置管理** | PyYAML | 配置文件解析 |
| **网络请求** | requests / httpx | HTTP请求 |
| **网页解析** | BeautifulSoup4 | HTML解析 |
| **浏览器自动化** | Playwright | 动态网页处理 |

---

## 3. 核心模块说明

### 3.1 CLI 模块（`cli.py`）

**职责**：命令行接口，参数解析与任务调度

**关键功能**：
- 解析用户输入的视频URL和参数
- 支持4种自动化级别：`extract`、`observe`、`confirm`、`auto`
- 协调各模块执行顺序
- 处理输出格式与保存路径

**输入**：
- 视频URL（抖音/B站/YouTube）
- `--level`：自动化级别
- `--output`：输出目录

**输出**：
- 控制台进度信息
- 调用各核心模块

---

### 3.2 Downloader 模块（`downloader.py`）

**职责**：视频下载器，支持多平台

**关键功能**：
- 使用yt-dlp下载主流平台视频
- 针对B站API的特殊处理
- 支持Cookies认证（抖音等需登录平台）
- 视频元数据提取

**核心方法**：
```python
def download(self, url: str) -> Path  # 下载视频，返回本地路径
def _download_bilibili(self, url: str) -> Path  # B站专用下载
def _get_cookies(self) -> str  # 读取Cookies配置
```

**输出**：
- 视频文件（MP4格式）
- 视频元数据（标题、时长等）

---

### 3.3 Extractor 模块（`extractor.py`）

**职责**：从视频中提取音频、转写文本、关键帧

**关键功能**：
- 使用ffmpeg提取音频（16kHz单声道PCM）
- 使用faster-whisper转写音频为带时间戳的文本
- 均匀截取关键帧（默认5张）
- 文本清理与格式化

**核心方法**：
```python
def extract_audio(self, video_path: Path) -> Path  # 提取音频
def transcribe(self, audio_path: Path) -> list[dict]  # 转写音频
def extract_frames(self, video_path: Path, count: int) -> list[Path]  # 截取关键帧
def process(self, video_path: Path) -> dict  # 完整处理流程
```

**输出**：
- 音频文件（WAV格式）
- 转写文本（带时间戳的segments）
- 关键帧图片（JPG格式）
- 完整文本（合并所有segments）

---

### 3.4 Analyzer 模块（`analyzer_v2.py`）

**职责**：调用LLM分析视频内容，生成操作方案

**关键功能**：
- 构建LLM分析Prompt（包含转录文本和任务描述）
- 支持多种LLM后端（OpenAI、本地模型等）
- 解析LLM返回的结构化结果
- 生成操作方案（工具列表、安装命令、配置步骤）

**核心方法**：
```python
def analyze(self, transcription: dict) -> dict  # 分析转录文本
def _build_prompt(self, text: str) -> str  # 构建分析Prompt
def _call_llm(self, prompt: str) -> str  # 调用LLM
def _parse_result(self, raw: str) -> dict  # 解析LLM返回结果
```

**输出**（结构化JSON）：
```json
{
  "theme": "视频主题",
  "summary": "内容摘要",
  "tools": [
    {
      "name": "工具名称",
      "install_commands": ["安装命令"],
      "config_steps": ["配置步骤"],
      "warnings": ["注意事项"]
    }
  ],
  "needs_credential": false,
  "is_paid": false,
  "alternative_tools": ["替代工具"]
}
```

---

### 3.5 Resolver 模块（`resolver.py`）

**职责**：错误诊断与自动修复

**关键功能**：
- 识别常见错误（命令未找到、网络超时、权限不足等）
- 生成修复建议
- 提取可执行的修复命令
- 支持多次重试与自动修复

**核心方法**：
```python
def suggest_fix(self, command: str, error_output: str) -> str | None  # 建议修复方案
def resolve(self, command: str, error_output: str, attempt: int) -> dict  # 执行修复
def _extract_executable_command(self, suggestion: str) -> str | None  # 提取可执行命令
```

**支持的错误类型**：
- pip/npm/git命令未找到
- 网络超时（自动切换镜像源）
- 权限不足（提示使用sudo）
- ffmpeg/yt-dlp未安装

---

### 3.6 Executor 模块（`executor.py`）

**职责**：执行安装/配置操作（待完整实现）

**关键功能**：
- 根据Analyzer生成的操作方案执行命令
- 支持dry-run模式（仅打印命令不执行）
- 安全边界检查（危险操作需确认）
- 执行结果验证

**安全边界**：
- 运行远程脚本（curl | bash等）需确认
- 输入密码/API Key需确认
- 修改系统环境变量需确认
- 安装系统级软件需确认
- 连续3次自动修复失败需确认

---

## 4. 数据流

### 4.1 完整数据流图

```
用户输入: 视频URL
    │
    ▼
[CLI 参数解析]
    │
    ▼
[Downloader 下载视频] ────→ outputs/videos/
    │
    ▼
[Extractor 提取内容]
    ├─→ 提取音频 ────→ outputs/audio/
    ├─→ 转写文本 ────→ outputs/transcripts/
    └─→ 截取关键帧 ──→ outputs/frames/
    │
    ▼
[Analyzer LLM分析]
    │
    ▼
{根据 --level 参数决定后续流程}
    │
    ├─→ extract: 仅提取文本，输出供Trae分析的Prompt
    ├─→ observe: 只分析并输出计划，不执行
    ├─→ confirm: 每步执行前询问用户
    └─→ auto: 自动执行，仅在危险操作时询问
    │
    ▼
[Executor 执行操作]（如选择auto/confirm模式）
    │
    ▼
[Resolver 错误修复] ←─── 如执行失败
    │
    ▼
输出最终结果:
    ├─→ Markdown报告 ────→ outputs/reports/
    ├─→ JSON数据 ──────→ outputs/data/
    └─→ 执行日志 ──────→ 控制台输出
```

### 4.2 数据格式

**转录文本格式**：
```json
{
  "audio_path": "outputs/audio/video.wav",
  "segments": [
    {"start": 0.0, "end": 5.2, "text": "欢迎来到本期教程..."}
  ],
  "frames": ["outputs/frames/frame_1.jpg", ...],
  "text": "欢迎来到本期教程..."
}
```

**分析报告格式**：
```json
{
  "theme": "Python环境配置",
  "summary": "介绍如何使用pyenv安装多版本Python",
  "tools": [
    {
      "name": "pyenv",
      "install_commands": ["curl https://pyenv.run | bash"],
      "config_steps": ["配置环境变量"],
      "warnings": ["需要gcc编译工具"]
    }
  ],
  "needs_credential": false,
  "is_paid": false,
  "alternative_tools": ["conda", "virtualenv"]
}
```

---

## 5. 配置说明

### 5.1 配置文件结构（`config/settings.yaml`）

```yaml
# LLM配置
llm:
  provider: "openai"  # openai / local / custom
  model: "gpt-4"
  api_key: "sk-..."  # 或从环境变量读取
  api_base: "https://api.openai.com/v1"  # 可选自定义端点
  temperature: 0.7
  max_tokens: 2000

# 转录配置
transcription:
  model: "base"  # tiny / base / small / medium / large
  language: "zh"  # 中文
  device: "cpu"  # cpu / cuda
  compute_type: "int8"  # int8 / float16 / float32

# 下载配置
download:
  output_dir: "outputs/videos"
  cookies_file: "config/douyin_cookies.txt"  # 可选
  format: "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

# 提取配置
extraction:
  audio_format: "wav"
  sample_rate: 16000
  channels: 1
  frame_count: 5  # 关键帧数量

# 输出配置
output:
  base_dir: "outputs"
  save_audio: true
  save_frames: true
  save_transcript: true
  report_format: "markdown"  # markdown / html / pdf

# 安全配置
safety:
  dry_run: false  # 是否仅打印命令不执行
  confirm_dangerous: true  # 危险操作是否确认
  dangerous_patterns:  # 危险命令模式
    - "rm -rf"
    - "curl | bash"
    - "wget | sh"
    - "sudo"
  max_retries: 3  # 最大自动修复次数
```

### 5.2 环境变量

```bash
# LLM API Key（推荐方式，避免硬编码）
export OPENAI_API_KEY="sk-..."

# ffmpeg路径（如未添加到PATH）
export FFMPEG_PATH="/usr/local/bin/ffmpeg"

# 输出目录（可选，覆盖配置文件）
export V2A_OUTPUT_DIR="/path/to/output"
```

---

## 6. 使用指南

### 6.1 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt -i https://mirrors.huaweicloud.com/repository/pypi/simple/

# 安装ffmpeg（必需）
# Windows: 从 https://ffmpeg.org/download.html 下载并添加到PATH
# macOS: brew install ffmpeg
# Ubuntu/Debian: sudo apt install ffmpeg

# 安装yt-dlp（必需）
pip install yt-dlp -i https://mirrors.huaweicloud.com/repository/pypi/simple/
```

### 6.2 配置

```bash
# 复制配置模板
cp config/settings.example.yaml config/settings.yaml

# 编辑配置文件，填入LLM API Key等
vim config/settings.yaml
```

### 6.3 使用示例

**模式1：仅提取文本（推荐首次使用）**
```bash
python -m video_to_action.cli "https://v.douyin.com/abc123" --level extract
```
- 下载视频并提取音频、转写文本
- 输出供Trae分析的Prompt
- 不调用外部LLM（无需API Key）

**模式2：分析但不执行**
```bash
python -m video_to_action.cli "https://www.bilibili.com/video/BV1xx411c7mD" --level observe
```
- 下载视频并分析内容
- 输出操作计划，不执行

**模式3：每步确认后执行**
```bash
python -m video_to_action.cli "https://www.youtube.com/watch?v=xxx" --level confirm
```
- 分析内容后，每步执行前询问用户

**模式4：全自动执行（谨慎使用）**
```bash
python -m video_to_action.cli "https://v.douyin.com/abc123" --level auto
```
- 自动执行所有操作
- 仅在危险操作时询问

### 6.4 输出结果

执行后，结果保存在`outputs/`目录：

```
outputs/
├── videos/          # 下载的视频
├── audio/           # 提取的音频
├── transcripts/     # 转写文本（JSON格式）
├── frames/          # 关键帧图片
├── reports/         # Markdown分析报告
└── logs/            # 执行日志
```

---

## 7. 安全边界

系统设置了多重安全机制，防止误操作：

### 7.1 危险操作检测

以下操作会自动暂停并请求用户确认：
- 运行远程脚本（`curl | bash`、`wget | sh`）
- 输入密码/API Key/Token
- 修改系统环境变量
- 安装系统级软件（`apt install`、`brew install`等）
- 删除操作（`rm -rf`、`del /S /Q`等）
- 检测到危险命令模式

### 7.2 自动修复限制

- 连续3次自动修复失败后，暂停并请求用户介入
- 无法识别的错误不自动修复

### 7.3 Dry-Run模式

设置`dry_run: true`后，系统仅打印将要执行的命令，不实际执行，方便调试。

---

## 8. 扩展开发

### 8.1 添加新的视频平台支持

在`downloader.py`中添加新的下载方法：

```python
def _download_newplatform(self, url: str) -> Path:
    """下载新平台视频。"""
    # 实现下载逻辑
    pass
```

然后在`download()`方法中添加平台识别：

```python
if "newplatform.com" in url:
    return self._download_newplatform(url)
```

### 8.2 添加新的LLM后端

在`analyzer_v2.py`中扩展`_call_llm()`方法：

```python
def _call_llm(self, prompt: str) -> str:
    provider = self.config.get("llm", {}).get("provider", "openai")
    
    if provider == "new_llm":
        return self._call_new_llm(prompt)
    # ... 其他provider
```

### 8.3 自定义输出格式

修改`cli.py`中的输出处理逻辑，或继承基类添加新格式。

---

## 9. 测试

### 9.1 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定模块测试
pytest tests/test_downloader.py
pytest tests/test_extractor.py
pytest tests/test_analyzer_v2.py

# 查看覆盖率
pytest --cov=video_to_action tests/
```

### 9.2 测试覆盖

- **单元测试**：各模块独立测试
- **集成测试**：完整流程测试（`test_integration.py`）
- **Mock测试**：模拟LLM调用、网络请求等

---

## 10. 未来规划

### 10.1 近期计划

- [ ] 完善Operator模块，支持更多操作类型
- [ ] 添加Web UI界面
- [ ] 支持更多视频平台（快手、小红书等）
- [ ] 优化LLM分析Prompt，提高准确率
- [ ] 添加多语言支持

### 10.2 长期愿景

- [ ] 构建视频知识库，支持跨视频搜索
- [ ] 社区分享平台，上传/下载操作方案
- [ ] 支持实时视频流分析
- [ ] 集成更多AI能力（视觉理解、代码生成等）

---

## 附录

### A. 参考资料

- [yt-dlp 官方文档](https://github.com/yt-dlp/yt-dlp)
- [faster-whisper 项目](https://github.com/guillaumekln/faster-whisper)
- [OpenAI API 文档](https://platform.openai.com/docs)

### B. 常见问题

**Q: ffmpeg未找到？**
A: 请确保ffmpeg已安装并添加到系统PATH，或设置`FFMPEG_PATH`环境变量。

**Q: LLM分析失败？**
A: 检查config/settings.yaml中的API Key是否正确，或网络是否可访问LLM服务。

**Q: 抖音视频下载失败？**
A: 抖音需要登录才能下载，请在config/douyin_cookies.txt中填入浏览器Cookies。

---

**文档版本**: v1.0
**最后更新**: 2026-06-25
**维护者**: Video-to-Action Team
