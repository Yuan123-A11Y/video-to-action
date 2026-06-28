# P2 用户认证系统 - 测试环境设置指南

## 测试概要

- **测试时间**: 2026-01-15
- **测试人员**: 严过关（QA工程师）
- **测试范围**: 后端API + 前端集成
- **测试轮次**: Round 1（发现问题并报告）

---

## 环境要求

### 后端测试
- Python 3.13+
- pytest 9.1+
- httpx (FastAPI TestClient依赖）
- 项目依赖：`pip install -e ".[dev]"` 或 `poetry install`

### 前端测试
- Node.js 18+
- npm 或 yarn
- Vitest（已配置）
- @testing-library/react（已安装）
- jsdom（已安装）

---

## 后端测试设置

### 1. 安装依赖
```bash
cd G:\trae\video-to-action
pip install -e ".[dev]"
# 或
poetry install
```

### 2. 设置环境变量（测试文件自动设置）
测试文件 `tests/test_auth_api.py` 会自动设置：
```python
os.environ["ENABLE_AUTH"] = "true"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
```

### 3. 运行测试
```bash
# 运行所有后端API测试
python -m pytest tests/test_auth_api.py -v

# 运行特定测试类
python -m pytest tests/test_auth_api.py::TestUserRegister -v

# 运行单个测试
python -m pytest tests/test_auth_api.py::TestUserRegister::test_register_success -v
```

### 4. 测试覆盖
- ✅ 15/18 测试通过（83.3%）
- ⏳ 3个测试跳过（源码Bug BUG-001）
- 🎯 修复Bug后目标：18/18 通过（100%）

---

## 前端测试设置

### 1. 安装依赖（已完成）
```bash
cd G:\trae\video-to-action\frontend
npm install
# 测试依赖已安装：
# - vitest ^4.1.9
# - @testing-library/react ^16.3.2
# - @testing-library/jest-dom ^6.9.1
# - jsdom ^29.1.1
```

### 2. 运行测试
```bash
# 运行所有前端测试
cd G:\trae\video-to-action\frontend
npm test

# 运行并查看UI（可选）
npm run test:ui
```

### 3. 测试覆盖
- ✅ 9/9 测试通过（100%）
- 覆盖功能：
  - LoginPage 渲染和交互
  - RegisterPage 渲染
  - AuthProvider 状态管理（localStorage）
  - ProtectedRoute 路由保护
  - PublicRoute 路由重定向

---

## 已知问题

### 🐛 BUG-001：登录API调用不存在的方法
- **位置**: `api/auth/router.py` 第108行
- **问题**: 调用 `service.get_current_user_by_username(user_login.username)`
- **错误**: `AttributeError: 'AuthService' object has no attribute 'get_current_user_by_username'`
- **影响**: 登录API（`/api/auth/login`）无法正常工作
- **状态**: ⏳ 等待工程师（寇豆码）修复
- **建议修复**: 在 `AuthService` 中添加 `get_user_by_username(username)` 方法

### ⚠️ 警告（非关键）
1. **Pydantic V2 弃用警告**: `dict` 方法已弃用，应使用 `model_dump()`
2. **JWT密钥长度不足**: HMAC密钥仅27字节，SHA256推荐至少32字节
3. **Starlette TestClient 弃用警告**: 应使用 `httpx2`

---

## 测试文件位置

### 后端测试
- **文件**: `tests/test_auth_api.py`
- **测试类**:
  - `TestUserRegister` (7 tests) ✅
  - `TestTokenRefresh` (2 tests) ✅
  - `TestGetCurrentUser` (3 tests) ✅
  - `TestChangePassword` (2 tests) ✅
  - `TestUserLogin` (3 tests) ⏳ 跳过（Bug）
  - `TestLogout` (1 test) ✅

### 前端测试
- **文件**: `frontend/src/__tests__/auth_integration.test.tsx`
- **测试套件**:
  - `LoginPage` (3 tests) ✅
  - `RegisterPage` (1 test) ✅
  - `AuthProvider` (3 tests) ✅
  - `ProtectedRoute` (1 test) ✅
  - `PublicRoute` (1 test) ✅

---

## Round 2 计划（回归验证）

### 等待中
- 工程师修复 BUG-001
- 提交修复后的代码

### Bug修复后行动
1. ✅ 重新运行后端API测试（验证修复）
2. ✅ 验证所有18个测试通过（目标100%通过率）
3. ✅ 进行手动端到端测试（可选）
4. ✅ 生成最终测试报告

---

## 手动测试场景（可选）

### 场景1：用户注册流程
1. 访问 http://localhost:3000/register
2. 填写注册表单
3. 提交
4. 验证：跳转到登录页，显示成功消息

### 场景2：用户登录流程
1. 访问 http://localhost:3000/login
2. 填写登录表单
3. 提交
4. 验证：跳转到首页，用户菜单显示用户名

### 场景3：Token过期处理
1. 登录后，修改localStorage中的Token（改为过期Token）
2. 刷新页面
3. 验证：自动跳转到登录页

### 场景4：路由保护
1. 未登录状态下，访问 http://localhost:3000/
2. 验证：重定向到 /login

### 场景5：受保护API调用
1. 登录后，调用受保护API（如 DELETE /api/videos/1）
2. 验证：请求包含Authorization Header，返回200

---

## 联系人

- **QA工程师**: 严过关（software-qa-engineer）
- **团队负责人**: team-lead
- **工程师**: 寇豆码

---

**最后更新**: 2026-01-15
**状态**: Round 1 完成，等待Bug修复
