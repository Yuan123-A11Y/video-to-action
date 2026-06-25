# Video-to-Action 项目功能模块完整分析

> 版本：v0.1.0 | 分析时间：2026-06-25 | 分析者：程

---

## 一、项目概述

**项目名称：** Video-to-Action（视频到行动助手）

**核心理念：** 将抖音、B站、YouTube 等平台的教程视频自动转化为可执行的工具和配置方案。

**完整数据流：**
```
视频链接 → 下载视频 → 提取音频 → 语音转写 → LLM分析内容
                                              ↓
                                   生成结构化行动计划 → 自动执行安装/配置 → 生成报告 → 存入知识库
```

---

## 二、功能模块分类详解

---

### 🔧 2.1 视频下载模块

#### `downloader.py` — 下载调度层
**用途：** 组合多个下载方案，支持断点续传和平台自动识别。

**实现方式：**
- `download_video(url, config, output_dir)` — 主入口函数
- 平台识别：`detect_video_platform(url)`（在 `ytdlp_downloader.py` 中）
- 断点续传：`_check_existing_download()` 精确匹配视频 ID，避免重复下载
- 降级策略：主方案失败 → 自动切换备选方案

**支持的平台：**
| 平台 | 主方案 | 备选方案 |
|------|--------|----------|
| 抖音 | douyin-downloader | yt-dlp → GreenVideo |
| B站 | yt-dlp | — |
| YouTube | yt-dlp | — |
| 其他 | yt-dlp | — |

---

#### `douyin_downloader.py` — 抖音专用下载器
**用途：** 基于 `tools/douyin-downloader/` 工具实现抖音视频无水印下载。

**实现方式：**
- 封装 `douyin-downloader` 的异步 API（`asyncio`）
- Cookie 管理：支持 Netscape 格式文件 + 浏览器导入
- 短链解析：自动将 `v.douyin.com` 解析为真实 URL
- 限流保护：`RateLimiter` 控制每秒请求数
- 重试机制：`RetryHandler` 自动重试失败请求

**关键特性：**
- ✅ 支持抖音各种页面格式（用户页、视频页、评论区视频）
- ✅ 视频 ID 精确提取（`modal_id` / `video/` / 数字段三种方式）
- ✅ 临时文件管理（`_douyin_temp/` 目录，下载后复制到输出目录）

---

#### `ytdlp_downloader.py` — 通用下载器
**用途：** 基于 `yt-dlp` 的通用视频下载，支持 1000+ 平台。

**实现方式：**
- 封装 `yt-dlp` Python API
- 格式选择：优先 1080p 以下 + 最佳音频
- Cookie 支持：`--cookies-from-browser chrome`
- 元数据保留：下载缩略图、字幕、元数据 JSON

---

#### `greenvideo_downloader.py` — 备选下载方案
**用途：** 通过 GreenVideo.cc 在线服务下载，无需本地 Cookie。

**实现方式：**
- HTTP API 调用 GreenVideo 服务
- 适用场景：Cookie 失效或无法安装 `yt-dlp` 时

---

### 🎙 2.2 内容提取模块（`extractor.py`）

**用途：** 从视频中提取可分析的内容（音频、转写文本、关键帧）。

**实现方式：**

#### 音频提取
```python
extract_audio(video_path) -> Path
```
- 使用 `ffmpeg` 提取单声道 16kHz PCM 音频（Whisper 要求格式）
- 输出：`<video>.wav`

#### 语音转写
```python
transcribe(audio_path) -> list[dict]
```
- 使用 `faster-whisper`（`WhisperModel`）进行本地语音识别
- **优化（已完成的）：**
  - ✅ **模型单例模式** — 类级别缓存，避免重复加载（节省 5-10 秒）
  - ✅ **GPU 自动检测** — CUDA 可用时自动切换（加速 5-10 倍）
  - ✅ **compute_type 配置** — 支持 `int8`（快速）/ `float16`（平衡）/ `float32`（精确）
  - ✅ **HuggingFace 镜像自动切换** — 国内网络环境自动使用 `hf-mirror.com`

#### 关键帧截取
```python
extract_frames(video_path, count=5) -> list[Path]
```
- 使用 `ffmpeg` 按等间隔时间截取帧
- 默认 5 张，保存到 `frames/` 目录

#### 完整处理流程
```python
process(video_path) -> dict  # 整合上述三个步骤
```
- 每个步骤独立保护（某一步失败不影响其他步骤）
- 返回：`{"audio_path", "segments", "frames", "text"}`

---

### � 2.3 内容分析模块

#### `analyzer.py` — V1 版本（纯文本）
**用途：** 构建提示词发送给 LLM，解析 JSON 格式的行动计划。

**实现方式：**
- 提示词工程：要求 LLM 返回结构化 JSON
- 包含字段：`theme`、`summary`、`tools`、`needs_credential`、`is_paid`、`alternative_tools`
- JSON 解析：处理 LLM 返回的各种格式问题（markdown 代码块、trailing comma 等）

---

#### `analyzer_v2.py` — V2 版本（推荐）
**用途：** 支持多模态分析（文本 + 关键帧图片），功能更完善。

**实现方式：**

##### 多模态支持
- 如果启用 `vision_enabled` 且有关键帧，将图片编码为 base64 嵌入提示词
- 最多使用 3 张关键帧（避免超出 token 限制）

##### 多种 LLM 提供商支持
| 提供商 | 配置值 | API 格式 | 适用场景 |
|----------|----------|----------|----------|
| OpenAI | `provider: openai` | OpenAI 兼容 | 官方 API / Agnes AI / 其他兼容服务 |
| Ollama | `provider: ollama` | Ollama 本地 API | 本地部署，无 API 成本 |
| LM Studio | `provider: openai` + 自定义 `base_url` | OpenAI 兼容 | 本地部署（GUI 界面） |

##### 分析结果缓存机制
- ✅ **已实现的：** 类级别缓存（`_cache` 字典）
- ✅ **缓存键：** 基于文本内容的 SHA-256 哈希
- ✅ **TTL 过期：** 默认 7 天（可配置）
- ✅ **持久化：** 保存到 `outputs/cache/analysis_cache.json`
- ⚠️ **默认禁用：** 需显式启用 `cache.enabled: true`（避免返回过期结果）

##### 提示词优化
- ✅ **文本截断保护** — 超过 8000 字符自动截断（避免 LLM API 500 错误）
- ✅ **Few-shot 示例** — 在提示词中嵌入示例输出，提高 JSON 解析成功率
- ✅ **JSON 格式增强解析** — 处理 markdown 代码块、trailing comma、注释等边界情况

##### 回退机制
- LLM 调用失败时返回占位结果（`_build_mock_response()`）
- 包含 `_llm_error` 字段，便于排查问题

---

### 🔨 2.4 命令执行模块（`executor.py`）

**用途：** 执行 LLM 生成的行动计划中的命令，内置多层安全检查。

**实现方式：**

#### 黑名单拦截
```python
FORBIDDEN_KEYWORDS = ["rm -rf /", "mkfs", "dd if=", ...]
```
- 匹配到危险关键词直接拦截，不执行

#### 白名单确认
```python
REQUIRE_CONFIRM = ["run_remote_script", "install_system_software", "modify_system_env"]
```
- `run_remote_script` — 匹配 `curl ... | sh` 等模式
- `install_system_software` — 匹配 `apt install` / `brew install` 等
- `modify_system_env` — 匹配 `export PATH` / `setx` 等
- 需要确认时才执行（根据 `automation_level` 配置）

#### 交互式工具检测
```python
INTERACTIVE_TOOLS = {"claude", "cursor", "codex", "windsurf", ...}
```
- 检测到交互式工具（无法在自动化流程中运行）时跳过，给出提示

#### 安装命令格式校验
```python
INSTALL_PREFIXES = {"pip install", "npm install", "brew install", ...}
```
- 警告但不阻止格式不正确的命令（LLM 可能生成不完美命令）

#### 超时保护
- 默认 300 秒超时（可在 `settings.yaml` 中配置 `safety.command_timeout`）
- 超时后自动终止命令，返回超时错误

---

### 🔧 2.5 错误修复模块（`resolver.py`）

**用途：** 当命令执行失败时，分析错误信息，给出修复建议或自动修复。

**实现方式：**

##### 支持的错误诊断场景
| 错误信息 | 修复建议 |
|----------|----------|
| `command not found: pip` | 检查 Python 和 pip 是否已安装并添加到 PATH |
| `timed out` / `timeout` | 为 `pip` 命令添加华为云镜像参数 |
| `Permission denied` | 建议使用 `sudo` 执行 |
| `command not found: npm` | 请安装 Node.js 和 npm |
| `command not found: git` | 请安装 Git |
| `ffmpeg: not found` | 请安装 ffmpeg 并添加到 PATH |
| `yt-dlp: not found` | 请安装 yt-dlp（带镜像参数） |

##### 自动修复执行
- `_extract_executable_command()` — 从修复建议中提取可执行的命令
- 例如：`"尝试使用 sudo 执行：sudo xxx"` → 提取 `sudo xxx`
- 如果提取成功，`Executor` 会自动执行修复命令

---

### 📋 2.6 报告生成模块（`reporter.py`）

**用途：** 将分析结果和执

行结果格式化为 Markdown 报告。

**实现方式：**

##### 报告内容
```markdown
# 视频到行动助手 - 执行报告

## 视频信息
- 视频链接、平台、下载方式、本地路径

## 视频内容摘要
- 主题、摘要

## 涉及工具
- 工具名称、用途、链接、注意事项

## 执行过程
- 每步的执行状态、命令、输出、错误

## 执行结果
- 总步骤数、成功数、失败数、最终状态

## 后续建议
- 检查输出、手动修复失败步骤等
```

##### 输出位置
- 默认：`outputs/reports/report_YYYYMMDD_HHMMSS.md`
- 包含时间戳，避免覆盖

---

### 💾 2.7 知识库模块（`knowledge_base.py`）

**用途：** 基于 SQLite 存储和检索历史分析结果，避免重复分析和便于查阅。

**实现方式：**

##### 数据库架构
```sql
-- 视频表
CREATE TABLE videos (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE,           -- 视频 URL（唯一）
    platform TEXT,              -- 平台名称
    title TEXT,                -- 视频标题
    theme TEXT,                -- 视频主题
    summary TEXT,               -- 视频摘要
    transcription_text TEXT,    -- 转写文本
    analysis_result TEXT,       -- 分析结果（JSON）
    created_at TIMESTAMP
);

-- 工具表
CREATE TABLE tools (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,          -- 工具名称（唯一）
    purpose TEXT,               -- 工具用途
    install_commands TEXT,       -- 安装命令（JSON 数组）
    config_steps TEXT,          -- 配置步骤（JSON 数组）
    warnings TEXT,             -- 注意事项（JSON 数组）
    alternatives TEXT,          -- 替代工具（JSON 数组）
    is_paid BOOLEAN,          -- 是否付费
    needs_credential BOOLEAN,  -- 是否需要凭证
    created_at TIMESTAMP
);

-- 关联表（多对多）
CREATE TABLE video_tools (
    video_id INTEGER,
    tool_id INTEGER,
    FOREIGN KEY (video_id) REFERENCES videos(id),
    FOREIGN KEY (tool_id) REFERENCES tools(id)
);
```

##### 支持的操作
| 操作 | 方法 | 说明 |
|------|------|----------|
| 添加视频分析 | `add_video_analysis()` | 插入视频记录 + 关联工具 |
| 搜索视频 | `search_videos(query)` | 基于 LIKE 模糊匹配主题/摘要 |
| 搜索工具 | `search_tools(query)` | 基于 LIKE 模糊匹配名称/用途 |
| 获取视频详情 | `get_video_by_url(url)` | 根据 URL 精确匹配 |
| 获取工具详情 | `get_tool_by_name(name)` | 根据名称精确匹配 |
| 获取视频关联工具 | `get_video_tools(video_id)` | 多对多关联查询 |
| 导出操作手册 | `export_handbook()` | 生成 Markdown 格式手册 |
| 获取统计信息 | `get_statistics()` | 视频数、工具数、平台分布 |

##### 操作手册导出格式
```markdown
# 视频知识库操作手册

## <工具名称>

**用途**：<工具用途>

**安装命令**：
- `pip install xxx`
- ...

**配置步骤**：
- 步骤 1
- ...

**注意事项**：
- ⚠️ 注意 1
- ...

**替代工具**：alt1, alt2

**相关视频**：
- [抖音] 视频主题 1
- ...
```

---

### ⚙️ 2.8 配置管理模块（`config.py`）

**用途：** 加载 YAML 配置文件，支持环境变量展开。

**实现方式：**

##### 环境变量展开
```yaml
# 在 settings.yaml 中
api_key: ${AGNES_API_KEY}  # 从环境变量读取
```
- `_expand_env_vars()` 函数递归展开 `${VAR_NAME}` 语法
- 如果环境变量未设置，保留原始字符串（不会报错）

##### `.env` 文件自动加载
- 项目根目录或 `config/` 目录下的 `.env` 文件会自动加载
- 使用 `python-dotenv` 库
- `.env` 已被 `.gitignore` 忽略，不会提交到远程仓库

##### 配置优先级
```
命令行参数 > 配置文件 > 环境变量 > 默认值
```

---

### 🌐 2.9 Web API 模块（`api/main.py`）

**用途：** 提供 RESTful API 接口，支持 Web UI 或第三方集成。

**实现方式：** 基于 FastAPI 框架

##### 支持的端点
| 方法 | 路径 | 用途 |
|------|------|----------|
| GET | `/` | API 根路径（返回端点列表） |
| POST | `/api/process` | 提交视频处理任务（异步） |
| GET | `/api/tasks/{task_id}` | 获取任务状态 |
| GET | `/api/search` | 搜索知识库 |
| GET | `/api/stats` | 获取统计信息 |
| GET | `/api/videos` | 获取视频列表（分页） |
| GET | `/api/videos/{id}` | 获取视频详情 |
| GET | `/api/tools` | 获取工具列表（分页） |
| GET | `/api/tools/{id}` | 获取工具详情 |

##### 异步任务处理
- 使用 `BackgroundTasks` 实现非阻塞视频处理
- 任务状态存储在内存的 `tasks` 字典中
- 状态类型：`pending` → `processing` → `completed` / `failed`

##### CORS 配置
- 默认允许所有来源（`allow_origins=["*"]`）
- 生产环境建议限制为前端域名

---

### 🎨 2.10 Web UI 模块（`web/index.html`）

**用途：** 基于 HTML + Tailwind CSS + Vanilla JavaScript 的单页应用（SPA）。

**实现方式：** 单文件前端（无构建步骤）

##### 页面结构
| 页面 | 导航 ID | 功能 |
|------|----------|------|
| 处理视频 | `page-process` | 输入视频链接、选择自动化级别、提交处理任务 |
| 视频库 | `page-videos` | 查看已处理视频列表、筛选、查看详情 |
| 工具库 | `page-tools` | 查看提取的工具列表、筛选、查看详情 |
| 搜索 | `page-search` | 在知识库中搜索视频或工具 |
| 统计概览 | `page-stats` | 显示视频数、工具数、平台分布图表 |

##### 技术特性
- ✅ **响应式设计** — 桌面端侧边栏 + 移动端底部导航栏
- ✅ **骨架屏加载** — 数据加载时显示 shimmer 动画
- ✅ **Toast 通知** — 成功/错误/警告/信息四种类型
- ✅ **API 健康检查** — 每 10 秒自动检测后端连接状态
- ✅ **模态框详情** — 点击视频/工具卡片弹出详情浮层
- ✅ **分页支持** — 视频库和工具库支持分页（后端已支持）

##### 自动化级别选择器
```
Extract  →  仅提取文本和关键帧，不调用 LLM
Observe  →  分析内容但不执行命令
Confirm  →  每步执行前询问用户确认
Auto     →  全自动执行（默认）
```

---

### 🛠️ 2.11 工具函数模块（`utils.py`）

**用途：** 提供通用的工具函数，被其他模块广泛引用。

**主要函数：**

| 函数 | 用途 |
|------|------|
| `setup_logging(level, log_file)` | 配置日志系统（同时输出到控制台和文件） |
| `get_logger(name)` | 获取模块级 logger（自动添加时间戳） |
| `ensure_dir(path)` | 创建目录（自动创建父目录） |
| `safe_filename(name)` | 生成安全的文件名（移除非法字符） |
| `format_duration(seconds)` | 格式化时长为 `HH:MM:SS` |
| `is_dangerous_command(command, forbidden)` | 检查命令是否包含危险关键词 |

---

## 三、CLI 命令详解

**入口：** `python -m video_to_action.cli <子命令>`

### 3.1 `process` 命令（默认）
```bash
python -m video_to_action.cli process <url> [选项]
```

**选项：**
| 选项 | 说明 | 默认值 |
|------|------|----------|
| `--level` | 自动化级别（extract/observe/confirm/auto） | `auto` |
| `--config` | 配置文件路径 | `config/settings.yaml` |
| `--output` | 输出目录 | `outputs/` |
| `--save-to-kb` | 保存分析结果到知识库 | 禁用 |
| `--verbose` | 输出详细调试信息 | 禁用 |

**执行流程：**
```
1. 下载视频（支持本地文件路径或远程 URL）
2. 提取音频 + 转写文本 + 截取关键帧
3. 调用 LLM 分析内容（extract 模式跳过此步）
4. 执行行动计划（observe 模式跳过此步）
5. 自动修复失败步骤
6. 生成 Markdown 报告
7. 保存到知识库（如启用）
```

---

### 3.2 `search` 命令
```bash
python -m video_to_action.cli search <query> [选项]
```

**选项：**
| 选项 | 说明 | 默认值 |
|------|------|----------|
| `--type` | 搜索类型（video/tool） | `video` |
| `--limit` | 结果数量限制 | 10 |

**用途：** 在知识库中搜索已处理的视频或提取的工具。

---

### 3.3 `export-handbook` 命令
```bash
python -m video_to_action.cli export-handbook [选项]
```

**选项：**
| 选项 | 说明 | 默认值 |
|------|------|----------|
| `--output` | 输出文件路径 | `outputs/handbook.md` |

**用途：** 导出所有工具的操作手册（Markdown 格式），便于离线查阅。

---

### 3.4 `kb-stats` 命令
```bash
python -m video_to_action.cli kb-stats
```

**用途：** 显示知识库统计信息（视频数、工具数、平台分布）。

---

## 四、配置文件详解（`settings.yaml`）

```yaml
# ============ 核心配置 ============

# 自动化级别：observe(仅分析) / confirm(每步确认) / auto(自动执行)
automation_level: confirm

# 输出目录
output_dir: outputs

# 最大重试次数
max_retries: 3


# ============ 下载配置 ============

download:
  primary: douyin-downloader  # 主方案
  fallback: yt-dlp             # 备选方案


# ============ 抖音下载器配置 ============

douyin_downloader:
  project_path: ""   # 留空使用 tools/douyin-downloader
  thread: 3         # 下载线程数
  retry_times: 3     # 重试次数
  proxy: ""          # 代理地址（如 "http://127.0.0.1:7890"）
  cookies: {}         # 直接从 YAML 配置（也可从 cookies.txt 读取）


# ============ 平台配置 ============

platforms:
  douyin:
    name: 抖音
    greenvideo_url: https://greenvideo.cc/douyin
  bilibili:
    name: B站
  youtube:
    name: YouTube


# ============ 语音转写配置 ============

transcription:
  model: base            # tiny / base / small / medium / large
  language: zh           # zh / en / auto
  device: auto           # auto / cpu / cuda（自动检测 GPU）
  compute_type: int8     # int8（快速）/ float16（平衡）/ float32（精确）


# ============ 缓存配置 ============

cache:
  enabled: false         # 是否启用分析结果缓存
  ttl: 604800          # 过期时间（秒）= 7 天
  file: outputs/cache/analysis_cache.json


# ============ LLM 配置 ============

llm:
  provider: openai       # openai / ollama / lm_studio
  api_key: ${AGNES_API_KEY}  # 从环境变量读取（推荐）
  base_url: https://apihub.agnes-ai.com/v1
  model: agnes-2.0-flash
  max_tokens: 2048
  temperature: 0.3
  timeout: 120
  vision_enabled: false   # 是否启用多模态分析（需要视觉模型）


# ============ 安全配置 ============

safety:
  forbidden_keywords:
    - "rm -rf /"
    - "mkfs"
    - "dd if="
    - ...
  require_confirm:
    - "run_remote_script"
    - "install_system_software"
    - "modify_system_env"
  command_timeout: 300   # 命令执行超时（秒）
```

---

## 五、辅助工具和集成点

### 5.1 第三方工具集成

#### `tools/douyin-downloader/`
**用途：** 完整的抖音视频下载工具（独立项目，被本项目引用）。

**包含模块：**
| 模块 | 路径 | 用途 |
|------|----------|------|
| Cookie 管理 | `auth/` | 加载和验证 Cookie |
| 配置加载 | `config/` | 解析下载器配置 |
| 核心下载 | `core/` | API 客户端、下载器工厂、URL 解析器 |
| 限流/重试 | `control/` | `RateLimiter`、`RetryHandler` |
| 文件管理 | `storage/` | 文件保存和目录管理 |
| Web 服务 | `server/` | 可选的 Web 界面 |
| 单元测试 | `tests/` | 60+ 个测试用例 |

---

### 5.2 外部依赖

| 依赖 | 版本 | 用途 |
|------|--------|------|
| `yt-dlp` | >=2024.12.0 | 通用视频下载 |
| `faster-whisper` | >=1.0.0 | 本地语音转写 |
| `requests` | >=2.32.0 | HTTP 客户端 |
| `httpx` | >=0.27.0 | 现代 HTTP 客户端（LLM API 调用） |
| `beautifulsoup4` | >=4.12.0 | HTML 解析（备用） |
| `playwright` | >=1.45.0 | 浏览器自动化（GreenVideo 备选方案） |
| `markdown` | >=3.6 | Markdown 解析（备用） |
| `pyyaml` | >=6.0.1 | YAML 配置解析 |
| `rich` | >=13.7.0 | CLI 进度条和彩色输出 |
| `python-dotenv` | >=1.0.0 | `.env` 文件加载 |
| `typer[all]` | >=0.12.0 | CLI 框架（当前使用 `argparse`，可升级） |
| `fastapi` | （可选） | Web API 服务 |
| `uvicorn` | （可选） | ASGI 服务器 |

---

## 六、测试覆盖情况

### 6.1 单元测试文件列表

| 测试文件 | 测试数量 | 覆盖率 | 状态 |
|----------|----------|--------|------|
| `test_utils.py` | 10+ | 100% ✅ | 优秀 |
| `test_resolver.py` | 10+ | 100% ✅ | 优秀 |
| `test_reporter.py` | 5+ | 100% ✅ | 优秀 |
| `test_config.py` | 8+ | 98% ✅ | 优秀 |
| `test_executor.py` | 15+ | 98% ✅ | 优秀 |
| `test_extractor.py` | 12+ | 94% ✅ | 优秀 |
| `test_cli.py` | 10+ | 64% ⚠️ | 良好（需提升） |
| `test_analyzer.py` | 8+ | 54% ⚠️ | 良好（需提升） |

**整体覆盖率：** 61.49% ⚠️（目标：70%+）

---

### 6.2 性能测试

#### `tests/perf_test.py`
**用途：** 对比 Whisper 模型单例模式的效果。

**测试场景：**
- 第一次转写（需加载模型）：~5-10 秒
- 第二次转写（使用缓存）：~0.5 秒
- **加速比：** ~10-20 倍

---

## 七、部署和运维

### 7.1 部署方式

#### 方式 1：本地 CLI 使用
```bash
# 安装依赖
pip install -r requirements.txt

# 执行
python -m video_to_action.cli process "视频链接"
```

#### 方式 2：Web 服务部署
```bash
# 安装 Web 依赖
pip install fastapi uvicorn

# 启动服务
python api/main.py
# 或
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 访问 Web UI
open http://localhost:8000
```

#### 方式 3：Docker 部署（待实现）
```dockerfile
# TODO: 创建 Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 7.2 日志系统

**配置方式：**
```python
setup_logging(level=logging.DEBUG, log_file="outputs/video_to_action.log")
```

**日志输出：**
- 控制台：INFO 级别（简洁）
- 文件：DEBUG 级别（详细，便于排查问题）

**日志格式：**
```
2026-06-25 21:00:00 - video_to_action.cli - INFO - 视频到行动助手启动
2026-06-25 21:00:01 - video_to_action.downloader - DEBUG - 开始下载视频...
```

---

### 7.3 常见运维任务

| 任务 | 命令 | 说明 |
|------|----------|------|
| 更新依赖 | `pip install -U yt-dlp` | 定期更新 `yt-dlp`（支持新平台） |
| 更新 Cookie | 重新导出 `config/douyin_cookies.txt` | 抖音 Cookie 约 7-30 天过期 |
| 查看知识库 | `python -m video_to_action.cli kb-stats` | 显示统计信息 |
| 导出操作手册 | `python -m video_to_action.cli export-handbook` | 生成 Markdown 手册 |
| 清理缓存 | 删除 `outputs/cache/` 目录 | 释放磁盘空间 |
| 查看日志 | `tail -f outputs/video_to_action.log` | 实时监控 |

---

## 八、已实现的高级特性

### 8.1 性能优化特性

| 特性 | 实现位置 | 效果 |
|------|----------|------|
| Whisper 模型单例模式 | `extractor.py` | 避免重复加载，节省 5-10 秒 |
| GPU 自动检测 | `extractor.py` | CUDA 可用时加速 5-10 倍 |
| 分析结果缓存 | `analyzer_v2.py` | 避免重复调用 LLM API，节省成本 |
| HuggingFace 镜像自动切换 | `extractor.py` | 国内网络环境自动使用镜像 |
| 断点续传 | `downloader.py` | 避免重复下载大视频文件 |

---

### 8.2 安全特性

| 特性 | 实现位置 | 效果 |
|------|----------|------|
| 危险命令黑名单 | `executor.py` + `utils.py` | 拦截 `rm -rf /` 等危险操作 |
| 白名单确认机制 | `executor.py` | 执行敏感操作前要求确认 |
| 交互式工具检测 | `executor.py` | 跳过无法自动执行的交互式工具 |
| 命令执行超时 | `executor.py` | 防止命令挂起导致进程卡死 |
| API Key 环境变量管理 | `config.py` | 避免硬编码敏感信息 |

---

### 8.3 用户体验特性

| 特性 | 实现位置 | 效果 |
|------|----------|------|
| 下载进度条 | `tools/douyin-downloader/` | 实时显示下载进度 |
| 友好错误提示 | 全局 | 替换 Python 异常为可读的中文提示 |
| 自动化级别选择 | `cli.py` | 4 级自动化（extract/observe/confirm/auto） |
| 知识库搜索 | `knowledge_base.py` | 快速查找已处理视频和工具 |
| Web UI | `web/index.html` | 可视化界面，降低使用门槛 |
| Toast 通知 | `web/index.html` | 操作反馈实时显示 |

---

## 九、待实现的功能（优化路线图）

### 9.1 短期（1-2 周）

| 功能 | 优先级 | 说明 |
|------|----------|------|
| 批量处理 | ⭐⭐⭐⭐⭐ | 支持 CSV/Excel 导入视频链接，自动排队处理 |
| B站完整支持 | ⭐⭐⭐⭐☆ | 当前仅通过 yt-dlp 支持，需优化 Cookie 管理 |
| YouTube 完整支持 | ⭐⭐⭐⭐☆ | 当前仅通过 yt-dlp 支持，需优化字幕下载 |
| 测试覆盖率 70%+ | ⭐⭐⭐⭐☆ | 重点提升 `analyzer_v2.py` 和 `cli.py` |

---

### 9.2 中期（1-2 月）

| 功能 | 优先级 | 说明 |
|------|----------|------|
| Web UI 完善 | ⭐⭐⭐⭐☆ | 添加分页、排序、筛选、编辑功能 |
| 本地 LLM 支持优化 | ⭐⭐⭐⭐☆ | 完善 Ollama 集成，降低 API 成本 |
| 协作功能 | ⭐⭐⭐☆☆ | 团队知识库共享、评论标注、版本管理 |
| Docker 部署 | ⭐⭐⭐☆☆ | 创建 Dockerfile 和 Docker Compose 配置 |

---

### 9.3 长期（3-6 月）

| 功能 | 优先级 | 说明 |
|------|----------|------|
| SaaS 服务部署 | ⭐⭐⭐⭐☆ | FastAPI + Docker + Nginx 生产环境部署 |
| 支付系统集成 | ⭐⭐⭐☆☆ | 微信支付/支付宝（商业化） |
| 用户管理系统 | ⭐⭐⭐☆☆ | 注册/登录/配额控制（多租户） |
| 移动端 App | ⭐⭐☆☆☆ | React Native / Flutter 跨平台应用 |

---

## 十、项目文件清单

### 10.1 核心代码文件（按重要性排序）

```
video_to_action/
├── cli.py                   # ⭐⭐⭐⭐⭐ CLI 入口（235 行）
├── analyzer_v2.py           # ⭐⭐⭐⭐⭐ 内容分析 V2（356 行）
├── extractor.py             # ⭐⭐⭐⭐⭐ 内容提取（191 行）
├── executor.py              # ⭐⭐⭐⭐☆ 命令执行（205 行）
├── knowledge_base.py        # ⭐⭐⭐⭐☆ 知识库（321 行）
├── resolver.py              # ⭐⭐⭐☆☆ 错误修复（124 行）
├── reporter.py              # ⭐⭐⭐☆☆ 报告生成（110 行）
├── downloader.py            # ⭐⭐⭐☆☆ 下载调度（159 行）
├── douyin_downloader.py   # ⭐⭐⭐☆☆ 抖音下载器（284 行）
├── ytdlp_downloader.py    # ⭐⭐⭐☆☆ yt-dlp 下载器
├── greenvideo_downloader.py # ⭐⭐☆☆☆ GreenVideo 备选
├── config.py               # ⭐⭐⭐⭐⭐ 配置管理（98 行）
└── utils.py                # ⭐⭐⭐⭐⭐ 工具函数（~100 行）

api/
└── main.py                # ⭐⭐⭐⭐☆ Web API（266 行）

web/
└── index.html             # ⭐⭐⭐⭐☆ Web UI（1005 行）

tools/
└── douyin-downloader/    # ⭐⭐⭐⭐☆ 第三方工具（完整项目）
```

---

### 10.2 配置文件

```
config/
├── settings.yaml            # 主配置文件（已被 gitignore）
├── settings.example.yaml   # 配置模板（可安全提交）
└── douyin_cookies.txt   # 抖音 Cookie（Netscape 格式，已被 gitignore）

.env                        # 环境变量（API Key 等，已被 gitignore）
```

---

### 10.3 测试文件

```
tests/
├── conftest.py               # pytest 固定装置
├── test_cli.py             # CLI 模块测试（64% 覆盖率）
├── test_config.py          # 配置模块测试（98% 覆盖率）
├── test_downloader.py      # 下载模块测试
├── test_extractor.py      # 提取模块测试（94% 覆盖率）
├── test_analyzer.py       # 分析模块测试（54% 覆盖率）
├── test_executor.py       # 执行模块测试（98% 覆盖率）
├── test_reporter.py       # 报告模块测试（100% 覆盖率）
├── test_resolver.py       # 修复模块测试（100% 覆盖率）
├── test_utils.py          # 工具函数测试（100% 覆盖率）
└── perf_test.py          # 性能对比测试
```

---

## 十一、总结

### 11.1 项目优势

1. **模块化设计良好** — 各功能模块职责清晰，便于单独测试和替换
2. **配置与代码分离** — YAML 配置文件 + 环境变量，便于部署和运维
3. **安全机制完善** — 多层安全检查（黑名单、白名单、超时、交互式工具检测）
4. **性能优化到位** — 模型单例模式、GPU 加速、结果缓存、断点续传
5. **测试覆盖较高** — 整体 61.49%，多个核心模块 >90%
6. **支持多种 LLM** — OpenAI 兼容接口、Ollama 本地模型、LM Studio
7. **Web UI 已就绪** — 单文件前端，无需构建，开箱即用

---

### 11.2 项目不足

1. **测试覆盖率待提升** — 目标 70%+（`analyzer_v2.py` 和 `cli.py` 需重点补充）
2. **Web UI 功能待完善** — 缺少分页、排序、筛选、编辑功能
3. **文档待补充** — 缺少用户手册、API 文档、开发者指南
4. **部署流程待优化** — 缺少 Dockerfile、CI/CD 配置
5. **批量处理未实现** — 无法处理多个视频链接（需手动逐个执行）

---

### 11.3 技术亮点

| 亮点 | 说明 |
|------|----------|
| **Whisper 模型单例模式** | 类级别缓存，所有实例共享，避免重复加载 |
| **多模态分析支持** | 文本 + 关键帧图片，提高分析准确率 |
| **自动错误修复** | 根据错误信息自动生成修复建议，甚至自动执行 |
| **知识库关联查询** | 视频和工具多对多关联，支持双向查询 |
| **HuggingFace 镜像自动切换** | 检测网络连接，自动选择最佳镜像源 |
| **4 级自动化级别** | extract → observe → confirm → auto，渐进式自动化 |

---

*本文档由 程 自动生成，基于完整代码分析*
*最后更新：2026-06-25 21:00*
