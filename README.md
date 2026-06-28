# Video-to-Action 🎬

**视频内容分析与动作生成工具** - 从视频中提取可执行的行动计划。

---

## 🚀 快速开始

### 1. 一键部署（推荐）

#### Windows
```bash
# 双击运行或从命令行执行
deploy.bat
```

#### Linux / macOS
```bash
chmod +x deploy.sh
./deploy.sh
```

### 2. 手动部署

#### 2.1 创建虚拟环境
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

#### 2.2 安装依赖
```bash
pip install -r requirements.txt
playwright install
```

#### 2.3 安装系统依赖
```bash
# Ubuntu / Debian
sudo apt-get install -y ffmpeg

# macOS
brew install ffmpeg

# Windows：下载 ffmpeg 并添加到 PATH
# https://ffmpeg.org/download.html
```

---

## 🔧 配置

### 方法1：交互式配置（推荐）
```bash
python -m video_to_action.cli setup
```

此命令会引导您配置：
- LLM 提供商（OpenAI、Ollama、LM Studio、Mock）
- API Key（如果使用 OpenAI）
- 模型选择
- 数据库类型（SQLite / MySQL）
- 安全选项

### 方法2：手动配置
复制示例配置并修改：
```bash
cp .env.example .env
# 编辑 .env 文件
```

或修改配置文件：
```bash
# 编辑 config/settings.yaml
```

---

## 🎯 使用方法

### 1. 处理单个视频
```bash
# 使用 B站视频
python -m video_to_action.cli process "https://www.bilibili.com/video/BV1xx411c7mD"

# 使用本地视频文件
python -m video_to_action.cli process "C:\Videos\video.mp4"

# 带预热（减少首次处理时间）
python -m video_to_action.cli process "视频URL" --warmup

# 详细输出
python -m video_to_action.cli process "视频URL" --verbose
```

### 2. 批量处理视频
```bash
# 创建视频列表文件
echo "https://www.bilibili.com/video/BV1xx411c7mD" > videos.txt
echo "https://www.bilibili.com/video/BV1yy411c7mE" >> videos.txt

# 批量处理
python -m video_to_action.cli batch videos.txt --output outputs
```

### 3. 模型预热
```bash
# 预热 LLM 模型（减少首次请求延迟）
python -m video_to_action.cli process "视频URL" --warmup
```

### 4. 清除缓存
```bash
# 清除分析器缓存
python -m video_to_action.cli clear-cache
```

---

## 📂 项目结构

```
video-to-action/
├── config/                    # 配置文件
│   └── settings.yaml          # 主配置文件
├── data/                      # 数据目录
│   └── video_to_action.db    # SQLite 数据库
├── outputs/                   # 输出目录
│   ├── cache/                # 分析器缓存
│   └── *.md                 # 生成的操作笔记
├── scripts/                   # 脚本目录
│   ├── deploy.py             # 部署脚本
│   ├── batch_process.py      # 批量处理脚本
│   └── warmup.py            # 模型预热脚本
├── video_to_action/           # 主模块
│   ├── cli.py               # 命令行入口
│   ├── analyzer_v2.py       # 视频内容分析（异步）
│   ├── extractor.py         # 音频提取和转写
│   ├── executor.py          # 命令执行
│   ├── reporter.py         # 报告生成
│   ├── exceptions.py        # 统一异常类
│   ├── config_wizard.py     # 交互式配置向导
│   └── tests/              # 单元测试
│       ├── test_exceptions.py
│       ├── test_utils.py
│       └── test_config.py
├── deploy.bat               # Windows 部署脚本
├── deploy.sh                # Linux/macOS 部署脚本
├── requirements.txt          # Python 依赖
├── pyproject.toml          # 项目配置
├── .env.example             # 环境变量模板
├── DEPLOYMENT_GUIDE.md     # 详细部署指南
└── README.md               # 本文件
```

---

## 🧪 测试

### 运行所有单元测试
```bash
python -m pytest video_to_action/tests/ -v
```

### 测试覆盖率
```bash
python -m pytest video_to_action/tests/ --cov=video_to_action --cov-report=term-missing
```

### 测试配置
```bash
python -m video_to_action.cli config-test
```

---

## 📊 功能特性

### ✅ 已完成功能

1. **异步 LLM 调用** - 使用 `asyncio` 实现真正的异步调用
2. **批量处理** - 支持批量处理多个视频
3. **模型预热** - `--warmup` 参数，减少首次处理时间
4. **持久化** - 保存/加载预热状态，有效期1小时
5. **统一异常处理** - 创建 `exceptions.py`，所有异常包含问题描述和建议解决方案
6. **进度条显示** - 使用 `tqdm` 显示5个步骤的进度
7. **交互式配置向导** - `setup` 命令，引导式配置
8. **数据库索引优化** - 为 `tools` 表添加 `idx_tool_name` 索引
9. **单元测试** - 34个单元测试，全部通过 ✅

### ❌ 待完成功能（需其他专家）

1. **Web UI 设计** - 需要 UI 设计师（Figma）
2. **Web UI 开发** - 需要前端工程师（React/Vue）

---

## 🔍 常见问题

### Q1: ffmpeg 未找到
**错误信息**：`ExtractionError: 未找到 ffmpeg，请先安装 ffmpeg`

**解决方案**：
```bash
# 检查 ffmpeg 是否在 PATH 中
ffmpeg -version

# 如果不在 PATH 中，添加到配置文件
# 编辑 config/settings.yaml
ffmpeg_path: "/path/to/ffmpeg"
```

### Q2: LLM API 调用失败
**错误信息**：`AnalysisError: LLM API 调用失败（已重试 3 次）`

**解决方案**：
1. 检查 API Key 是否正确
2. 检查网络连接
3. 检查 API 配额是否用完
4. 如果使用 Ollama，确保服务已启动：`ollama serve`

### Q3: 数据库迁移失败
**错误信息**：`sqlite3.OperationalError: index idx_tool_name already exists`

**解决方案**：
```bash
# 重置数据库（⚠️ 会丢失数据）
rm data/video_to_action.db
python -m video_to_action.cli process --help  # 重新创建数据库
```

---

## 📖 文档

- **部署指南**：`DEPLOYMENT_GUIDE.md` - 详细的生产环境部署指南
- **执行计划**：`deliverables/product-strategy/execution-plan-2026-06-26.md`
- **完成报告**：`EXECUTION_COMPLETION_REPORT_FINAL.md`

---

## 📞 技术支持

**开发者**：吴八哥（高级开发工程师）

**遇到问题？**
1. 查看日志文件：`logs/video_to_action.log`
2. 运行配置测试：`python -m video_to_action.cli config-test`
3. 查看详细文档：`DEPLOYMENT_GUIDE.md`

---

## 📝 更新日志

### v0.1.0 (2026-06-26)
- ✅ 实现异步 LLM 调用
- ✅ 添加批量处理功能
- ✅ 实现模型预热 + 持久化
- ✅ 优化错误提示（统一异常类）
- ✅ 添加进度条显示
- ✅ 实现交互式配置向导
- ✅ 数据库索引优化
- ✅ 编写单元测试（34个，全部通过）
- ✅ 创建部署脚本和指南

---

**开始使用 Video-to-Action 吧！** 🎉
