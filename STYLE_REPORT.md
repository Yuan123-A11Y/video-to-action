# 代码风格检查报告

**项目：** video-to-action  
**扫描时间：** 2026-06-25  
**扫描工具：** black, isort, flake8  

---

## 📊 扫描摘要

| 指标 | 数量 |
|------|------|
| 总文件数 | 117 |
| 需要格式化的文件（black） | 59 |
| 导入排序问题（isort） | 5 |
| PEP 8 违规（flake8） | 28 |
| **关键 Bug** | **1** |

---

## 🚨 关键 Bug（需立即修复）

| 文件 | 行号 | 错误码 | 问题描述 | 修复方案 |
|------|------|--------|----------|----------|
| `video_to_action/greenvideo_downloader.py` | 50 | F821 | 未定义名称 `detect_video_platform` | 导入 `detect_video_platform` 函数（应从 `ytdlp_downloader` 导入） |

---

## 🔧 详细问题清单

### 1. video_to_action/ 目录

| 文件 | 行号 | 错误码 | 问题类型 | 问题描述 | 修复方案 |
|------|------|--------|----------|----------|----------|
| `cli.py` | 66 | F841 | 未使用变量 | `stats_parser` 赋值但未使用 | 删除该行或添加 `_` 前缀 |
| `config.py` | 17 | E306 | 空行问题 | 嵌套定义前应有 1 个空行 | 在嵌套函数/类前添加空行 |
| `config.py` | 34,49,52 | W293 | 空白字符 | 空行包含空白字符 | 删除空行中的空格/制表符 |
| `douyin_downloader.py` | 9 | F401 | 未使用导入 | `typing.Any` 导入但未使用 | 删除该导入 |
| `douyin_downloader.py` | 11 | F401 | 未使用导入 | `detect_platform` 导入但未使用 | 删除该导入 |
| `downloader.py` | 34 | F401 | 未使用导入 | `pathlib.Path` 导入但未使用 | 删除该导入 |
| `extractor.py` | 58 | F401 | 未使用导入 | `os` 导入但未使用 | 删除该导入 |
| `extractor.py` | 63,71 | W293 | 空白字符 | 空行包含空白字符 | 删除空行中的空格/制表符 |
| `greenvideo_downloader.py` | 9 | F401 | 未使用导入 | `detect_platform` 导入但未使用 | 删除该导入 |
| `greenvideo_downloader.py` | 50 | F821 | 未定义名称 | `detect_video_platform` 未定义 | 添加 `from video_to_action.ytdlp_downloader import detect_video_platform` |
| `knowledge_base.py` | 116,153,195 | W291 | 行尾空白 | 行尾有空格 | 删除行尾空格 |
| `knowledge_base.py` | 246 | W293 | 空白字符 | 空行包含空白字符 | 删除空行中的空格/制表符 |
| `ytdlp_downloader.py` | 4 | F401 | 未使用导入 | `subprocess` 导入但未使用 | 删除该导入 |

### 2. tools/douyin-downloader/ 目录

| 文件 | 行号 | 错误码 | 问题类型 | 问题描述 | 修复方案 |
|------|------|--------|----------|----------|----------|
| `core/user_downloader.py` | 369 | E501 | 行太长 | 143 > 120 字符 | 换行 |
| `tools/cookie_fetcher.py` | 217 | E501 | 行太长 | 123 > 120 字符 | 换行 |
| `utils/abogus.py` | 3 | E265 | 注释格式 | 块注释应以 `# ` 开头 | 修改注释格式 |
| `utils/abogus.py` | 262,265,266,269 | E131 | 缩进问题 | continuation line unaligned | 对齐续行 |
| `utils/abogus.py` | 276,421,606,619,660,838,844,850 | E501 | 行太长 | 133-790 字符 | 换行 |

### 3. Black 格式问题（59 个文件）

以下文件需要运行 `black` 重新格式化（统一引号、空行、换行等）：

<details>
<summary>点击查看完整文件列表（59 个）</summary>

**video_to_action/ 目录（11 个）：**
- `config.py`
- `executor.py`
- `resolver.py`
- `utils.py`
- `analyzer_v2.py`
- `douyin_downloader.py`
- `extractor.py`
- `knowledge_base.py`
- `cli.py`
- `ytdlp_downloader.py`

**tools/douyin-downloader/ 目录（48 个）：**
- `auth/ms_token_manager.py`
- `config/config_loader.py`
- `core/downloader_factory.py`
- `core/audio_extraction.py`
- `core/silent_audio.py`
- `control/retry_handler.py`
- `control/queue_manager.py`
- `core/user_modes/music_strategy.py`
- `core/user_modes/mix_strategy.py`
- `core/mix_downloader.py`
- `core/comments_collector.py`
- `core/retry_executor.py`
- `core/user_modes/post_strategy.py`
- `cli/main.py`
- `core/transcript_manager.py`
- `server/jobs.py`
- `server/app.py`
- `core/music_downloader.py`
- `core/user_modes/base_strategy.py`
- `core/user_downloader.py`
- `tests/test_config_validation.py`
- `tests/test_cookie_fetcher.py`
- `tests/test_file_manager.py`
- `tests/test_database_top_authors.py`
- `tests/test_discovery.py`
- `cli/whisper_transcribe.py`
- `tests/test_config_loader.py`
- `tests/test_media_quality.py`
- `tests/test_silent_audio.py`
- `tests/test_music_downloader.py`
- `tests/test_database.py`
- `tests/test_live_downloader.py`
- `tests/test_downloader_author_sec_uid.py`
- `tests/test_audio_extraction.py`
- `core/api_client.py`
- `storage/database.py`
- `tests/test_naming.py`
- `tests/test_notifier_redactor_property.py`
- `tests/test_proxy_validator_parity.py`
- `utils/logger.py`
- `tests/test_user_downloader_modes.py`
- `tests/test_transcript_manager_audio.py`
- `tools/cookie_fetcher.py`
- `utils/notifier.py`
- `core/downloader_base.py`
- `utils/xbogus.py`
- `utils/naming.py`
- `utils/abogus.py`
- `tests/test_video_downloader.py`

</details>

---

## 🛠️ 自动修复方案

### 方案 1：一键自动修复（推荐）

运行以下命令，自动修复所有格式问题：

```bash
# 1. 使用 black 格式化所有文件（修复引号、空行、换行等）
python -m black video_to_action/ tools/douyin-downloader/

# 2. 使用 isort 排序导入
python -m isort video_to_action/ tools/douyin-downloader/

# 3. 使用 autopep8 修复 PEP 8 问题
python -m autopep8 --in-place --recursive --max-line-length=120 video_to_action/ tools/douyin-downloader/

# 4. 删除未使用的导入（需要 pyflakes）
python -m autoflake --in-place --remove-all-unused-imports --recursive video_to_action/ tools/douyin-downloader/
```

### 方案 2：手动修复关键 Bug

**Bug：greenvideo_downloader.py 引用未定义的 `detect_video_platform`**

修复方法：在 `video_to_action/greenvideo_downloader.py` 文件顶部添加：

```python
from video_to_action.ytdlp_downloader import detect_video_platform
```

并删除未使用的导入：

```python
# 删除这行
from video_to_action.utils import detect_platform
```

---

## 📋 修复脚本

保存以下脚本为 `fix_style.py`，然后运行：

```python
#!/usr/bin/env python3
"""自动修复代码风格问题。"""

import subprocess
import sys

def run(cmd: list[str]) -> None:
    """运行命令并打印输出。"""
    print(f"运行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        print(f"警告: 命令返回非零退出码 {result.returncode}")

def main() -> None:
    """主函数。"""
    # 1. 使用 black 格式化
    run([
        sys.executable, "-m", "black",
        "--line-length", "120",
        "video_to_action/",
        "tools/douyin-downloader/",
    ])

    # 2. 使用 isort 排序导入
    run([
        sys.executable, "-m", "isort",
        "--profile", "black",
        "video_to_action/",
        "tools/douyin-downloader/",
    ])

    # 3. 删除未使用的导入
    run([
        sys.executable, "-m", "autoflake",
        "--in-place",
        "--remove-all-unused-imports",
        "--recursive",
        "video_to_action/",
        "tools/douyin-downloader/",
    ])

    # 4. 使用 autopep8 修复 PEP 8 问题
    run([
        sys.executable, "-m", "autopep8",
        "--in-place",
        "--recursive",
        "--max-line-length", "120",
        "--extend-ignore", "E203,W503",
        "video_to_action/",
        "tools/douyin-downloader/",
    ])

    print("\n✅ 修复完成！请运行测试确保没有破坏现有功能。")

if __name__ == "__main__":
    main()
```

---

## ✅ 修复后的验证

修复完成后，运行以下命令验证：

```bash
# 1. 检查 black 格式
python -m black --check video_to_action/ tools/douyin-downloader/

# 2. 检查 isort 导入排序
python -m isort --check-only video_to_action/ tools/douyin-downloader/

# 3. 检查 flake8 PEP 8 违规
python -m flake8 video_to_action/ tools/douyin-downloader/ --max-line-length=120

# 4. 运行测试
python -m pytest tests/ -v
```

---

## 📝 风格规范建议

建议在项目中添加以下配置文件，确保团队统一风格：

### 1. `.editorconfig`（编辑器配置）

```ini
[*.py]
indent_style = space
indent_size = 4
max_line_length = 120
quote_type = double
```

### 2. `pyproject.toml`（已添加）

已完成。

### 3. 预提交钩子（`.pre-commit-config.yaml`）

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
```

---

**报告结束**
