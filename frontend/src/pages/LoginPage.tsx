import { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '../hooks/useAuth';
import { Zap, Eye, EyeOff, AlertCircle, CircleCheck, Loader2 } from 'lucide-react';

/**
 * 登录表单验证 Schema
 */
const loginSchema = z.object({
  username: z.string()
    .min(3, '用户名至少3个字符')
    .max(50, '用户名最多50个字符'),
  password: z.string()
    .min(6, '密码至少6个字符'),
  remember_me: z.boolean(),
});

type LoginFormData = z.infer<typeof loginSchema>;

/**
 * 登录页面组件 — 统一品牌设计语言
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, error, clearError } = useAuth();

  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [loginSuccess, setLoginSuccess] = useState<boolean>(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isSubmitting },
    trigger,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: 'onTouched',
    reValidateMode: 'onChange',
    defaultValues: {
      username: '',
      password: '',
      remember_me: false,
    },
  });

  // 清除错误当组件卸载时
  useEffect(() => {
    return () => {
      clearError();
    };
  }, [clearError]);

  /**
   * 处理表单提交
   */
  const onSubmit = async (data: LoginFormData) => {
    if (isSubmitting) return; // 防止重复提交

    clearError();
    setLoginSuccess(false);

    try {
      await login(data.username, data.password);
      setLoginSuccess(true);

      // 登录成功，跳转到之前尝试访问的页面或首页
      const from = (location.state as any)?.from || '/';
      setTimeout(() => {
        navigate(from, { replace: true });
      }, 500);
    } catch (error) {
      console.error('Login failed:', error);
      trigger(); // 触发字段验证以显示错误状态
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-app)] py-12 px-4 sm:px-6 lg:px-8">
      {/* 背景装饰 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-[var(--color-primary)]/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-[var(--color-primary)]/3 rounded-full blur-3xl" />
      </div>

      <div className="max-w-md w-full space-y-8 relative">
        {/* 标题区 */}
        <div className="text-center">
          {/* Logo */}
          <div className="mx-auto h-14 w-14 flex items-center justify-center rounded-2xl bg-[var(--color-primary-soft)] shadow-[var(--shadow-md)] mb-5">
            <Zap size={28} className="text-[var(--color-primary)]" />
          </div>
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)] tracking-tight">
            Video-to-Action
          </h1>
          <p className="mt-2 text-[var(--color-text-secondary)] text-sm">
            登录您的账户，开始智能视频分析
          </p>
        </div>

        {/* 成功提示 */}
        {loginSuccess && (
          <div className="rounded-xl bg-[var(--color-success-soft)] border border-[var(--color-success)]/20 p-4 animate-fade-in">
            <div className="flex items-center gap-3">
              <CircleCheck size={20} className="text-[var(--color-success)] shrink-0" />
              <p className="text-sm font-medium text-[var(--color-success)]">
                登录成功！正在跳转...
              </p>
            </div>
          </div>
        )}

        {/* 登录表单卡片 */}
        <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-xl)] border border-[var(--color-border-subtle)] shadow-[var(--shadow-lg)] p-8">
          <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
            {/* 用户名输入框 */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">
                用户名
              </label>
              <div className="relative">
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  {...register('username')}
                  className={`w-full px-4 py-2.5 rounded-[var(--radius-sm)] border text-sm transition-all outline-none ${
                    errors.username
                      ? 'border-[var(--color-error)] focus:border-[var(--color-error)] focus:shadow-[0_0_0_3px_rgba(220,38,38,0.15)] bg-[var(--color-error-soft)]/30'
                      : 'border-[var(--color-border-default)] bg-[var(--color-bg-surface)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] hover:border-[var(--color-border-strong)]'
                  } placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)]`}
                  placeholder="请输入用户名"
                  disabled={isLoading}
                />
                {errors.username && (
                  <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                    <AlertCircle size={12} />
                    {errors.username.message}
                  </p>
                )}
              </div>
            </div>

            {/* 密码输入框 */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">
                密码
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  {...register('password')}
                  className={`w-full px-4 py-2.5 rounded-[var(--radius-sm)] border text-sm transition-all outline-none pr-12 ${
                    errors.password
                      ? 'border-[var(--color-error)] focus:border-[var(--color-error)] focus:shadow-[0_0_0_3px_rgba(220,38,38,0.15)] bg-[var(--color-error-soft)]/30'
                      : 'border-[var(--color-border-default)] bg-[var(--color-bg-surface)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] hover:border-[var(--color-border-strong)]'
                  } placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)]`}
                  placeholder="请输入密码"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] transition-colors"
                  disabled={isLoading}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
                {errors.password && (
                  <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                    <AlertCircle size={12} />
                    {errors.password.message}
                  </p>
                )}
              </div>
            </div>

            {/* 记住我和忘记密码 */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  {...register('remember_me')}
                  className="h-4 w-4 rounded border-[var(--color-border-default)] text-[var(--color-primary)] focus:ring-[var(--color-primary)] focus:ring-offset-0 accent-[var(--color-primary)]"
                  disabled={isLoading}
                />
                <span className="text-sm text-[var(--color-text-secondary)] select-none">记住我</span>
              </label>
              <button
                type="button"
                onClick={() => alert('忘记密码功能正在开发中，请联系管理员重置密码。')}
                className="text-sm text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] transition-colors font-medium"
              >
                忘记密码？
              </button>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="rounded-lg bg-[var(--color-error-soft)] border border-[var(--color-error)]/20 p-3 animate-shake">
                <div className="flex items-center gap-2">
                  <AlertCircle size={16} className="text-[var(--color-error)] shrink-0" />
                  <p className="text-sm text-[var(--color-error)]">{error}</p>
                </div>
              </div>
            )}

            {/* 提交按钮 */}
            <button
              type="submit"
              disabled={isLoading || isSubmitting}
              className={`w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-[var(--radius-sm)] text-sm font-medium text-white transition-all ${
                isLoading || isSubmitting
                  ? 'bg-[var(--color-primary-disabled)] cursor-not-allowed'
                  : 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] active:bg-[var(--color-primary-active)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)]'
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  登录中...
                </>
              ) : (
                '登录'
              )}
            </button>
          </form>

          {/* 注册链接 */}
          <p className="mt-6 text-center text-sm text-[var(--color-text-secondary)]">
            还没有账户？{' '}
            <Link
              to="/register"
              className="font-medium text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] transition-colors"
            >
              注册新账户
            </Link>
          </p>
        </div>

        {/* 社交登录（占位） */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[var(--color-border-subtle)]" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="bg-[var(--color-bg-app)] px-3 text-[var(--color-text-tertiary)]">
              其他登录方式
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            disabled
            className="flex justify-center items-center gap-2 py-2.5 px-4 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface)] text-sm text-[var(--color-text-disabled)] cursor-not-allowed"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.111.793.793.277 1.606.097 2.126.638 6.627 2.373 12.146 6.627 12.146 0 1.794.089 2.812.647 3.006.453-.317.527-.837.966-1.502 1.228-.625.341-1.004.558-1.036.558-.002.002-.404 1.202.757 1.202.552 0 1.127-.16 1.805-.538 2.091-.538.96 1.22 1.168 1.987.118-.199-.148-1.575-.27-2.988-.303-1.412-.033-2.909.405-3.591 1.155-.685.723-1.613 1.155-2.575 1.155-.97 0-1.842-.438-2.575-1.155-.682-.77-1.77-1.155-3.192-1.155-1.062 0-1.86.378-2.391 1.003-.531.626-.843 1.418-.843 2.248 0 .829.291 1.633.862 2.193 1.155zm-6.548 8.443c-.84 0-1.545.659-1.545 1.476 0 .816.705 1.476 1.545 1.476.84 0 1.545-.66 1.545-1.476 0-.817-.705-1.476-1.545-1.476zm12.609 0c-.84 0-1.545.659-1.545 1.476 0 .816.704 1.476 1.545 1.476.84 0 1.544-.66 1.544-1.476 0-.817-.704-1.476-1.544-1.476z"/>
            </svg>
            GitHub
          </button>
          <button
            type="button"
            disabled
            className="flex justify-center items-center gap-2 py-2.5 px-4 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface)] text-sm text-[var(--color-text-disabled)] cursor-not-allowed"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.12H12.48z"/>
            </svg>
            Google
          </button>
        </div>
        <p className="text-center text-xs text-[var(--color-text-tertiary)]">
          社交登录功能即将推出
        </p>
      </div>
    </div>
  );
}
