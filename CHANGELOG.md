# Changelog

本文档记录了 Video-to-Action 项目的所有 notable changes。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 添加 CHANGELOG.md

### Fixed
- 修复 `knowledge_base.py` 中 `updated_at` 列缺失问题（自动迁移）
- 修复 `analyzer_v2.py` 中 `analyze_with_llm()` 调用不存在的方法
- 修复 `api/main.py` 中 CORS 配置过于宽松
- 修复 `api/main.py` 中敏感信息泄露到前端
- 修复 `api/main.py` 中应用启动依赖性问题（添加懒加载 + MySQL → SQLite 降级）
- 修复 `api/main.py` 中缺少认证/授权机制（添加可选的 API Key 认证）

### Security
- 改进 CORS 配置（从环境变量读取允许的来源）
- 改进错误处理（记录详细错误到日志，返回通用错误给前端）
- 添加可选的 API Key 认证（通过 `ENABLE_AUTH` 环境变量控制）

## [0.1.0] - 2026-06-25

### Added
- 初始版本
- 支持 B站、抖音、YouTube 视频下载
- 支持 Whisper 转录
- 支持 LLM 分析（OpenAI 兼容接口）
- 支持 SQLite/MySQL 知识库
- 支持 FastAPI Web API
- 支持 CLI 命令行界面

[Unreleased]: https://github.com/yourusername/video-to-action/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/video-to-action/releases/tag/v0.1.0
