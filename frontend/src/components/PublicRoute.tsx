import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

/**
 * 公共路由组件 Props
 */
interface PublicRouteProps {
  children: ReactNode;
  redirectPath?: string;  // 可选，自定义重定向路径，默认是 '/'
}

/**
 * 公共路由组件
 * - 已登录用户重定向到首页（或其他自定义路径）
 * - 支持自定义重定向路径
 * - 添加 Loading 状态
 */
export default function PublicRoute({ children, redirectPath = '/' }: PublicRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
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

  // 已认证，重定向到指定路径
  // 如果 location.state.from 存在，则重定向到该路径（用户之前尝试访问的页面）
  if (isAuthenticated) {
    const from = (location.state as any)?.from || redirectPath;
    return <Navigate to={from} replace />;
  }

  return <>{children}</>;
}
