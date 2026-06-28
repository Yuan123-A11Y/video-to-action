import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { changePassword } from '../api/client';
import { User, AlertCircle, CheckCircle2, Camera, Shield, Trash2, Eye, EyeOff, Loader2 } from 'lucide-react';

/**
 * 用户资料页面组件 — 统一品牌设计语言
 */
export default function ProfilePage() {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  const [activeTab, setActiveTab] = useState<'profile' | 'password' | 'danger'>('profile');
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');

  // 修改密码表单
  const [oldPassword, setOldPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [isChangingPassword, setIsChangingPassword] = useState<boolean>(false);

  // 编辑邮箱
  const [isEditingEmail, setIsEditingEmail] = useState<boolean>(false);
  const [newEmail, setNewEmail] = useState<string>('');
  const [isSavingEmail, setIsSavingEmail] = useState<boolean>(false);

  // 注销账户
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<boolean>(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState<string>('');

  // 重定向如果未认证
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--color-primary)] mx-auto" />
          <p className="text-[var(--color-text-secondary)] text-sm">加载中...</p>
        </div>
      </div>
    );
  }

  /**
   * 处理修改密码
   */
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage('');
    setErrorMessage('');

    if (newPassword !== confirmPassword) {
      setErrorMessage('两次输入的密码不一致');
      return;
    }

    if (newPassword.length < 6) {
      setErrorMessage('新密码至少6个字符');
      return;
    }

    setIsChangingPassword(true);

    try {
      await changePassword(oldPassword, newPassword);
      setSuccessMessage('密码修改成功！');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '修改密码失败');
    } finally {
      setIsChangingPassword(false);
    }
  };

  /**
   * 处理修改邮箱
   */
  const handleChangeEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage('');
    setErrorMessage('');

    if (!newEmail.trim()) {
      setErrorMessage('请输入新邮箱地址');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(newEmail)) {
      setErrorMessage('请输入有效的邮箱地址');
      return;
    }

    setIsSavingEmail(true);

    try {
      // TODO: 调用修改邮箱的 API
      // await updateEmail(newEmail);
      setSuccessMessage('邮箱修改成功！');
      setIsEditingEmail(false);
      setNewEmail('');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '修改邮箱失败');
    } finally {
      setIsSavingEmail(false);
    }
  };

  /**
   * 处理注销账户
   */
  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== '确认注销') {
      setErrorMessage('请输入"确认注销"以确认操作');
      return;
    }

    try {
      // TODO: 调用注销账户的 API
      // await deleteAccount();
      logout();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '注销账户失败');
    }
  };

  /**
   * 获取用户头像字母
   */
  const getAvatarLetter = (username: string): string => {
    return username.charAt(0).toUpperCase();
  };

  const tabItems = [
    { key: 'profile' as const, label: '个人资料', icon: User },
    { key: 'password' as const, label: '修改密码', icon: Shield },
    { key: 'danger' as const, label: '危险操作', icon: Trash2 },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">用户资料</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          管理您的账户信息和设置
        </p>
      </div>

      {/* 成功/错误提示 */}
      {successMessage && (
        <div className="mb-4 rounded-xl bg-[var(--color-success-soft)] border border-[var(--color-success)]/20 p-4 animate-fade-in">
          <div className="flex items-center gap-3">
            <CheckCircle2 size={20} className="text-[var(--color-success)] shrink-0" />
            <p className="text-sm font-medium text-[var(--color-success)]">{successMessage}</p>
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="mb-4 rounded-xl bg-[var(--color-error-soft)] border border-[var(--color-error)]/20 p-4 animate-shake">
          <div className="flex items-center gap-3">
            <AlertCircle size={20} className="text-[var(--color-error)] shrink-0" />
            <p className="text-sm font-medium text-[var(--color-error)]">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* 主卡片 */}
      <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-xl)] border border-[var(--color-border-subtle)] shadow-[var(--shadow-lg)] overflow-hidden">

        {/* 用户信息头部 */}
        <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-hover)] px-6 py-10">
          <div className="flex items-center gap-6">
            {/* 头像 */}
            <div className="relative">
              <div className="h-24 w-24 rounded-full bg-white flex items-center justify-center text-4xl font-bold text-[var(--color-primary-strong)] shadow-lg">
                {getAvatarLetter(user.username)}
              </div>
              <button
                className="absolute bottom-0 right-0 p-1.5 bg-white rounded-full shadow-md text-[var(--color-text-tertiary)] hover:text-[var(--color-primary)] transition-colors"
                title="更换头像"
              >
                <Camera size={14} />
              </button>
            </div>
            {/* 用户信息 */}
            <div className="flex-1 min-w-0">
              <h2 className="text-3xl font-bold text-white truncate">{user.username}</h2>
              <p className="mt-1 text-[var(--color-primary-soft)] truncate">{user.email}</p>
              <div className="mt-3 flex items-center gap-2 flex-wrap">
                <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                  user.role === 'admin'
                    ? 'bg-purple-200 text-purple-900'
                    : 'bg-blue-200 text-blue-900'
                }`}>
                  {user.role === 'admin' ? '管理员' : '用户'}
                </span>
                <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                  user.is_active ? 'bg-green-200 text-green-900' : 'bg-red-200 text-red-900'
                }`}>
                  {user.is_active ? '活跃' : '禁用'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 标签页导航 */}
        <div className="border-b border-[var(--color-border-subtle)]">
          <nav className="flex">
            {tabItems.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`py-4 px-6 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                  activeTab === key
                    ? key === 'danger'
                      ? 'border-[var(--color-error)] text-[var(--color-error)]'
                      : 'border-[var(--color-primary)] text-[var(--color-primary-strong)]'
                    : 'border-transparent text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] hover:border-[var(--color-border-subtle)]'
                }`}
              >
                <Icon size={16} />
                {label}
              </button>
            ))}
          </nav>
        </div>

        {/* 标签页内容 */}
        <div className="p-6">
          {/* 个人资料标签页 */}
          {activeTab === 'profile' && (
            <div className="space-y-8">
              <div>
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-5">基本信息</h3>
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-6">
                  <div>
                    <dt className="text-sm font-medium text-[var(--color-text-tertiary)]">用户名</dt>
                    <dd className="mt-1.5 text-sm text-[var(--color-text-primary)] font-medium">{user.username}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-[var(--color-text-tertiary)]">邮箱</dt>
                    <dd className="mt-1.5 text-sm text-[var(--color-text-primary)]">{user.email}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-[var(--color-text-tertiary)]">角色</dt>
                    <dd className="mt-1.5 text-sm text-[var(--color-text-primary)]">
                      {user.role === 'admin' ? '管理员' : '普通用户'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-[var(--color-text-tertiary)]">注册时间</dt>
                    <dd className="mt-1.5 text-sm text-[var(--color-text-primary)]">
                      {new Date(user.created_at).toLocaleString('zh-CN')}
                    </dd>
                  </div>
                  {user.last_login_at && (
                    <div>
                      <dt className="text-sm font-medium text-[var(--color-text-tertiary)]">上次登录</dt>
                      <dd className="mt-1.5 text-sm text-[var(--color-text-primary)]">
                        {new Date(user.last_login_at).toLocaleString('zh-CN')}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>

              {/* 编辑邮箱 */}
              <div className="pt-6 border-t border-[var(--color-border-subtle)]">
                <h4 className="text-base font-semibold text-[var(--color-text-primary)] mb-4">修改邮箱</h4>
                {isEditingEmail ? (
                  <form onSubmit={handleChangeEmail} className="space-y-4">
                    <div>
                      <label htmlFor="newEmail" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">
                        新邮箱地址
                      </label>
                      <input
                        type="email"
                        id="newEmail"
                        value={newEmail}
                        onChange={(e) => setNewEmail(e.target.value)}
                        className="w-full px-4 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] text-sm bg-[var(--color-bg-surface)] outline-none transition-all placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] hover:border-[var(--color-border-strong)]"
                        placeholder={user.email}
                        disabled={isSavingEmail}
                      />
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        type="submit"
                        disabled={isSavingEmail}
                        className={`px-5 py-2 text-sm font-medium text-white rounded-[var(--radius-sm)] transition-all ${
                          isSavingEmail ? 'bg-[var(--color-primary-disabled)] cursor-not-allowed' : 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] active:bg-[var(--color-primary-active)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)]'
                        }`}
                      >
                        {isSavingEmail ? '保存中...' : '保存'}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setIsEditingEmail(false);
                          setNewEmail('');
                          setErrorMessage('');
                        }}
                        className="px-5 py-2 text-sm font-medium text-[var(--color-text-secondary)] bg-[var(--color-bg-raised)] rounded-[var(--radius-sm)] hover:bg-[var(--color-bg-hover)] transition-colors border border-[var(--color-border-default)]"
                      >
                        取消
                      </button>
                    </div>
                  </form>
                ) : (
                  <button
                    onClick={() => setIsEditingEmail(true)}
                    className="px-5 py-2 text-sm font-medium text-[var(--color-primary)] bg-[var(--color-primary-soft)] rounded-[var(--radius-sm)] hover:bg-[var(--color-primary-soft-hover)] transition-colors border border-[var(--color-primary-border)]/30"
                  >
                    修改邮箱
                  </button>
                )}
              </div>
            </div>
          )}

          {/* 修改密码标签页 */}
          {activeTab === 'password' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-1">修改密码</h3>
                <p className="text-sm text-[var(--color-text-secondary)] mb-6">设置一个新的强密码来保护您的账户</p>
              </div>
              <form onSubmit={handleChangePassword} className="space-y-5 max-w-md">
                {/* 当前密码 */}
                <div>
                  <label htmlFor="oldPassword" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">
                    当前密码
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="oldPassword"
                      value={oldPassword}
                      onChange={(e) => setOldPassword(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] text-sm bg-[var(--color-bg-surface)] outline-none transition-all placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] hover:border-[var(--color-border-strong)] pr-12"
                      required
                      disabled={isChangingPassword}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] transition-colors"
                      disabled={isChangingPassword}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                {/* 新密码 */}
                <div>
                  <label htmlFor="newPassword" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">
                    新密码
                  </label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="newPassword"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] text-sm bg-[var(--color-bg-surface)] outline-none transition-all placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] hover:border-[var(--color-border-strong)]"
                    required
                    minLength={6}
                    disabled={isChangingPassword}
                  />
                </div>

                {/* 确认新密码 */}
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-[var(--color-text-primary)] mb-1.5">
                    确认新密码
                  </label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="confirmPassword"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] text-sm bg-[var(--color-bg-surface)] outline-none transition-all placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] hover:border-[var(--color-border-strong)]"
                    required
                    disabled={isChangingPassword}
                  />
                </div>

                {/* 显示密码选项 */}
                <div className="flex items-center gap-2">
                  <input
                    id="showPassword"
                    type="checkbox"
                    checked={showPassword}
                    onChange={(e) => setShowPassword(e.target.checked)}
                    className="h-4 w-4 rounded border-[var(--color-border-default)] text-[var(--color-primary)] focus:ring-[var(--color-primary)] focus:ring-offset-0 accent-[var(--color-primary)]"
                    disabled={isChangingPassword}
                  />
                  <label htmlFor="showPassword" className="text-sm text-[var(--color-text-secondary)] select-none cursor-pointer">
                    显示密码
                  </label>
                </div>

                {/* 提交按钮 */}
                <div>
                  <button
                    type="submit"
                    disabled={isChangingPassword}
                    className={`px-5 py-2.5 text-sm font-medium text-white rounded-[var(--radius-sm)] transition-all ${
                      isChangingPassword ? 'bg-[var(--color-primary-disabled)] cursor-not-allowed' : 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] active:bg-[var(--color-primary-active)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)]'
                    }`}
                  >
                    {isChangingPassword ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 size={14} className="animate-spin" />
                        修改中...
                      </span>
                    ) : (
                      '修改密码'
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* 危险操作标签页 */}
          {activeTab === 'danger' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-[var(--color-error)] mb-1">危险操作</h3>
                <p className="text-sm text-[var(--color-text-secondary)] mb-6">
                  以下操作不可逆转，请谨慎操作。
                </p>
              </div>

              {/* 注销账户 */}
              <div className="bg-[var(--color-error-soft)]/50 border border-[var(--color-error)]/20 rounded-[var(--radius-lg)] p-5">
                <h4 className="text-base font-semibold text-[var(--color-error)] mb-2">注销账户</h4>
                <p className="text-sm text-[var(--color-error)]/80 mb-4">
                  注销账户后，您的所有数据将被永久删除，且无法恢复。
                </p>
                {showDeleteConfirm ? (
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="deleteConfirm" className="block text-sm font-medium text-[var(--color-error)] mb-1.5">
                        请输入"确认注销"以确认操作
                      </label>
                      <input
                        type="text"
                        id="deleteConfirm"
                        value={deleteConfirmText}
                        onChange={(e) => setDeleteConfirmText(e.target.value)}
                        className="w-full px-4 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-error)]/50 text-sm bg-white outline-none transition-all placeholder-[var(--color-text-tertiary)] text-[var(--color-text-primary)] focus:border-[var(--color-error)] focus:shadow-[0_0_0_3px_rgba(220,38,38,0.15)]"
                        placeholder="确认注销"
                      />
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={handleDeleteAccount}
                        className="px-5 py-2 text-sm font-medium text-white bg-[var(--color-error)] rounded-[var(--radius-sm)] hover:bg-[var(--color-error-hover)] transition-colors"
                      >
                        确认注销
                      </button>
                      <button
                        onClick={() => {
                          setShowDeleteConfirm(false);
                          setDeleteConfirmText('');
                        }}
                        className="px-5 py-2 text-sm font-medium text-[var(--color-text-secondary)] bg-[var(--color-bg-raised)] rounded-[var(--radius-sm)] hover:bg-[var(--color-bg-hover)] transition-colors border border-[var(--color-border-default)]"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="px-5 py-2 text-sm font-medium text-[var(--color-error)] bg-white border border-[var(--color-error)]/30 rounded-[var(--radius-sm)] hover:bg-[var(--color-error-soft)] transition-colors"
                  >
                    注销我的账户
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
