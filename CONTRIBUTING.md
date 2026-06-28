# Contributing to Video-to-Action

感谢你对 Video-to-Action 项目的关注！

## 开发环境设置

1. Fork 本仓库
2. Clone 到本地：`git clone https://github.com/yourusername/video-to-action.git`
3. 创建虚拟环境：`python -m venv .venv`
4. 激活虚拟环境：
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
5. 安装依赖：`pip install -r requirements.txt`
6. 安装开发依赖：`pip install ruff pytest pytest-cov`
7. 复制环境变量：`cp .env.example .env`，并填写实际值

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行测试并检查覆盖率
pytest tests/ -v --cov=video_to_action --cov-report=term-missing

# 代码检查
ruff check .

# 代码格式化检查
ruff format --check .
```

## 提交规范

本项目遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 规范：

```
feat: 添加新功能
fix: 修复 Bug
docs: 文档更新
style: 代码格式调整（不影响功能）
refactor: 重构（既不是新功能也不是修复）
test: 添加测试
chore: 构建过程或辅助工具变动
```

示例：
```
feat: 添加 B站视频下载支持
fix: 修复 Whisper 模型缓存内存泄漏
docs: 更新 API 文档
```

## Pull Request 流程

1. 创建功能分支：`git checkout -b feat/my-feature`
2. 提交变更：`git commit -m "feat: 添加新功能"`
3. 推送到 Fork：`git push origin feat/my-feature`
4. 创建 Pull Request 到主仓库的 `main` 分支
5. 等待 CI 检查通过和代码审查

## 代码规范

- 使用 `ruff` 进行代码检查
- 遵循 PEP 8 规范
- 所有公共函数/类都需要添加 docstring
- 测试覆盖率保持在 40% 以上

## 问题反馈

- 发现问题？请创建 [Issue](https://github.com/yourusername/video-to-action/issues)
- 有功能建议？也请创建 Issue，并添加 `enhancement` 标签

感谢你的贡献！
