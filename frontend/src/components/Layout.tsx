import { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  Home,
  Film,
  BookOpen,
  Package,
  Settings,
  Zap,
  User,
  LogOut,
  LogIn,
  UserPlus,
  ChevronDown,
  LayoutDashboard,
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: '首页', Icon: Home },
  { path: '/videos', label: '视频库', Icon: Film },
  { path: '/knowledge', label: '知识库', Icon: BookOpen },
  { path: '/batch', label: '批量处理', Icon: Package },
  { path: '/settings', label: '配置', Icon: Settings },
];

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();

  const [isUserMenuOpen, setIsUserMenuOpen] = useState<boolean>(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  /**
   * 获取用户头像字母
   */
  const getAvatarLetter = (username: string): string => {
    return username.charAt(0).toUpperCase();
  };

  /**
   * 处理退出登录
   */
  const handleLogout = () => {
    setIsUserMenuOpen(false);
    logout();
  };

  /**
   * 处理个人资料点击
   */
  const handleProfileClick = () => {
    setIsUserMenuOpen(false);
    navigate('/profile');
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg-app)] flex flex-col">
      {/* Header */}
      <header className="bg-[var(--color-bg-surface)] border-b border-[var(--color-border-subtle)] sticky top-0 z-50" style={{ height: 'var(--nav-height)' }}>
        <div className="h-full max-w-[var(--content-max-width)] mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          {/* Logo */}
          <Link
            to="/"
            className="flex items-center gap-2 text-lg font-semibold text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] transition-colors"
          >
            <Zap size={22} />
            <span>Video-to-Action</span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(({ path, label, Icon }) => {
              const isActive = path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(path);
              return (
                <Link
                  key={path}
                  to={path}
                  className={`relative px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'text-[var(--color-primary-strong)]'
                      : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)]'
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <Icon size={16} />
                    {label}
                  </span>
                  {/* Active indicator */}
                  {isActive && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-[var(--color-primary)] rounded-full" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* User Menu */}
          <div className="flex items-center gap-2">
            {isAuthenticated && user ? (
              <div className="relative" ref={userMenuRef}>
                {/* User Avatar Button */}
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-[var(--color-bg-hover)] transition-colors"
                >
                  {/* Avatar */}
                  <div className="h-8 w-8 rounded-full bg-[var(--color-primary)] flex items-center justify-center text-white text-sm font-bold">
                    {getAvatarLetter(user.username)}
                  </div>

                  {/* Username and Role */}
                  <div className="hidden sm:block text-left">
                    <div className="text-[var(--color-text-primary)] font-medium">{user.username}</div>
                    <div className="text-xs text-[var(--color-text-tertiary)]">
                      {user.role === 'admin' ? '管理员' : '用户'}
                    </div>
                  </div>

                  {/* Dropdown Arrow */}
                  <ChevronDown
                    size={16}
                    className={`text-[var(--color-text-secondary)] transition-transform ${
                      isUserMenuOpen ? 'rotate-180' : ''
                    }`}
                  />
                </button>

                {/* Dropdown Menu */}
                {isUserMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded-md shadow-[var(--shadow-lg)] bg-[var(--color-bg-surface)] ring-1 ring-[var(--color-border-subtle)] divide-y divide-[var(--color-border-subtle)] animate-fade-in">
                    {/* User Info */}
                    <div className="px-4 py-3">
                      <p className="text-sm font-medium text-[var(--color-text-primary)]">{user.username}</p>
                      <p className="text-sm text-[var(--color-text-secondary)] truncate">{user.email}</p>
                      <div className="mt-1">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          user.role === 'admin'
                            ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary-strong)]'
                            : 'bg-[var(--color-bg-raised)] text-[var(--color-text-secondary)]'
                        }`}>
                          {user.role === 'admin' ? '管理员' : '用户'}
                        </span>
                      </div>
                    </div>

                    {/* Menu Items */}
                    <div className="py-1">
                      <button
                        onClick={handleProfileClick}
                        className="w-full text-left px-4 py-2 text-sm text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] flex items-center gap-2"
                      >
                        <User size={16} />
                        个人资料
                      </button>

                      {user.role === 'admin' && (
                        <button
                          onClick={() => {
                            setIsUserMenuOpen(false);
                            navigate('/admin');
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] flex items-center gap-2"
                        >
                          <LayoutDashboard size={16} />
                          管理后台
                        </button>
                      )}
                    </div>

                    {/* Logout */}
                    <div className="py-1">
                      <button
                        onClick={handleLogout}
                        className="w-full text-left px-4 py-2 text-sm text-[var(--color-error)] hover:bg-[var(--color-error-soft)] flex items-center gap-2"
                      >
                        <LogOut size={16} />
                        退出登录
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-1">
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] transition-colors"
                >
                  <LogIn size={16} />
                  <span>登录</span>
                </Link>
                <Link
                  to="/register"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)] transition-colors"
                >
                  <UserPlus size={16} />
                  <span>注册</span>
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden border-t border-[var(--color-border-subtle)]">
          <nav className="flex items-center justify-around px-4 py-2">
            {NAV_ITEMS.map(({ path, label, Icon }) => {
              const isActive = path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(path);
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex flex-col items-center gap-1 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? 'text-[var(--color-primary-strong)]'
                      : 'text-[var(--color-text-secondary)]'
                  }`}
                >
                  <Icon size={20} />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 w-full max-w-[var(--content-max-width)] mx-auto px-4 sm:px-6 lg:px-8 py-6" key={location.pathname}>
        <div className="animate-fade-in">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border-subtle)] py-6 mt-auto">
        <div className="max-w-[var(--content-max-width)] mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-[var(--color-text-tertiary)]">
          Video-to-Action &copy; {new Date().getFullYear()} &mdash; AI 驱动的视频分析平台
        </div>
      </footer>
    </div>
  );
}
