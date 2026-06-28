# Video-to-Action 代码审查标准

**版本**: v1.0  
**生效日期**: 2026-06-26  
**维护者**: Video-to-Action Team

---

## 1. 文档目的

本文档定义 Video-to-Action 项目的代码审查标准，确保代码质量、安全性和可维护性。所有代码变更在合并到主分支前必须通过代码审查。

---

## 2. 审查原则

### 2.1 核心原则

1. **尽早审查** - 小批量、高频次的审查比大批量审查更有效
2. **建设性反馈** - 批评代码，而非人；提供改进建议，而非仅指出问题
3. **明确优先级** - 使用标准标记区分问题严重程度
4. **知识共享** - 审查过程是团队学习和知识传递的机会
5. **持续改进** - 根据审查发现的问题，持续改进标准和流程

### 2.2 审查者职责

- 确保代码功能正确、安全、可维护
- 检查代码是否符合项目和行业标准
- 提供清晰的反馈和改进建议
- 批准或拒绝代码合并请求
- 与作者沟通，确保问题得到解决

### 2.3 作者职责

- 提交清晰、自包含的变更
- 提供充分的上下文和说明
- 积极响应审查反馈
- 及时修复发现的问题
- 不将未解决的问题标记为"已解决"

---

## 3. 代码质量标准

### 3.1 正确性 (Correctness)

#### 必须检查项

- [ ] **功能实现** - 代码是否实现了预期功能？
- [ ] **边界条件** - 是否处理了所有边界情况（空值、空列表、最大值等）？
- [ ] **错误处理** - 是否妥善处理了可能的异常和错误？
- [ ] **并发安全** - 多线程/异步代码是否存在竞态条件？
- [ ] **逻辑正确性** - 算法和逻辑是否正确的？

#### Python 特定检查

```python
# ❌ 错误示例：未处理边界条件
def process_video(video_path: str) -> dict:
    with open(video_path, 'r') as f:
        data = f.read()
    return {"status": "success", "data": data}

# ✅ 正确示例：处理边界条件
def process_video(video_path: str) -> dict:
    if not video_path or not os.path.exists(video_path):
        return {"status": "error", "message": "视频文件不存在"}
    
    try:
        with open(video_path, 'r') as f:
            data = f.read()
        return {"status": "success", "data": data}
    except IOError as e:
        logger.error("读取视频文件失败: %s", e)
        return {"status": "error", "message": str(e)}
```

---

### 3.2 安全性 (Security)

#### 🔴 阻断级问题（必须修复）

| 问题类型 | 检查项 | 示例 |
|---------|--------|------|
| **SQL注入** | 是否使用参数化查询？ | ❌ `cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")` |
| **命令注入** | 是否验证和清理用户输入？ | ❌ `os.system(f"ffmpeg -i {user_input}.mp4")` |
| **路径遍历** | 是否验证文件路径？ | ❌ `open(f"outputs/{user_filename}", 'w')` |
| **敏感信息泄露** | 是否提交了密钥、密码？ | ❌ `API_KEY = "sk-abc123"` |
| **XSS攻击** | 是否转义用户输入？ | ❌ `return f"<div>{user_input}</div>"` |
| **不安全的反序列化** | 是否使用安全的序列化方法？ | ❌ `pickle.loads(user_data)` |

#### 安全检查清单

```python
# ✅ 安全示例：参数化查询
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# ✅ 安全示例：验证文件路径
from pathlib import Path
output_dir = Path("outputs")
file_path = output_dir / user_filename
if not file_path.resolve().startswith(output_dir.resolve()):
    raise ValueError("非法的文件路径")

# ✅ 安全示例：使用环境变量存储密钥
import os
API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ 安全示例：转义用户输入
from html import escape
return f"<div>{escape(user_input)}</div>"
```

---

### 3.3 可维护性 (Maintainability)

#### 必须检查项

- [ ] **命名规范** - 变量、函数、类名是否清晰、一致？
- [ ] **函数长度** - 函数是否过长（>50行）？是否应拆分？
- [ ] **代码复杂度** - 圈复杂度是否过高（>10）？
- [ ] **注释质量** - 注释是否解释"为什么"，而非"是什么"？
- [ ] **文档完整性** - 公共API是否有文档字符串？
- [ ] **代码重复** - 是否存在重复代码可以抽取？

#### 命名规范（Python）

```python
# ❌ 错误示例：命名不清晰
def proc(v):  # 缩写不清晰
    pass

class videoDL:  # 混合大小写不规范
    pass

# ✅ 正确示例：命名清晰
def process_video(video_path: str) -> dict:
    """处理视频文件，提取音频和关键帧。"""
    pass

class VideoDownloader:
    """视频下载器基类。"""
    pass
```

#### 函数复杂度

```python
# ❌ 错误示例：函数过长、复杂度高
def process_video(video_path):
    # 100+ 行代码，嵌套层次深
    if condition1:
        if condition2:
            if condition3:
                # ...
    # ...

# ✅ 正确示例：拆分函数
def process_video(video_path: str) -> dict:
    """处理视频文件的主函数。"""
    video_info = extract_video_info(video_path)
    audio_path = extract_audio(video_path)
    frames = extract_key_frames(video_path)
    return {
        "info": video_info,
        "audio": audio_path,
        "frames": frames
    }

def extract_video_info(video_path: str) -> dict:
    """提取视频元数据。"""
    # ...

def extract_audio(video_path: str) -> str:
    """提取音频。"""
    # ...
```

---

### 3.4 性能 (Performance)

#### 必须检查项

- [ ] **时间复杂度** - 算法时间复杂度是否合理？
- [ ] **空间复杂度** - 是否存在不必要的内存占用？
- [ ] **数据库查询** - 是否存在 N+1 查询问题？
- [ ] **文件操作** - 是否及时关闭文件句柄？
- [ ] **循环优化** - 循环中是否有可提取的计算？
- [ ] **缓存使用** - 是否合理使用缓存？

#### 性能检查示例

```python
# ❌ 错误示例：N+1 查询问题
for user in users:
    orders = db.query(f"SELECT * FROM orders WHERE user_id = {user.id}")
    process_orders(orders)

# ✅ 正确示例：批量查询
user_ids = [user.id for user in users]
orders = db.query(f"SELECT * FROM orders WHERE user_id IN ({','.join(map(str, user_ids))})")
# 然后在应用层按用户分组

# ❌ 错误示例：循环中重复计算
for item in items:
    result = expensive_computation(item)
    normalized = result / max_value  # max_value 在循环中不变

# ✅ 正确示例：提取不变的计算
max_value = get_max_value()
for item in items:
    result = expensive_computation(item)
    normalized = result / max_value
```

---

### 3.5 测试 (Testing)

#### 必须检查项

- [ ] **测试覆盖** - 新代码是否有对应的测试？
- [ ] **测试质量** - 测试是否覆盖了关键路径和边界条件？
- [ ] **测试命名** - 测试名称是否描述性强？
- [ ] **测试独立性** - 测试是否相互独立？
- [ ] **Mock使用** - 是否合理使用Mock？
- [ ] **测试数据** - 是否使用合适的测试数据？

#### 测试示例

```python
# ❌ 错误示例：测试命名不清晰、未覆盖边界条件
def test_process():
    result = process_video("test.mp4")
    assert result is not None

# ✅ 正确示例：测试命名清晰、覆盖边界条件
def test_process_video_with_valid_file_returns_success():
    """测试处理有效视频文件时返回成功结果。"""
    result = process_video("test.mp4")
    assert result["status"] == "success"
    assert "data" in result

def test_process_video_with_nonexistent_file_returns_error():
    """测试处理不存在的视频文件时返回错误。"""
    result = process_video("nonexistent.mp4")
    assert result["status"] == "error"
    assert "message" in result

def test_process_video_with_empty_path_raises_exception():
    """测试传入空路径时抛出异常。"""
    with pytest.raises(ValueError):
        process_video("")
```

---

## 4. Python 代码规范

### 4.1 风格规范

遵循 [PEP 8](https://pep8.org/) 和项目配置：

```toml
# pyproject.toml
[tool.black]
line-length = 120
target-version = ['py312']

[tool.isort]
profile = "black"
line_length = 120
```

#### 关键规范

1. **行长度** - 最大120字符
2. **缩进** - 使用4个空格
3. **导入顺序** - 标准库 → 第三方库 → 本地模块
4. **空行** - 顶层函数和类之间空两行，方法之间空一行
5. **命名** - 
   - 函数/变量：小写 + 下划线 (`process_video`)
   - 类：首字母大写 (`VideoDownloader`)
   - 常量：全大写 (`MAX_RETRIES`)
   - 私有属性：前缀下划线 (`_internal_method`)

### 4.2 类型注解

**必须**：所有公共函数的参数和返回值必须有类型注解

```python
# ❌ 错误示例：缺少类型注解
def process_video(path):
    pass

# ✅ 正确示例：完整的类型注解
from typing import Optional
from pathlib import Path

def process_video(
    video_path: str | Path,
    output_dir: Optional[str | Path] = None,
    extract_audio: bool = True
) -> dict[str, Any]:
    """
    处理视频文件。
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录，默认为当前目录
        extract_audio: 是否提取音频
        
    Returns:
        包含处理结果的字典
    """
    pass
```

### 4.3 文档字符串

使用 [Google 风格](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) 的文档字符串：

```python
def process_video(video_path: str, config: dict) -> dict:
    """
    处理视频文件并提取内容。
    
    Args:
        video_path: 视频文件绝对路径
        config: 配置字典，包含转录和分析参数
        
    Returns:
        包含转录文本、关键帧和操作方案的字典
        
    Raises:
        FileNotFoundError: 视频文件不存在
        TranscriptionError: 音频转写失败
        
    Examples:
        >>> result = process_video("/path/to/video.mp4", config)
        >>> print(result["transcript"][:100])
    """
    pass
```

---

## 5. 项目特定标准

### 5.1 配置管理

#### 检查项

- [ ] 配置键名是否一致？（注意 `safety` vs `safety` 拼写）
- [ ] 是否提供了合理的默认值？
- [ ] 是否验证了配置值的类型和范围？
- [ ] 敏感配置是否通过环境变量读取？

```python
# ✅ 正确的配置验证
def _validate_thread(value: Any) -> int:
    """验证并转换 thread 配置。"""
    try:
        thread_val = int(value)
        if thread_val < 1:
            raise ValueError("thread must be >= 1")
        if thread_val > 20:
            logger.warning("thread=%s exceeds recommended max 20", thread_val)
        return thread_val
    except (TypeError, ValueError):
        logger.warning("Invalid thread value: %s, using default 5", value)
        return 5
```

### 5.2 错误处理

#### 检查项

- [ ] 是否统一使用异常而非返回错误字典？
- [ ] 是否定义了自定义异常类？
- [ ] 是否记录了足够的错误上下文？
- [ ] 是否向用户提供了清晰的错误消息？

```python
# ✅ 正确的错误处理
# 定义自定义异常
class VideoToActionError(Exception):
    """基础异常类。"""
    pass

class DownloadError(VideoToActionError):
    """下载失败。"""
    pass

# 使用异常而非返回错误字典
def download_video(url: str) -> Path:
    """下载视频并返回本地路径。"""
    try:
        # 下载逻辑
        pass
    except NetworkError as e:
        logger.error("下载失败: %s, URL: %s", e, url)
        raise DownloadError(f"无法下载视频: {e}") from e
```

### 5.3 日志记录

#### 检查项

- [ ] 是否使用了 `logging` 模块而非 `print()`？
- [ ] 日志级别是否合适？（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- [ ] 是否记录了关键的流程和决策点？
- [ ] 是否避免了记录敏感信息？

```python
# ✅ 正确的日志记录
import logging

logger = logging.getLogger(__name__)

def process_video(video_path: str) -> dict:
    """处理视频文件。"""
    logger.info("开始处理视频: %s", video_path)
    
    try:
        logger.debug("正在提取音频...")
        audio_path = extract_audio(video_path)
        logger.info("音频提取成功: %s", audio_path)
        
        logger.debug("正在转写音频...")
        transcript = transcribe_audio(audio_path)
        logger.info("音频转写完成，文本长度: %d", len(transcript))
        
        return {"status": "success", "transcript": transcript}
    except Exception as e:
        logger.error("视频处理失败: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}
```

### 5.4 异步代码

#### 检查项

- [ ] 是否正确使用了 `async/await`？
- [ ] 是否避免了阻塞操作？
- [ ] 是否正确管理了异步上下文？
- [ ] 是否处理了异步异常？

```python
# ✅ 正确的异步代码
import asyncio
from contextlib import asynccontextmanager

class APIClient:
    """异步API客户端。"""
    
    @asynccontextmanager
    async def get_client(self):
        """获取HTTP客户端的异步上下文管理器。"""
        client = httpx.AsyncClient(timeout=30.0)
        try:
            yield client
        finally:
            await client.aclose()
    
    async def fetch_data(self, url: str) -> dict:
        """异步获取数据。"""
        async with self.get_client() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error("HTTP错误: %s, URL: %s", e, url)
                raise
```

---

## 6. 问题严重程度标记

在代码审查中使用以下标记：

### 🔴 Blocker（阻断）

**必须修复后才能合并**

- 安全漏洞（注入、XSS、认证绕过等）
- 数据丢失或 corruption 风险
- 竞态条件或死锁
- 破坏API契约
- 关键路径缺少错误处理

**示例评论**：

```
🔴 **Security: Command Injection Risk**
File: `video_to_action/executor.py`, Line 42

**Problem:** User input is directly interpolated into the command string.

Current code:
```python
os.system(f"ffmpeg -i {video_path} -o {output_path}")
```

**Why:** An attacker could inject malicious commands via `video_path`.

**Suggestion:**
- Use `subprocess.run()` with a list of arguments:
  ```python
  subprocess.run(["ffmpeg", "-i", video_path, "-o", output_path])
  ```
- Or validate and sanitize the input:
  ```python
  if not re.match(r'^[\w\-\.\/]+$', video_path):
      raise ValueError("Invalid video path")
  ```
```

---

### 🟡 Suggestion（建议）

**应该修复，但不阻断合并**

- 缺少输入验证
- 命名不清晰或逻辑混乱
- 重要行为缺少测试
- 性能问题（N+1查询、不必要的内存分配）
- 应提取的代码重复

**示例评论**：

```
🟡 **Maintainability: Function Too Complex**
File: `video_to_action/analyzer_v2.py`, Line 89

**Problem:** The `analyze()` function is 120 lines long and has a cyclomatic complexity of 15.

**Why:** Long functions are harder to test, understand, and maintain.

**Suggestion:**
- Extract the LLM call logic into a separate function:
  ```python
  def _call_llm(self, prompt: str) -> str:
      """Call LLM with the given prompt."""
      # ...
  
  def _parse_response(self, raw: str) -> dict:
      """Parse LLM response into structured data."""
      # ...
  
  def analyze(self, transcription: dict) -> dict:
      prompt = self._build_prompt(transcription["text"])
      raw_response = self._call_llm(prompt)
      return self._parse_response(raw_response)
  ```
```

---

### 💭 Nit（细节）

**可以后续改进，不紧急**

- 风格不一致（如果没有linter处理）
- 次要的命名改进
- 文档缺失
- 值得考虑的替代方案

**示例评论**：

```
💭 **Style: Consider Using f-string**
File: `video_to_action/utils.py`, Line 156

**Current code:**
```python
message = "Processing video: " + video_name + " (" + str(video_id) + ")"
```

**Suggestion:**
Consider using f-strings for better readability:
```python
message = f"Processing video: {video_name} ({video_id})"
```

This is a minor style suggestion and not required for merge.
```

---

## 7. 审查检查清单

审查者在每次审查时应使用此清单：

### 7.1 自动化检查（Pre-commit/CI）

- [ ] 代码格式化工具（black, isort）已运行
- [ ] 静态类型检查（mypy）通过
- [ ] 代码质量检查（pylint, flake8）通过
- [ ] 测试全部通过
- [ ] 测试覆盖率未下降

### 7.2 手动检查

#### 功能正确性

- [ ] 代码实现了预期功能
- [ ] 处理了边界条件
- [ ] 错误处理恰当

#### 安全性

- [ ] 无SQL注入、命令注入等漏洞
- [ ] 无敏感信息泄露
- [ ] 输入验证充分

#### 可维护性

- [ ] 命名清晰、一致
- [ ] 函数长度合理
- [ ] 代码复杂度可控
- [ ] 注释和文档充分

#### 性能

- [ ] 无明显的性能瓶颈
- [ ] 数据库查询优化
- [ ] 内存使用合理

#### 测试

- [ ] 新代码有对应测试
- [ ] 测试覆盖关键路径
- [ ] 测试命名清晰

---

## 8. 审查流程

### 8.1 提交前（作者）

1. **Self-review** - 自己先审查代码
2. **运行测试** - 确保所有测试通过
3. **运行linter** - 运行 `black`, `isort`, `mypy`, `pylint`
4. **编写测试** - 为新功能编写测试
5. **更新文档** - 更新相关的文档

### 8.2 审查中（审查者）

1. **理解变更** - 阅读变更说明和相关issue
2. **检查自动化结果** - 确认CI通过
3. **逐文件审查** - 使用清单进行系统审查
4. **提供反馈** - 使用标准标记（🔴/🟡/💭）
5. **提出疑问** - 对不清晰的地方提问

### 8.3 审查后（作者）

1. **回应反馈** - 逐条回应审查意见
2. **修复问题** - 修复标记的问题
3. **更新代码** - 提交修复后的代码
4. **回复评论** - 在评论中说明修复情况
5. **请求重新审查** - 标记审查为"Ready for review"

---

## 9. 常见问题与解决方案

### Q1: 如何处理大量的风格问题？

**A**: 使用自动化工具（black, isort）统一风格，而非在审查中讨论风格问题。

### Q2: 审查者过多关注细节怎么办？

**A**: 审查者应优先关注正确性、安全性和架构，细节问题标记为 💭 Nit。

### Q3: 作者不认同审查意见怎么办？

**A**: 在评论中讨论，必要时请第三方（Tech Lead）仲裁。

### Q4: 紧急修复如何审查？

**A**: 紧急修复可以先合并，但必须在合并后24小时内补充完整的代码审查。

---

## 10. 工具推荐

### 10.1 必备工具

| 工具 | 用途 | 配置文件 |
|------|------|----------|
| **black** | 代码格式化 | `pyproject.toml` |
| **isort** | 导入排序 | `pyproject.toml` |
| **mypy** | 静态类型检查 | `pyproject.toml` |
| **pylint** | 代码质量检查 | `.pylintrc` |
| **pytest** | 测试框架 | `pyproject.toml` |
| **pytest-cov** | 测试覆盖率 | `pyproject.toml` |

### 10.2 可选工具

| 工具 | 用途 |
|------|------|
| **pre-commit** | Git hooks 管理 |
| **sonarqube** | 代码质量平台 |
| **codecov** | 覆盖率报告 |
| **dependabot** | 依赖更新 |

---

## 11. 附录

### A. 审查评论模板

```
### 🔴/🟡/💭 **[Category]: [Title]**

**File:** `path/to/file.py`, **Line:** XX

**Problem:** [描述问题]

**Why:** [解释为什么这是问题]

**Suggestion:**
[提供具体的修复建议或代码示例]
```

### B. 审查检查清单（打印版）

See [CODE_REVIEW_CHECKLIST.md](./CODE_REVIEW_CHECKLIST.md)

---

**文档版本**: v1.0  
**最后更新**: 2026-06-26  
**维护者**: Video-to-Action Team

如有疑问或建议，请联系 Tech Lead 或在 GitHub Issues 中讨论。
