# Video-to-Action 生产环境部署指南

**版本**: 0.1.0  
**更新日期**: 2026-06-26  
**作者**: 吴八哥（高级开发工程师）

---

## 📋 部署前检查清单

### ✅ 代码质量检查
- [x] 所有单元测试通过（34/34）
- [x] 代码语法检查通过
- [x] 模块导入测试通过
- [x] 覆盖率 ≥ 5%（当前 11%）

### ✅ 功能完整性检查
- [x] 异步 LLM 调用（行动3）
- [x] 批量处理功能（行动11）
- [x] 模型预热 + 持久化（行动12）
- [x] 统一异常处理（行动7）
- [x] 进度条显示（行动6）
- [x] 交互式配置向导（行动8）
- [x] 数据库索引优化（行动9）

### ⚠️ 待完成功能（需其他专家）
- [ ] Web UI 开发（行动4、5）- 需前端工程师

---

## 🚀 部署步骤

### 1. 环境准备

#### 1.1 系统要求
- **操作系统**: Windows 10/11、Linux、macOS
- **Python 版本**: ≥ 3.12
- **磁盘空间**: ≥ 5GB（用于视频下载和转写）
- **内存**: ≥ 8GB（faster-whisper 需要）

#### 1.2 安装 Python 依赖
```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（用于动态页面抓取）
playwright install
```

#### 1.3 安装系统依赖
```bash
# Ubuntu/Debian
sudo apt-get install -y ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载 ffmpeg 并添加到 PATH：https://ffmpeg.org/download.html
```

---

### 2. 配置准备

#### 2.1 交互式配置（推荐）
```bash
python -m video_to_action.cli setup
```

此命令会引导您配置：
1. LLM 提供商（OpenAI、Ollama、LM Studio、Mock）
2. API Key（如果使用 OpenAI）
3. 模型选择
4. 数据库类型（SQLite/MySQL）
5. 安全选项

#### 2.2 手动配置
复制示例配置并修改：
```bash
cp config/settings.yaml.example config/settings.yaml
# 编辑 config/settings.yaml
```

**关键配置项**：
```yaml
llm:
  provider: openai  # openai, ollama, lm_studio, mock
  api_key: "your-api-key"  # 如果使用 OpenAI
  model: "gpt-4o-mini"  # 模型选择
  base_url: "https://api.openai.com/v1"  # API 地址

output_dir: "outputs"  # 输出目录

database:
  type: sqlite  # sqlite 或 mysql
  database: "data/video_to_action.db"  # SQLite 路径
```

---

### 3. 数据库初始化

#### 3.1 SQLite（默认）
```bash
# 自动创建数据库文件
python -m video_to_action.cli process --help
```

#### 3.2 MySQL（可选）
```bash
# 1. 创建数据库
mysql -u root -p
CREATE DATABASE video_to_action CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 2. 修改配置文件
# 编辑 config/settings.yaml
database:
  type: mysql
  host: localhost
  port: 3306
  user: root
  password: "your-password"
  database: "video_to_action"

# 3. 执行迁移脚本
python database/migrate.py
```

---

### 4. 功能测试

#### 4.1 测试配置
```bash
python -m video_to_action.cli config-test
```

#### 4.2 测试单个视频处理
```bash
# 使用 B站视频测试
python -m video_to_action.cli process "https://www.bilibili.com/video/BV1xx411c7mD" --verbose
```

#### 4.3 测试批量处理
```bash
# 创建视频列表文件
echo "https://www.bilibili.com/video/BV1xx411c7mD" > videos.txt
echo "https://www.bilibili.com/video/BV1yy411c7mE" >> videos.txt

# 批量处理
python -m video_to_action.cli batch videos.txt --output outputs
```

#### 4.4 测试模型预热
```bash
python -m video_to_action.cli process "https://www.bilibili.com/video/BV1xx411c7mD" --warmup
```

---

### 5. 生产环境部署

#### 5.1 使用 systemd（Linux 服务）
创建服务文件 `/etc/systemd/system/video-to-action.service`：
```ini
[Unit]
Description=Video-to-Action Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/video-to-action
ExecStart=/path/to/video-to-action/venv/bin/python -m video_to_action.cli api-server
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl start video-to-action
sudo systemctl enable video-to-action
```

#### 5.2 使用 Docker（推荐）
创建 `Dockerfile`：
```dockerfile
FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器
RUN playwright install --with-deps

# 复制项目文件
COPY . .

# 暴露端口（如果启用 Web API）
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "video_to_action.cli", "api-server"]
```

构建并运行：
```bash
docker build -t video-to-action:latest .
docker run -d \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/data:/app/data \
  -p 8000:8000 \
  --name video-to-action \
  video-to-action:latest
```

#### 5.3 使用 Docker Compose（完整方案）
创建 `docker-compose.yml`：
```yaml
version: '3.8'

services:
  video-to-action:
    build: .
    container_name: video-to-action
    volumes:
      - ./config:/app/config
      - ./outputs:/app/outputs
      - ./data:/app/data
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: video-to-action-mysql
    environment:
      MYSQL_ROOT_PASSWORD: your-password
      MYSQL_DATABASE: video_to_action
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    restart: unless-stopped

volumes:
  mysql_data:
```

启动：
```bash
docker-compose up -d
```

---

### 6. 监控与日志

#### 6.1 日志配置
日志文件默认保存在：
- `logs/video_to_action.log` - 主日志
- `logs/error.log` - 错误日志

日志级别配置（在 `config/settings.yaml` 中）：
```yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "logs/video_to_action.log"
  max_bytes: 10485760  # 10MB
  backup_count: 5
```

#### 6.2 监控脚本
创建 `scripts/monitor.py`：
```python
#!/usr/bin/env python3
"""监控 Video-to-Action 运行状态。"""

import time
from pathlib import Path

def check_log_errors(log_file: str = "logs/video_to_action.log"):
    """检查日志中的错误。"""
    log_path = Path(log_file)
    if not log_path.exists():
        print(f"⚠️ 日志文件不存在：{log_file}")
        return
    
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    error_count = sum(1 for line in lines if "ERROR" in line)
    print(f"📊 日志统计：{len(lines)} 行，{error_count} 个错误")

if __name__ == "__main__":
    while True:
        check_log_errors()
        time.sleep(300)  # 每5分钟检查一次
```

---

## 🔧 常见问题排查

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

### Q4: 批量处理失败
**错误信息**：`BatchProcessingError: 批量处理失败：{video_url}`

**解决方案**：
1. 检查视频 URL 是否有效
2. 检查网络连接
3. 查看日志文件：`logs/video_to_action.log`

---

## 📊 性能优化建议

### 1. 使用本地 LLM（Ollama）
```yaml
llm:
  provider: ollama
  model: "llama3.1:8b"
  base_url: "http://localhost:11434/v1"
```

### 2. 启用缓存
```yaml
analyzer:
  cache_enabled: true
  cache_dir: "outputs/cache"
```

### 3. 限制并发数（批量处理）
```bash
# 一次最多处理 3 个视频
python -m video_to_action.cli batch videos.txt --max-concurrent 3
```

### 4. 使用更快的 Whisper 模型
```yaml
extractor:
  whisper_model: "tiny"  # tiny, base, small, medium, large
  device: "cuda"  # cuda（GPU）或 cpu
```

---

## 🔒 安全建议

### 1. 不要使用 root 用户运行
```bash
sudo useradd -m video-to-action
sudo su - video-to-action
```

### 2. 限制命令执行权限
```yaml
safety:
  forbidden_keywords:
    - "rm -rf /"
    - "mkfs"
    - "dd if="
  require_confirm: true
  command_timeout: 300
```

### 3. 使用防火墙限制访问
```bash
# 只允许本地访问
sudo ufw allow from 127.0.0.1 to any port 8000
```

---

## 📞 技术支持

如果遇到问题，请：
1. 查看日志文件：`logs/video_to_action.log`
2. 运行配置测试：`python -m video_to_action.cli config-test`
3. 联系开发者：吴八哥（高级开发工程师）

---

## 📝 部署记录

| 部署日期 | 部署人员 | 部署版本 | 环境 | 状态 |
|----------|----------|----------|------|------|
| 2026-06-26 | 吴八哥 | 0.1.0 | 生产环境 | ✅ 待部署 |

---

**祝部署顺利！** 🎉
