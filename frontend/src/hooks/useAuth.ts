import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import type { AuthContextType } from '../types/auth';

/**
 * 自定义 Hook：获取认证上下文
 *
 * @returns {AuthContextType} 认证上下文
 * @throws {Error} 如果不在 AuthProvider 内使用
 *
 * @example
 * // 在组件中使用
 * const { user, isAuthenticated, login, logout } = useAuth();
 *
 * if (isAuthenticated) {
 *   return <div>欢迎，{user?.username}！</div>;
 * }
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider. Please wrap your component with <AuthProvider>.');
  }

  return context;
};

export default useAuth;
