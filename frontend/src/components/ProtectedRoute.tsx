import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import type { UserRole } from '../types/auth';

/**
 * 受保护路由组件 Props
 */
interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: UserRole;  // 可选，检查用户角色
}

/**
 * 受保护的路由组件
 * - 未登录用户重定向到 /login
 * - 登录后跳转回原页面（使用 location.state.from）
 * - 支持角色检查（如 admin 才能访问管理页面）
 * - 添加 Loading 状态（Token 验证中）
 */
export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  // 显示加载状态
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  // 未认证，重定向到登录页
  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    );
  }

  // 检查角色权限
  if (requiredRole && user?.role !== requiredRole) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="mb-4">
            <svg
              className="mx-auto h-12 w-12 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-18L18.364 4.64c-.866-1.5-3.032-1.5-3.898 0L10.832 14.36c-.866 1.5-.068 3.36 1.732 3.36z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">权限不足</h3>
          <p className="text-gray-600 mb-4">
            您没有权限访问此页面。此页面仅对 {requiredRole === 'admin' ? '管理员' : '用户'} 开放。
          </p>
          <a
            href="/"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            返回首页
          </a>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
