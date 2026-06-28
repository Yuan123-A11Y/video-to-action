import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '../hooks/useAuth';
import { Zap, Eye, EyeOff, AlertCircle, CircleCheck, Loader2 } from 'lucide-react';

/**
 * 注册表单验证 Schema
 */
const registerSchema = z.object({
  username: z.string()
    .min(3, '用户名至少3个字符')
    .max(50, '用户名最多50个字符')
    .regex(/^[a-zA-Z0-9_]+$/, '用户名只能包含字母、数字和下划线'),
  email: z.string()
    .email('请输入有效的邮箱地址'),
  password: z.string()
    .min(6, '密码至少6个字符')
    .regex(/^(?=.*[A-Za-z])(?=.*\d)/, '密码必须包含字母和数字'),
  confirm_password: z.string(),
}).refine((data) => data.password === data.confirm_password, {
  message: '两次输入的密码不一致',
  path: ['confirm_password'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

/**
 * 注册页面组件 — 统一品牌设计语言
 */
export default function RegisterPage() {
  const navigate = useNavigate();
  const { register: registerUser, isLoading, error, clearError } = useAuth();

  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [registerSuccess, setRegisterSuccess] = useState<boolean>(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    mode: 'onBlur',
    defaultValues: {
      username: '',
      email: '',
      password: '',
      confirm_password: '',
    },
  });

  const password = watch('password');

  // 清除错误当组件卸载时
  useEffect(() => {
    return () => {
      clearError();
    };
  }, [clearError]);

  /**
   * 检查密码强度
   */
  const getPasswordStrength = (password: string): { strength: number; label: string; color: string; bgColor: string } => {
    if (!password) return { strength: 0, label: '', color: '', bgColor: '' };

    let score = 0;
    if (password.length >= 6) score++;
    if (password.length >= 10) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[a-z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    if (score <= 2) return { strength: 1, label: '弱', color: 'bg-red-500', bgColor: 'bg-red-50' };
    if (score <= 4) return { strength: 2, label: '中', color: 'bg-yellow-500', bgColor: 'bg-yellow-50' };
    return { strength: 3, label: '强', color: 'bg-[var(--color-success)]', bgColor: 'bg-[var(--color-success-soft)]' };
  };

  const passwordStrength = getPasswordStrength(password);

  /**
   * 处理表单提交
   */
  const onSubmit = async (data: RegisterFormData) => {
    clearError();
    setRegisterSuccess(false);

    try {
      await registerUser(data.username, data.email, data.password);
      setRegisterSuccess(true);

      // 注册成功，延迟跳转到登录页
      setTimeout(() => {
        navigate('/login', {
          state: { message: '注册成功！请登录您的账户。' },
        });
      }, 1500);
    } catch (error) {
      console.error('Registration failed:', error);
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
            创建新账户，开始智能视频分析
          </p>
        </div>

        {/* 成功提示 */}
        {registerSuccess && (
          <div className="rounded-xl bg-[var(--color-success-soft)] border border-[var(--color-success)]/20 p-4 animate-fade-in">
            <div className="flex items-center gap-3">
              <CircleCheck size={20} className="text-[var(--color-success)] shrink-0" />
              <p className="text-sm font-medium text-[var(--color-success)]">
                注册成功！正在跳转到登录页...
              </p>
            </div>
          </div>
        )}

        {/* 注册表单卡片 */}
        <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-xl)] border border-[var(--color-border-subtle)] shadow-[var(--shadow-lg)] p-8">
          <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
            {/* 用户名输入框 */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">
                用户名
              </label>
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
                placeholder="3-50字符，仅字母数字下划线"
                disabled={isLoading}
              />
              {errors.username && (
                <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                  <AlertCircle size={12} />
                  {errors.username.message}
                </p>
              )}
            </div>

            {/* 邮箱输入框 */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">
                邮箱地址
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                {...register('email')}
                className={`w-full px-4 py-2.5 rounded-[var(--radius-sm)] border text-sm transition-all outline-none ${
                  errors.email
                    ? 'border-[var(--color-error)] focus:border-[var(--color-error)] focus:shadow-[0_0_0_3px_rgba(220,38,38,0.15)] bg-[var(--color-error-soft)]/30'
                    : 'border-[var(--color-border-default)] bg-[var(--color-bg-surface)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] hover:border-[var(--color-border-strong)]'
                } placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)]`}
                placeholder="you@example.com"
                disabled={isLoading}
              />
              {errors.email && (
                <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                  <AlertCircle size={12} />
                  {errors.email.message}
                </p>
              )}
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
                  autoComplete="new-password"
                  {...register('password')}
                  className={`w-full px-4 py-2.5 rounded-[var(--radius-sm)] border text-sm transition-all outline-none pr-12 ${
                    errors.password
                      ? 'border-[var(--color-error)] focus:border-[var(--color-error)] focus:shadow-[0_0_0_3px_rgba(220,38,38,0.15)] bg-[var(--color-error-soft)]/30'
                      : 'border-[var(--color-border-default)] bg-[var(--color-bg-surface)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] hover:border-[var(--color-border-strong)]'
                  } placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)]`}
                  placeholder="至少6个字符，包含字母和数字"
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
              </div>
              {errors.password && (
                <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                  <AlertCircle size={12} />
                  {errors.password.message}
                </p>
              )}

              {/* 密码强度指示器 */}
              {password && (
                <div className="mt-2.5 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-[var(--color-bg-overlay)] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${passwordStrength.color}`}
                        style={{ width: `${(passwordStrength.strength / 3) * 100}%` }}
                      />
                    </div>
                    <span className={`text-xs font-medium ${passwordStrength.label === '强' ? 'text-[var(--color-success)]' : passwordStrength.label === '中' ? 'text-[var(--color-warning)]' : 'text-[var(--color-error)]'}`}>
                      {passwordStrength.label}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--color-text-tertiary)]">
                    规则：6+字符，含字母和数字
                  </p>
                </div>
              )}
            </div>

            {/* 确认密码输入框 */}
            <div>
              <label htmlFor="confirm_password" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">
                确认密码
              </label>
              <div className="relative">
                <input
                  id="confirm_password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  {...register('confirm_password')}
                  className={`w-full px-4 py-2.5 rounded-[var(--radius-sm)] border text-sm transition-all outline-none ${
                    errors.confirm_password
                      ? 'border-[var(--color-error)] focus:border-[var(--color-error)] focus:shadow-[0_0_0_3px_rgba(220,38,38,0.15)] bg-[var(--color-error-soft)]/30'
                      : 'border-[var(--color-border-default)] bg-[var(--color-bg-surface)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] hover:border-[var(--color-border-strong)]'
                  } placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)]`}
                  placeholder="再次输入密码"
                  disabled={isLoading}
                />
              </div>
              {errors.confirm_password && (
                <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                  <AlertCircle size={12} />
                  {errors.confirm_password.message}
                </p>
              )}
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
              disabled={isLoading || !isValid}
              className={`w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-[var(--radius-sm)] text-sm font-medium text-white transition-all ${
                isLoading || !isValid
                  ? 'bg-[var(--color-primary-disabled)] cursor-not-allowed'
                  : 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] active:bg-[var(--color-primary-active)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)]'
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  注册中...
                </>
              ) : (
                '注册账户'
              )}
            </button>
          </form>

          {/* 登录链接 */}
          <p className="mt-6 text-center text-sm text-[var(--color-text-secondary)]">
            已有账户？{' '}
            <Link
              to="/login"
              className="font-medium text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] transition-colors"
            >
              立即登录
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
