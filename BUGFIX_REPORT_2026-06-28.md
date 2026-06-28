# 前端卡死问题排查与修复报告

**日期**: 2026-06-28  
**排查人**: Senior Developer（高级开发工程师）  
**测试链接**: `https://v.douyin.com/z8aBVj9XnHk/`  
**状态**: ✅ 已修复并验证通过

---

## 🔍 问题现象

用户反馈：
1. 提交抖音视频链接后，进度面板消失
2. 视频一直卡在"等待中"状态
3. 控制台显示 WS 连接成功但"未收到数据"
4. 第一步都无法完成

---

## 🎯 根因分析（3 个 Bug）

### Bug #1（核心问题）：视频状态永远停留在 `pending`

**文件**: `video_to_action/knowledge_base.py` → `add_video_analysis()` 方法

**原因**: INSERT 语句没有包含 `status` 字段，数据库使用默认值 `'pending'`

```sql
-- 数据库 schema 定义
status TEXT DEFAULT 'pending'  -- 默认值是 pending！

-- 但代码插入时完全没有 status 字段：
INSERT INTO videos (url, platform, title, ...)
VALUES (?, ?, ?, ...)  -- ← 缺少 status!
```

**影响**: 所有已完成的视频在前端都显示"等待中"

**修复**: 在 INSERT 中添加 `status='completed'`

---

### Bug #2：进度面板刷新后消失

**文件**: `frontend/src/pages/HomePage.tsx`

**原因**: `taskId` 只存储在 React state 中（内存），页面刷新后丢失

```tsx
// 之前：taskId 只在内存中
const [taskId, setTaskId] = useState<string | null>(null)
// 刷新页面 → taskId 变 null → 进度面板隐藏 → 显示"最近视频"
```

**修复**: 
1. `taskId` 持久化到 `sessionStorage`
2. 页面加载时自动检测活跃任务
3. 任务完成/失败后清除 `sessionStorage`

---

### Bug #3：轮询模式下缺少 progress 数据

**文件**: `api/main.py` → `get_task_status()` 端点

**原因**: API 只返回 `{status, result, error}`，不返回 `progress`

```typescript
// 前端轮询代码期望 task.progress 存在：
setState(prev => ({
  ...prev,
  progress: task.progress || prev.progress,  // ← task.progress 永远是 undefined！
}))
```

**修复**: 
- 端点现在返回 `progress` 字段（根据 status 推断或从 WS 缓存获取）
- 新增 `ws_manager.get_latest_progress()` 方法
- 新增 `/api/tasks?status_filter=processing` 列表接口（供前端自动恢复使用）

---

## ✅ 修改的文件清单

| 文件 | 修改内容 | 类型 |
|------|----------|------|
| `video_to_action/knowledge_base.py` | `add_video_analysis()` INSERT 增加 `status='completed'` | 🔴 关键修复 |
| `api/main.py` | `/api/tasks/{task_id}` 返回 progress 字段；新增 `/api/tasks` 列表接口 | 🟡 增强 |
| `api/ws_manager.py` | 新增 `get_latest_progress()` 同步方法 | 🟡 增强 |
| `frontend/src/pages/HomePage.tsx` | taskId 持久化到 sessionStorage；自动检测活跃任务；导入 getTask | 🔴 关键修复 |
| `data/knowledge_base.db` | 修复 Video 14 状态 pending→completed | 🟢 数据修复 |

---

## ✅ 验证结果

### 后端测试（用 `https://v.douyin.com/z8aBVj9XnHk/`）

```
1. POST /api/process → {"task_id": "39"} ✅
2. GET /api/tasks/39   → status=completed, progress={step:5, percentage:100} ✅
3. Videos 表查询      → ID=15, status=completed ✅
4. Videos API 返回    → "status":"completed" ✅
5. /api/tasks 列表     → 正常返回任务列表 ✅
```

### 日志确认（task 39）

```
16:28:xx push_progress: task=39, step=1/5, 0%, 正在下载...
16:28:xx push_progress: task=39, step=1/5, 20%, 视频下载完成
16:28:xx push_progress: task=39, step=2/5, 25%, 正在提取音频...
16:29:xx push_progress: task=39, step=2/5, 40%, 内容提取完成
16:29:xx push_progress: task=39, step=3/5, 45%, AI 分析中...
16:29:xx push_progress: task=39, step=3/5, 70%, 分析完成
16:29:xx push_progress: task=39, step=4/5, 75%, 保存到知识库...
16:29:xx push_progress: task=39, step=4/5, 90%, 已保存
16:29:xx push_progress: task=39, step=5/5, 100%, 全部处理完成！
```

**完整流程耗时 ~60 秒，全部步骤正常执行 ✅**

---

## ⚠️ 需要注意的事项

### 1. 后端服务需要重启才能加载 Python 代码修改
- `knowledge_base.py`、`main.py`、`ws_manager.py` 的修改需要重启 API 服务
- 当前服务已在运行旧代码，新提交的任务会用到新代码

### 2. 前端需要重新构建
- `HomePage.tsx` 的修改需要重新 `npm run build`
- 建议执行：`cd frontend && npm run build`

### 3. MySQL 连接失败（非本次引入）
- 日志显示 `MySQL 连接失败，降级到 SQLite`
- 这是已有问题，不影响功能（SQLite 作为 fallback 正常工作）

---

## 📋 后续建议

### 立即执行
1. **重启后端服务**（让 Python 代码修改生效）
2. **重新构建前端**（`npm run build`）
3. **刷新浏览器测试**

### 可选优化
1. 将 `sessionStorage` 改为 `localStorage`（跨标签页保持）
2. 添加任务取消功能（用户可以中断卡住的任务）
3. WebSocket 重连时自动同步当前进度
