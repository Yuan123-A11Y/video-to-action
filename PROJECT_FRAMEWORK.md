# Video-to-Action 项目框架整理

> 版本：v0.1.0 | 整理时间：2026-06-25 | 维护者：老板 & 程

---

## 一、项目概述

**项目名称：** Video-to-Action（视频到行动助手）

**核心功能：** 将抖音、B站、YouTube 等平台的教程视频自动转化为可执行的工具和配置方案。

**工作原理：**
```
视频链接 → 下载视频 → 提取音频 → 语音转写 → LLM分析内容 → 生成行动计划 → 自动执行
```

**技术栈：**
- Python 3.12+
- yt-dlp（通用视频下载）
- faster-whisper（本地语音转写）
- Playwright（浏览器自动化）
- httpx（LLM API 调用）
- Rich（CLI 进度显示）

---

## 二、目录结构

```
video-to-action/
├── video_to_action/          # 核心包
│   ├── __init__.py          # 包版本 v0.1.0
│   ├── cli.py               # CLI 入口（typer 子命令）
│   ├── config.py            # 配置加载（YAML + 环境变量）
│   ├── downloader.py        # 下载器兼容层（重新导出）
│   ├── douyin_downloader.py # 抖音下载器（封装 douyin-downloader）
│   ├── ytdlp_downloader.py  # yt-dlp 下载器
│   ├── greenvideo_downloader.py  # GreenVideo 备选方案
│   ├── extractor.py         # 内容提取器（音频+转写+关键帧）
│   ├── analyzer.py          # 内容分析 V1（纯文本）
│   ├── analyzer_v2.py      # 内容分析 V2（多模态+缓存）
│   ├── executor.py          # 命令执行器（安全检查）
│   ├── resolver.py          # 错误修复器（自动排错）
│   ├── reporter.py         # 报告生成器（Markdown）
│   ├── knowledge_base.py   # 知识库管理
│   └── utils.py            # 工具函数（日志、路径、文件）
│
├── tools/                   # 第三方工具
│   └── douyin-downloader/  # 完整的抖音下载工具（独立项目）
│       ├── cli/             # 命令行界面
│       ├── core/            # 下载核心逻辑
│       ├── auth/            # Cookie 管理
│       ├── config/          # 配置加载
│       ├── control/         # 队列/限流/重试
│       ├── storage/         # 数据库/文件管理
│       ├── server/          # Web 服务
│       ├── utils/           # 工具函数
│       └── tests/          # 单元测试（60+ 个）
│
├── api/                     # Web API（FastAPI）
│   └── main.py
├── web/                    # Web UI
│   └── index.html
├── tests/                  # 项目级单元测试
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_downloader.py
│   ├── test_extractor.py   # 覆盖率 94% ✅
│   ├── test_analyzer.py
│   ├── test_executor.py
│   ├── test_reporter.py
│   ├── test_resolver.py    # 覆盖率 100% ✅
│   ├── test_utils.py       # 覆盖率 100% ✅
│   └── perf_test.py       # 性能对比测试
│
├── config/                  # 配置文件
│   ├── settings.yaml        # 主配置（已被 gitignore）
│   ├── settings.example.yaml
│   └── douyin_cookies.txt # 抖音 Cookie（已被 gitignore）
│
├── outputs/                # 输出目录
│   ├── cache/              # 分析结果缓存
│   └── *_report.md        # 生成的操作报告
│
├── .env                    # 环境变量（已被 gitignore）
├── pyproject.toml         # 项目配置（pytest/black/isort/flake8）
├── requirements.txt        # Python 依赖
├── README.md              # 项目说明文档
└── .gitignore            # Git 忽略规则
```

---

## 三、核心模块详解

### 3.1 CLI 模块（`cli.py`）

**职责：** 命令行入口，解析参数，协调各模块完成完整流程。

**支持的子命令：**
```
video-to-action process <url>   # 处理视频（默认命令）
video-to-action search <query>   # 搜索知识库
video-to-action export-handbook    # 导出操作手册
video-to-action kb-stats         # 知识库统计
```

**自动化级别（`--level` 参数）：**
| 级别 | 说明 | 适用场景 |
|------|------|----------|
| `extract` | 仅下载+转写+关键帧，不调用 LLM | 快速提取，无需 API Key |
| `observe` | 分析内容但不执行命令 | 预览分析结果 |
| `confirm` | 每步执行前询问用户确认 | 测试阶段（推荐） |
| `auto` | 全自动执行 | 稳定后使用 |

**覆盖率：** 64%

---

### 3.2 配置模块（`config.py`）

**职责：** 加载 YAML 配置文件，支持 `${ENV_VAR}` 环境变量展开，自动加载 `.env` 文件。

**关键功能：**
```python
load_config(path)  # 加载配置文件
# 支持的环境变量展开：
# api_key: ${AGNES_API_KEY}  → 从环境变量读取
# 自动加载 config/.env 文件
```

**覆盖率：** 98% ✅

---

### 3.3 下载模块

#### `downloader.py` — 兼容层
重新导出各下载器类，保持向后兼容。新代码建议直接导入对应模块。

#### `douyin_downloader.py` — 抖音专用
封装 `tools/douyin-downloader/` 工具，支持：
- Netscape 格式 Cookie 文件
- 浏览器 Cookie 导入
- 断点续传（已实现的 `--continue` 选项）

#### `ytdlp_downloader.py` — 通用下载器
基于 yt-dlp，支持抖音/B站/YouTube 等多个平台。

#### `greenvideo_downloader.py` — 备选方案
通过 GreenVideo.cc 在线服务下载，无需本地 Cookie。

---

### 3.4 内容提取模块（`extractor.py`）

**职责：** 从视频中提取可分析的内容。

**处理流程：**
```
视频文件 → ffmpeg 提取音频 → faster-whisper 转写 → 返回文本片段
                     ↓
             ffmpeg 截取关键帧 → 返回帧图片路径列表
```

**关键优化（已完成）：**
- ✅ **Whisper 模型单例模式** — 避免重复加载模型（节省 5-10 秒）
- ✅ **GPU 自动检测** — CUDA 可用时自动加速（5-10 倍）
- ✅ **compute_type 配置** — 支持 int8/float16/float32

**覆盖率：** 94% ✅

---

### 3.5 内容分析模块

#### `analyzer.py` — V1 版本
纯文本分析，构建提示词发送给 LLM，解析 JSON 格式的行动计划。

#### `analyzer_v2.py` — V2 版本（推荐）
支持多模态分析（文本 + 关键帧图片），功能更完善。

**关键优化（已完成）：**
- ✅ **分析结果缓存** — 对相同视频避免重复调用 LLM API
- ✅ **Few-shot 示例** — 提高 JSON 解析成功率
- ✅ **截断保护** — 转写文本过长时自动截断（避免 500 错误）

**覆盖率：** 54%（有待提升）

---

### 3.6 命令执行模块（`executor.py`）

**职责：** 执行 LLM 生成的行动计划中的命令，内置安全检查。

**安全机制：**
1. **黑名单拦截** — 禁止执行危险命令（`rm -rf /`、`format c:` 等）
2. **白名单确认** — 需确认命令（`pip install`、`npm install` 等）
3. **自动化级别控制** — 根据 `settings.yaml` 中的 `automation_level` 决定行为

**覆盖率：** 98% ✅

---

### 3.7 错误修复模块（`resolver.py`）

**职责：** 当命令执行失败时，分析错误信息，生成修复方案。

**支持的修复场景：**
- `command not found` → 建议安装对应包
- `npm not found` → 建议安装 Node.js
- `git not found` → 建议安装 Git
- `ffmpeg not found` → 建议安装 ffmpeg
- `yt-dlp not found` → 建议安装 yt-dlp

**覆盖率：** 100% ✅

---

### 3.8 报告生成模块（`reporter.py`）

**职责：** 将分析结果格式化为 Markdown 报告，包含：
- 视频主题和摘要
- 工具列表（名称/用途/安装命令/配置步骤）
- 注意事项和替代工具

**覆盖率：** 100% ✅

---

### 3.9 工具函数模块（`utils.py`）

**职责：** 提供通用的工具函数。

**主要函数：**
- `setup_logging()` — 配置日志系统
- `get_logger(name)` — 获取模块级 logger
- `ensure_dir(path)` — 创建目录（自动创建父目录）
- `safe_filename(name)` — 生成安全的文件名
- `format_duration(seconds)` — 格式化时长

**覆盖率：** 100% ✅

---

## 四、数据流图

```
用户输入视频链接
       │
       ▼
┌─────────────────┐
│  CLI 模块       │  ← parse_arguments()
│  (cli.py)      │  ← 读取 automation_level
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  下载模块       │  ← DouyinDownloader / YtDlpDownloader
│  (downloader)   │  ← 支持断点续传 + 进度条
└────────┬────────┘
         │ 输出：video.mp4
         ▼
┌─────────────────┐
│  提取模块       │  ← 提取音频 (ffmpeg)
│  (extractor)    │  ← 转写文本 (faster-whisper)
         │  ← 截取关键帧 (ffmpeg)
└────────┬────────┘
         │ 输出：audio.wav + segments.json + frames/*.jpg
         ▼
┌─────────────────┐
│  分析模块       │  ← 构建提示词（文本 + 帧）
│  (analyzer_v2)  │  ← 调用 LLM API
         │  ← 缓存检查结果（如启用）
└────────┬────────┘
         │ 输出：analysis.json（结构化行动计划）
         ▼
┌─────────────────┐
│  执行模块       │  ← 安全检查（黑名单/白名单）
│  (executor)     │  ← 按 automation_level 执行
└────────┬────────┘
         │ 如失败
         │───────┐
         │       ▼
         │  ┌─────────────────┐
         │  │  修复模块       │
         │  │  (resolver)     │
         │  └─────────────────┘
         ▼
┌─────────────────┐
│  报告模块       │  ← 生成 Markdown 报告
│  (reporter)     │  ← 保存结果到 outputs/
└─────────────────┘
```

---

## 五、配置文件详解（`settings.yaml`）

```yaml
# 自动化级别
automation_level: confirm  # observe / confirm / auto

# 输出目录
output_dir: outputs

# 最大重试次数
max_retries: 3

# 下载配置
download:
  primary: douyin-downloader  # 主方案
  fallback: yt-dlp             # 备选方案
  format: mp4
  quality: best

# 抖音下载器配置
douyin_downloader:
  project_path: ""   # 留空使用 tools/douyin-downloader
  thread: 3
  retry_times: 3
  proxy: ""
  cookies:  # 直接从 YAML 配置（也可从 cookies.txt 读取）

# 平台配置
platforms:
  douyin:
    name: 抖音
    greenvideo_url: https://greenvideo.cc/douyin
  bilibili:
    name: B站
  youtube:
    name: YouTube

# 语音转写配置
transcription:
  model: base        # tiny / base / small / medium / large
  language: zh       # zh / en / auto
  device: auto       # auto / cpu / cuda（自动检测 GPU）
  compute_type: int8 # int8 / float16 / float32

# 缓存配置
cache:
  enabled: false     # 是否启用分析结果缓存
  ttl: 604800      # 过期时间（秒）= 7 天
  file: outputs/cache/analysis_cache.json

# LLM 配置
llm:
  provider: openai
  api_key: ${AGNES_API_KEY}  # 从环境变量读取
  base_url: https://apihub.agnes-ai.com/v1
  model: agnes-2.0-flash
  max_tokens: 2048
  temperature: 0.3
  timeout: 120
```

---

## 六、测试覆盖情况

| 模块 | 覆盖率 | 状态 |
|------|--------|------|
| `utils.py` | 100% | ✅ 优秀 |
| `resolver.py` | 100% | ✅ 优秀 |
| `reporter.py` | 100% | ✅ 优秀 |
| `config.py` | 98% | ✅ 优秀 |
| `executor.py` | 98% | ✅ 优秀 |
| `extractor.py` | 94% | ✅ 优秀 |
| `cli.py` | 64% | ⚠️ 良好 |
| `analyzer_v2.py` | 54% | ⚠️ 需提升 |
| `analyzer.py` | — | ⚠️ 已被 V2 取代 |
| **整体** | **61.49%** | ⚠️ 目标 70% |

**测试执行命令：**
```bash
# 运行所有测试
.venv/Scripts/python.exe -m pytest tests/ -v

# 运行指定模块测试
.venv/Scripts/python.exe -m pytest tests/test_extractor.py -v

# 查看覆盖率报告
.venv/Scripts/python.exe -m pytest tests/ --cov=video_to_action --cov-report=html
# 然后打开 htmlcov/index.html
```

---

## 七、已完成的优化（本迭代）

### ✅ 基础设施
1. **虚拟环境配置** — 创建 `.venv`，隔离项目依赖
2. **依赖安装** — 安装所有 requirements.txt 和 playwright 浏览器
3. **环境变量支持** — 修改 `config.py` 支持 `${VAR_NAME}` 语法
4. **`.env` 文件** — API Key 安全存储，已被 gitignore

### ✅ 功能增强
1. **下载进度条** — 使用 `rich` 库显示实时进度（已集成到 `douyin-downloader`）
2. **断点续传** — 检查已存在文件 + `--continue` 选项
3. **错误处理完善** — 统一日志格式，友好错误提示

### ✅ 性能优化
1. **Whisper 模型单例模式** — 避免重复加载（节省 5-10 秒）
2. **GPU 自动检测** — CUDA 可用时自动切换（加速 5-10 倍）
3. **分析结果缓存** — 避免重复调用 LLM API（节省成本）

### ✅ 测试提升
1. **覆盖率从 52.81% → 61.49%** — 增加 8.68%
2. **新增测试用例** — `test_cli.py` / `test_extractor.py` / `test_resolver.py` 等
3. **性能测试** — `perf_test.py` 对比单例模式效果

---

## 八、待完成的功能（优化路线图）

### 🔜 短期（1-2周）
1. **批量处理模块** — 支持 CSV/Excel 导入视频链接
2. **多平台支持** — 添加 B站、YouTube 完整支持
3. **测试覆盖率 70%+** — 重点提升 `analyzer_v2.py` 和 `cli.py`

### 🔜 中期（1-2月）
1. **Web UI 界面** — 基于 Gradio/Streamlit 的原型
2. **协作功能** — 团队知识库共享
3. **本地 LLM 支持** — 集成 Ollama，降低 API 成本

### 🔜 长期（3-6月）
1. **SaaS 服务部署** — FastAPI + Docker
2. **支付系统集成** — 微信支付/支付宝
3. **商业化运营** — 免费版/个人版/专业版/企业版

---

## 九、快速上手指南

### 安装
```bash
cd G:/trae/video-to-action
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt -i https://mirrors.huaweicloud.com/repository/pypi/simple/
playwright install chromium
```

### 配置
```bash
# 1. 复制配置模板
cp config/settings.example.yaml config/settings.yaml

# 2. 创建 .env 文件
echo AGNES_API_KEY=your_key_here > .env

# 3. 配置抖音 Cookie（如需下载抖音视频）
# 浏览器登录 douyin.com，导出 Cookie 为 Netscape 格式
# 保存到 config/douyin_cookies.txt
```

### 使用
```bash
# 仅提取（无需 API Key）
.venv/Scripts/python.exe -m video_to_action.cli "视频链接" --level extract

# 分析并确认执行
.venv/Scripts/python.exe -m video_to_action.cli "视频链接" --level confirm

# 全自动执行（需谨慎）
.venv/Scripts/python.exe -m video_to_action.cli "视频链接" --level auto
```

---

## 十、常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|------------|
| `command not found: python` | Python 未添加到 PATH | 使用完整路径或重新安装 Python |
| `No module named 'video_to_action'` | 未在项目根目录运行 | `cd G:/trae/video-to-action` |
| `WhisperModel not found` | faster-whisper 未安装 | `pip install faster-whisper` |
| `Playwright not found` | playwright 未安装或浏览器未安装 | `pip install playwright && playwright install chromium` |
| LLM API 500 错误 | 转写文本过长 | 已修复：自动截断（见 `analyzer_v2.py`） |
| Cookie 无效 | Cookie 过期或未正确配置 | 重新导出 Cookie，确认 `config/douyin_cookies.txt` 格式正确 |

---

## 十一、项目维护建议

### 定期检查项
1. **Cookie 有效期** — 抖音 Cookie 约 7-30 天过期，需定期更新
2. **依赖更新** — 每月检查 `yt-dlp` / `faster-whisper` 是否有新版本
3. **测试覆盖率** — 每次添加功能后运行 `pytest --cov`，确保覆盖率不下降
4. **API 成本** — 启用缓存后监控 LLM API 调用次数和费用

### Git 管理
```bash
# 已被 gitignore 的文件（不要提交到远程仓库）
.env                      # 环境变量（含 API Key）
config/settings.yaml      # 本地配置
config/douyin_cookies.txt # 抖音 Cookie
.venv/                   # 虚拟环境
outputs/                 # 输出目录（可选）

# 安全提交
git add .
git commit -m "feat: 添加 XXX 功能"
git push origin main
```

---

*本文档由 程 自动生成，最后更新：2026-06-25 21:00*
