import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '../hooks/useAuth';
import { Zap, Eye, EyeOff, AlertCircle, CircleCheck, Loader2, User, Mail, KeyRound, ShieldCheck } from 'lucide-react';

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
 * 密码强度计算
 */
function getPasswordStrength(password: string): { level: number; label: string; color: string; percent: number } {
  if (!password) return { level: 0, label: '', color: '', percent: 0 };

  let score = 0;
  if (password.length >= 6) score++;
  if (password.length >= 10) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[a-z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  if (score <= 2) return { level: 1, label: '弱', color: 'var(--color-error)', percent: 33 };
  if (score <= 4) return { level: 2, label: '中', color: 'var(--color-warning)', percent: 66 };
  return { level: 3, label: '强', color: 'var(--color-success)', percent: 100 };
}

/**
 * 注册页面组件 — 统一品牌设计语言
 */
export default function RegisterPage() {
  const navigate = useNavigate();
  const { register: registerUser, isLoading, error, clearError } = useAuth();

  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [registerSuccess, setRegisterSuccess] = useState<boolean>(false);
  const submitBtnRef = useRef<HTMLButtonElement>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, touchedFields },
    watch,
    setFocus,
    trigger,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    mode: 'onTouched',
    reValidateMode: 'onChange',
    defaultValues: {
      username: '',
      email: '',
      password: '',
      confirm_password: '',
    },
  });

  const password = watch('password');
  const passwordStrength = getPasswordStrength(password);

  // 自动聚焦
  useEffect(() => {
    setFocus('username');
  }, [setFocus]);

  // 清除错误
  useEffect(() => {
    return () => { clearError(); };
  }, [clearError]);

  const onSubmit = async (data: RegisterFormData) => {
    if (isSubmitting) return;

    clearError();
    setRegisterSuccess(false);

    try {
      await registerUser(data.username, data.email, data.password);
      setRegisterSuccess(true);
      setTimeout(() => navigate('/login', {
        state: { message: '注册成功！请登录您的账户。' },
      }), 1500);
    } catch {
      submitBtnRef.current?.classList.add('animate-shake');
      setTimeout(() => submitBtnRef.current?.classList.remove('animate-shake'), 500);
    }
  };

  const fieldBaseClass =
    'w-full pl-10 pr-4 py-2.5 rounded-[var(--radius-sm)] border text-sm transition-all duration-200 outline-none ' +
    'placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)]';

  const fieldNormalClass =
    'border-[var(--color-border-default)] bg-[var(--color-bg-surface)] ' +
    'focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] ' +
    'hover:border-[var(--color-border-strong)]';

  const fieldErrorClass =
    'border-[var(--color-error)] focus:border-[var(--color-error)] ' +
    'focus:shadow-[0_0_0_3px_rgba(220,38,38,0.15)] bg-[var(--color-error-soft)]/30';

  const iconBaseClass =
    'absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none transition-colors duration-200';

  const inputIconColor = (fieldName: 'username' | 'email' | 'password' | 'confirm_password') =>
    errors[fieldName]
      ? 'text-[var(--color-error)]'
      : touchedFields[fieldName]
        ? 'text-[var(--color-primary)]'
        : 'text-[var(--color-text-tertiary)]';

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-app)] py-12 px-4 sm:px-6 lg:px-8">
      {/* 背景装饰 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-[var(--color-primary)]/5 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-[var(--color-primary)]/3 rounded-full blur-3xl animate-pulse-slower" />
      </div>

      <div className="max-w-md w-full space-y-8 relative animate-fade-in">
        {/* 标题区 */}
        <div className="text-center animate-slide-down">
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

        {/* 注册成功提示 */}
        {registerSuccess && (
          <div className="rounded-xl bg-[var(--color-success-soft)] border border-[var(--color-success)]/20 p-4 animate-slide-down">
            <div className="flex items-center gap-3">
              <CircleCheck size={20} className="text-[var(--color-success)] shrink-0" />
              <p className="text-sm font-medium text-[var(--color-success)]">
                注册成功！正在跳转到登录页...
              </p>
            </div>
          </div>
        )}

        {/* 注册表单卡片 */}
        <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-xl)] border border-[var(--color-border-subtle)] shadow-[var(--shadow-lg)] p-8 animate-scale-in">
          <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
            {/* 用户名 */}
            <div className="animate-stagger-1">
              <label htmlFor="username" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">用户名</label>
              <div className="relative">
                <User size={16} className={`${iconBaseClass} ${inputIconColor('username')}`} />
                <input
                  id="username" type="text" autoComplete="username"
                  {...register('username')}
                  className={`${fieldBaseClass} ${errors.username ? fieldErrorClass : fieldNormalClass}`}
                  placeholder="3-50字符，仅字母数字下划线"
                  disabled={isLoading}
                />
                {errors.username && (
                  <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                    <AlertCircle size={12} /> {errors.username.message}
                  </p>
                )}
              </div>
            </div>

            {/* 邮箱 */}
            <div className="animate-stagger-2">
              <label htmlFor="email" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">邮箱地址</label>
              <div className="relative">
                <Mail size={16} className={`${iconBaseClass} ${inputIconColor('email')}`} />
                <input
                  id="email" type="email" autoComplete="email"
                  {...register('email')}
                  className={`${fieldBaseClass} ${errors.email ? fieldErrorClass : fieldNormalClass}`}
                  placeholder="you@example.com"
                  disabled={isLoading}
                />
                {errors.email && (
                  <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                    <AlertCircle size={12} /> {errors.email.message}
                  </p>
                )}
              </div>
            </div>

            {/* 密码 */}
            <div className="animate-stagger-3">
              <label htmlFor="password" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">密码</label>
              <div className="relative">
                <KeyRound size={16} className={`${iconBaseClass} ${inputIconColor('password')}`} />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  {...register('password')}
                  className={`${fieldBaseClass} pr-12 ${errors.password ? fieldErrorClass : fieldNormalClass}`}
                  placeholder="至少6个字符，包含字母和数字"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] transition-colors z-10"
                  tabIndex={-1}
                  disabled={isLoading}
                  aria-label={showPassword ? '隐藏密码' : '显示密码'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
                {errors.password && (
                  <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                    <AlertCircle size={12} /> {errors.password.message}
                  </p>
                )}
              </div>

              {/* 密码强度指示器 */}
              {password && (
                <div className="mt-2.5 animate-fade-in">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-[var(--color-bg-overlay)] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500 ease-out"
                        style={{
                          width: `${passwordStrength.percent}%`,
                          backgroundColor: passwordStrength.color,
                        }}
                      />
                    </div>
                    <span
                      className="text-xs font-medium transition-colors duration-300"
                      style={{ color: passwordStrength.color }}
                    >
                      {passwordStrength.label}
                    </span>
                    {passwordStrength.level >= 3 && <ShieldCheck size={14} className="text-[var(--color-success)]" />}
                  </div>
                  <p className="text-xs text-[var(--color-text-tertiary)] mt-1">
                    规则：6+字符，含字母和数字{passwordStrength.level >= 3 ? ' ✅ 强度达标' : ''}
                  </p>
                </div>
              )}
            </div>

            {/* 确认密码 */}
            <div className="animate-stagger-4">
              <label htmlFor="confirm_password" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">确认密码</label>
              <div className="relative">
                <ShieldCheck size={16} className={`${iconBaseClass} ${inputIconColor('confirm_password')}`} />
                <input
                  id="confirm_password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  {...register('confirm_password')}
                  className={`${fieldBaseClass} ${errors.confirm_password ? fieldErrorClass : fieldNormalClass}`}
                  placeholder="再次输入密码"
                  disabled={isLoading}
                />
                {errors.confirm_password && (
                  <p className="mt-1.5 text-xs text-[var(--color-error)] flex items-center gap-1 animate-fade-in">
                    <AlertCircle size={12} /> {errors.confirm_password.message}
                  </p>
                )}
              </div>
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
            <div className="animate-stagger-5">
              <button
                ref={submitBtnRef}
                type="submit"
                disabled={isLoading || isSubmitting}
                className={`w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-[var(--radius-sm)] text-sm font-medium text-white transition-all duration-200 relative overflow-hidden ${
                  isLoading || isSubmitting
                    ? 'bg-[var(--color-primary-disabled)] cursor-not-allowed'
                    : 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] active:bg-[var(--color-primary-active)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] active:scale-[0.98]'
                }`}
              >
                {isLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>注册中...</span>
                    <span className="absolute bottom-0 left-0 h-0.5 bg-white/30 animate-progress" />
                  </>
                ) : (
                  '注册账户'
                )}
              </button>
            </div>
          </form>

          {/* 登录链接 */}
          <p className="mt-6 text-center text-sm text-[var(--color-text-secondary)] animate-stagger-5">
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

      {/* CSS 动画 */}
      <style>{`
        @keyframes pulse-slow {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.05); }
        }
        @keyframes pulse-slower {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(1.08); }
        }
        @keyframes slide-down {
          from { opacity: 0; transform: translateY(-12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes scale-in {
          from { opacity: 0; transform: scale(0.96); }
          to { opacity: 1; transform: scale(1); }
        }
        @keyframes progress {
          0% { width: 0; }
          50% { width: 60%; }
          100% { width: 100%; }
        }
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20% { transform: translateX(-4px); }
          40% { transform: translateX(4px); }
          60% { transform: translateX(-3px); }
          80% { transform: translateX(3px); }
        }
        .animate-pulse-slow { animation: pulse-slow 6s ease-in-out infinite; }
        .animate-pulse-slower { animation: pulse-slower 8s ease-in-out infinite; }
        .animate-slide-down { animation: slide-down 0.4s ease-out both; }
        .animate-scale-in { animation: scale-in 0.35s ease-out both; }
        .animate-progress { animation: progress 2s ease-in-out infinite; }
        .animate-fade-in { animation: fade-in 0.25s ease-out both; }
        .animate-shake { animation: shake 0.4s ease-out both; }
        .animate-stagger-1 { animation: slide-down 0.35s ease-out 0.05s both; }
        .animate-stagger-2 { animation: slide-down 0.35s ease-out 0.1s both; }
        .animate-stagger-3 { animation: slide-down 0.35s ease-out 0.15s both; }
        .animate-stagger-4 { animation: slide-down 0.35s ease-out 0.2s both; }
        .animate-stagger-5 { animation: slide-down 0.35s ease-out 0.25s both; }
      `}</style>
    </div>
  );
}
