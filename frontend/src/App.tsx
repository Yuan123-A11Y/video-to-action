import React, { Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import PublicRoute from './components/PublicRoute';

// 使用 React.lazy() 实现路由级代码分割（懒加载）
const HomePage = React.lazy(() => import('./pages/HomePage'));
const VideoListPage = React.lazy(() => import('./pages/VideoListPage'));
const VideoDetailPage = React.lazy(() => import('./pages/VideoDetailPage'));
const KnowledgePage = React.lazy(() => import('./pages/KnowledgePage'));
const BatchPage = React.lazy(() => import('./pages/BatchPage'));
const SettingsPage = React.lazy(() => import('./pages/SettingsPage'));
const LoginPage = React.lazy(() => import('./pages/LoginPage'));
const RegisterPage = React.lazy(() => import('./pages/RegisterPage'));
const ProfilePage = React.lazy(() => import('./pages/ProfilePage'));
const NotFoundPage = React.lazy(() => import('./pages/NotFoundPage'));

// 加载指示器组件
function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">加载中...</p>
      </div>
    </div>
  );
}

/**
 * 应用主组件
 * 注意：此组件必须在 AuthProvider 内使用
 */
function AppContent() {
  return (
    <Routes>
      {/* 公共路由（未登录用户可访问） */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Suspense fallback={<LoadingFallback />}>
              <LoginPage />
            </Suspense>
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <Suspense fallback={<LoadingFallback />}>
              <RegisterPage />
            </Suspense>
          </PublicRoute>
        }
      />

      {/* 受保护的路由（需要登录） */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout>
              <Suspense fallback={<LoadingFallback />}>
                <HomePage />
              </Suspense>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/videos"
        element={
          <ProtectedRoute>
            <Layout>
              <Suspense fallback={<LoadingFallback />}>
                <VideoListPage />
              </Suspense>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/videos/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <Suspense fallback={<LoadingFallback />}>
                <VideoDetailPage />
              </Suspense>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/knowledge"
        element={
          <ProtectedRoute>
            <Layout>
              <Suspense fallback={<LoadingFallback />}>
                <KnowledgePage />
              </Suspense>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/batch"
        element={
          <ProtectedRoute>
            <Layout>
              <Suspense fallback={<LoadingFallback />}>
                <BatchPage />
              </Suspense>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Layout>
              <Suspense fallback={<LoadingFallback />}>
                <SettingsPage />
              </Suspense>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Layout>
              <Suspense fallback={<LoadingFallback />}>
                <ProfilePage />
              </Suspense>
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* 管理员路由（需要 admin 角色） */}
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute requiredRole="admin">
            <Layout>
              <Suspense fallback={<LoadingFallback />}>
                <div className="p-6">
                  <h1 className="text-2xl font-bold text-gray-900">管理后台</h1>
                  <p className="mt-2 text-gray-600">此页面仅管理员可访问</p>
                </div>
              </Suspense>
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* 404 页面 */}
      <Route
        path="*"
        element={
          <Suspense fallback={<LoadingFallback />}>
            <NotFoundPage />
          </Suspense>
        }
      />
    </Routes>
  );
}

/**
 * 应用根组件
 * 包裹 AuthProvider 以提供认证上下文
 */
export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
