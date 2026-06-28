# Video-to-Action 项目完善方案

**目标**: 将项目补充为完整的、可部署的软件项目  
**时间**: 2026-06-26  
**执行方式**: 自动化执行（无需人工确认）

---

## 一、方案概述

本方案将补充项目缺失的核心组件，使其达到生产级项目标准。

### 补充内容清单

| # | 组件 | 优先级 | 预计工作量 |
|---|------|--------|------------|
| 1 | `CHANGELOG.md` | P0 | 低 |
| 2 | `.env.example` | P0 | 低 |
| 3 | `Dockerfile` | P0 | 中 |
| 4 | `docker-compose.yml` | P0 | 中 |
| 5 | GitHub Actions CI/CD | P0 | 中 |
| 6 | API 文档（OpenAPI） | P1 | 中 |
| 7 | 健康检查端点 | P1 | 低 |
| 8 | 结构化日志配置 | P1 | 低 |
| 9 | `CONTRIBUTING.md` | P2 | 低 |
| 10 | 依赖漏洞扫描 | P2 | 低 |

---

## 二、详细执行计划

### Phase 1: 项目基础（P0）

#### 1.1 `CHANGELOG.md`
- **内容**: 记录项目版本变更历史
- **格式**: [Keep a Changelog](https://keepachangelog.com/zh-CN/) 格式
- **版本**: 从 `v0.1.0` 开始

#### 1.2 `.env.example`
- **内容**: 环境变量示例文件
- **包含**: 
  - `LLM_API_KEY` - LLM API 密钥
  - `LLM_BASE_URL` - LLM API 地址
  - `MYSQL_HOST` - MySQL 主机
  - `MYSQL_PORT` - MySQL 端口
  - `MYSQL_USER` - MySQL 用户
  - `MYSQL_PASSWORD` - MySQL 密码
  - `MYSQL_DATABASE` - MySQL 数据库名
  - `ENABLE_AUTH` - 是否启用 API 认证
  - `API_KEY` - API 密钥
  - `CORS_ORIGINS` - CORS 允许的来源

#### 1.3 `Dockerfile`
- **基础镜像**: `python:3.13-slim`
- **多阶段构建**: 
  - 阶段 1: 安装系统依赖（Playwright 浏览器）
  - 阶段 2: 安装 Python 依赖
  - 阶段 3: 运行应用
- **端口**: `8000`
- **健康检查**: `GET /health`

#### 1.4 `docker-compose.yml`
- **服务**:
  - `api` - FastAPI 应用
  - `mysql` - MySQL 数据库（可选）
  - `redis` - Redis 缓存（可选）
- **卷**: 
  - `./data:/app/data`
  - `./outputs:/app/outputs`
  - `./config:/app/config`

---

### Phase 2: CI/CD 与文档（P0-P1）

#### 2.1 GitHub Actions CI/CD
- **工作流文件**: `.github/workflows/ci.yml`
- **触发条件**: 
  - Push 到 `main` 分支
  - Pull Request 到 `main` 分支
- **步骤**:
  1. 代码检查（Ruff/Flake8）
  2. 单元测试（`pytest`）
  3. 覆盖率检查（`pytest-cov`，阈值 40%）
  4. 依赖漏洞扫描（`pip-audit`）
  5. Docker 镜像构建（可选）
  6. 自动部署到生产环境（可选）

#### 2.2 API 文档（OpenAPI）
- **自动生成**: FastAPI 自带 Swagger UI（`/docs`）和 ReDoc（`/redoc`）
- **补充**: 
  - 添加详细的接口描述
  - 添加请求/响应示例
  - 添加错误码说明
- **导出**: 生成 `openapi.json` 供前端使用

#### 2.3 健康检查端点
- **端点**: `GET /health`
- **返回**:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "database": "connected",  // or "disconnected"
    "timestamp": "2026-06-26T12:00:00Z"
  }
  ```

---

### Phase 3: 日志与安全（P1-P2）

#### 3.1 结构化日志配置
- **格式**: JSON（便于日志收集系统解析）
- **工具**: `python-json-logger`
- **配置**:
  - 开发环境: 人类可读格式
  - 生产环境: JSON 格式
- **字段**:
  - `timestamp` - 时间戳
  - `level` - 日志级别
  - `message` - 日志消息
  - `module` - 模块名
  - `function` - 函数名
  - `line` - 行号

#### 3.2 依赖漏洞扫描
- **工具**: `pip-audit` 或 `safety`
- **集成**: GitHub Actions CI/CD
- **策略**: 
  - 发现高危漏洞 → 阻断 CI
  - 发现中低危漏洞 → 警告，不阻断

#### 3.3 `CONTRIBUTING.md`
- **内容**:
  - 如何运行项目
  - 如何运行测试
  - 代码规范（Ruff）
  - 提交规范（Conventional Commits）
  - Pull Request 流程

---

## 三、文件结构（补充后）

```
video-to-action/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI/CD
├── api/
│   ├── main.py                # FastAPI 应用（已存在）
│   └── task_manager.py       # 任务管理器（已存在）
├── config/
│   ├── settings.yaml         # 配置文件（已存在）
│   └── bilibili_cookies.json # B站 Cookie（已存在）
├── data/
│   └── knowledge_base.db    # SQLite 数据库（已存在）
├── outputs/
│   └── ...                 # 输出文件（已存在）
├── tests/
│   └── ...                 # 测试文件（已存在）
├── video_to_action/
│   ├── __init__.py
│   ├── analyzer_v2.py       # 分析器（已存在）
│   ├── cli.py               # CLI（已存在）
│   ├── config.py             # 配置管理（已存在）
│   ├── extractor.py         # 提取器（已存在）
│   ├── knowledge_base.py     # 知识库（已存在）
│   └── ...                 # 其他模块（已存在）
├── .env.example             # 环境变量示例（新增）
├── .gitignore               # Git 忽略文件（已存在？）
├── CHANGELOG.md             # 版本变更记录（新增）
├── CONTRIBUTING.md          # 贡献指南（新增）
├── Dockerfile                # Docker 镜像（新增）
├── docker-compose.yml       # Docker Compose（新增）
├── LICENSE                  # 开源协议（新增？）
├── pyproject.toml           # 项目配置（已存在）
├── README.md                # 项目介绍（已存在）
└── requirements.txt         # 依赖清单（已存在）
```

---

## 四、执行顺序

1. **Phase 1** (P0): 项目基础
   - 创建 `CHANGELOG.md`
   - 创建 `.env.example`
   - 创建 `Dockerfile`
   - 创建 `docker-compose.yml`

2. **Phase 2** (P0-P1): CI/CD 与文档
   - 创建 `.github/workflows/ci.yml`
   - 补充 API 文档（OpenAPI）
   - 添加健康检查端点

3. **Phase 3** (P1-P2): 日志与安全
   - 配置结构化日志
   - 添加依赖漏洞扫描
   - 创建 `CONTRIBUTING.md`

---

## 五、验收标准

### 5.1 `CHANGELOG.md`
- ✅ 包含项目版本变更历史
- ✅ 格式符合 [Keep a Changelog](https://keepachangelog.com/zh-CN/)

### 5.2 `.env.example`
- ✅ 包含所有必需的环境变量
- ✅ 有详细的注释说明

### 5.3 `Dockerfile`
- ✅ 能够成功构建 Docker 镜像
- ✅ 能够成功运行容器
- ✅ 健康检查正常工作

### 5.4 `docker-compose.yml`
- ✅ 能够成功启动所有服务
- ✅ 数据持久化正常工作

### 5.5 GitHub Actions CI/CD
- ✅ Push 到 `main` 分支时自动运行
- ✅ 所有检查通过后才能合并 PR

### 5.6 API 文档
- ✅ 访问 `/docs` 能看到 Swagger UI
- ✅ 访问 `/redoc` 能看到 ReDoc
- ✅ 访问 `/openapi.json` 能下载 OpenAPI 规范

### 5.7 健康检查端点
- ✅ `GET /health` 返回 200 状态码
- ✅ 返回 JSON 格式的健康状态

### 5.8 结构化日志
- ✅ 开发环境输出人类可读格式
- ✅ 生产环境输出 JSON 格式

### 5.9 `CONTRIBUTING.md`
- ✅ 包含完整的贡献指南

### 5.10 依赖漏洞扫描
- ✅ CI/CD 中自动运行
- ✅ 发现高危漏洞时阻断 CI

---

## 六、风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| Docker 镜像构建失败 | 高 | 中 | 先在本地测试构建 |
| GitHub Actions 配置错误 | 中 | 低 | 参考官方文档和示例 |
| 健康检查端点影响性能 | 低 | 低 | 使用轻量级检查逻辑 |
| 结构化日志配置复杂 | 中 | 中 | 使用成熟的第三方库 |

---

## 七、时间估算

| Phase | 预计时间 | 说明 |
|--------|----------|------|
| Phase 1 | 30 分钟 | 创建配置文件和 Docker 相关文件 |
| Phase 2 | 45 分钟 | 配置 CI/CD 和补充文档 |
| Phase 3 | 30 分钟 | 配置日志和安全扫描 |
| **总计** | **~2 小时** | 不含调试时间 |

---

## 八、后续优化建议

1. **添加监控告警** - 使用 Prometheus + Grafana
2. **添加性能测试** - 使用 Locust 或 wrk
3. **添加 E2E 测试** - 使用 Playwright 或 Selenium
4. **优化 Docker 镜像大小** - 使用多阶段构建
5. **添加数据库迁移工具** - 使用 Alembic（如果切换到 ORM）

---

## 九、结论

本方案将补充项目缺失的核心组件，使其达到生产级项目标准。执行完成后，项目将具备：

1. ✅ 完整的项目基础和文档
2. ✅ 自动化 CI/CD 流程
3. ✅ 容器化部署能力
4. ✅ 基本的安全和保护措施

**建议**: 先执行 Phase 1 和 Phase 2，快速提升项目完整性；Phase 3 可以根据实际需求逐步补充。

---

*方案版本: v1.0*  
*创建时间: 2026-06-26*  
*预计执行时间: ~2 小时*
