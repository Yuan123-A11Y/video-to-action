import { createContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { AuthContextType, AuthState, User, LoginRequest, RegisterRequest, JWTPayload } from '../types/auth';

// 导入 API 客户端
import { login as loginApi, register as registerApi, refreshToken as refreshTokenApi, getMe, setLogoutCallback } from '../api/client';

// 创建认证上下文
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// localStorage 键名常量
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user';

/**
 * 解析 JWT Token 获取 Payload
 */
function parseJWTPayload(token: string): JWTPayload | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Failed to parse JWT token:', error);
    return null;
  }
}

/**
 * 检查 Token 是否即将过期（5分钟内）
 */
function isTokenExpiringSoon(token: string): boolean {
  const payload = parseJWTPayload(token);
  if (!payload || !payload.exp) {
    return true;
  }

  const exp = payload.exp * 1000;
  const now = Date.now();
  const fiveMinutes = 5 * 60 * 1000;

  return exp - now < fiveMinutes;
}

/**
 * 检查 Token 是否已过期
 */
function isTokenExpired(token: string): boolean {
  const payload = parseJWTPayload(token);
  if (!payload || !payload.exp) {
    return true;
  }

  const exp = payload.exp * 1000;
  const now = Date.now();

  return now >= exp;
}

/**
 * 从 localStorage 加载认证状态
 */
function loadAuthState(): Partial<AuthState> {
  try {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    const userStr = localStorage.getItem(USER_KEY);

    let user: User | null = null;
    if (userStr) {
      user = JSON.parse(userStr);
    }

    if (accessToken && isTokenExpired(accessToken)) {
      return {
        user: null,
        accessToken: null,
        refreshToken,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      };
    }

    return {
      user,
      accessToken,
      refreshToken,
      isAuthenticated: !!accessToken && !!user,
      isLoading: false,
      error: null,
    };
  } catch (error) {
    console.error('Failed to load auth state from localStorage:', error);
    return {
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    };
  }
}

/**
 * AuthProvider 组件 Props
 */
interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Token 过期提示组件 Props
 */
interface TokenExpiryWarningProps {
  show: boolean;
  onRefresh: () => void;
  onDismiss: () => void;
}

/**
 * Token 过期提示组件
 */
function TokenExpiryWarning({ show, onRefresh, onDismiss }: TokenExpiryWarningProps) {
  if (!show) return null;

  return (
    <div className="fixed bottom-4 right-4 max-w-sm bg-yellow-50 border border-yellow-200 rounded-lg shadow-lg p-4 animate-fade-in z-50">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <svg className="h-6 w-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-18L18.364 4.64c-.866-1.5-3.032-1.5-3.898 0L10.832 14.36c-.866 1.5-.068 3.36 1.732 3.36z" />
          </svg>
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-medium text-yellow-800">会话即将过期</h4>
          <p className="mt-1 text-sm text-yellow-700">
            您的登录状态将在5分钟内过期。
          </p>
          <div className="mt-3 flex items-center gap-2">
            <button
              onClick={onRefresh}
              className="px-3 py-1.5 text-xs font-medium text-white bg-yellow-600 rounded hover:bg-yellow-700 transition-colors"
            >
              立即刷新
            </button>
            <button
              onClick={onDismiss}
              className="px-3 py-1.5 text-xs font-medium text-yellow-800 bg-yellow-100 rounded hover:bg-yellow-200 transition-colors"
            >
              稍后提醒
            </button>
          </div>
        </div>
        <button
          onClick={onDismiss}
          className="flex-shrink-0 text-yellow-600 hover:text-yellow-800"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

/**
 * 认证提供者组件
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>(() => ({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  }));

  // Token 过期提示状态
  const [showExpiryWarning, setShowExpiryWarning] = useState<boolean>(false);
  const [expiryWarningDismissed, setExpiryWarningDismissed] = useState<boolean>(false);

  /**
   * 更新状态并持久化到 localStorage
   */
  const updateState = useCallback((newState: Partial<AuthState>) => {
    setState((prevState) => {
      const updatedState = { ...prevState, ...newState };

      try {
        if (updatedState.accessToken !== undefined) {
          if (updatedState.accessToken) {
            localStorage.setItem(ACCESS_TOKEN_KEY, updatedState.accessToken);
          } else {
            localStorage.removeItem(ACCESS_TOKEN_KEY);
          }
        }

        if (updatedState.refreshToken !== undefined) {
          if (updatedState.refreshToken) {
            localStorage.setItem(REFRESH_TOKEN_KEY, updatedState.refreshToken);
          } else {
            localStorage.removeItem(REFRESH_TOKEN_KEY);
          }
        }

        if (updatedState.user !== undefined) {
          if (updatedState.user) {
            localStorage.setItem(USER_KEY, JSON.stringify(updatedState.user));
          } else {
            localStorage.removeItem(USER_KEY);
          }
        }
      } catch (error) {
        console.error('Failed to persist auth state:', error);
      }

      return updatedState;
    });
  }, []);

  /**
   * 登录方法
   */
  const login = useCallback(async (username: string, password: string) => {
    updateState({ isLoading: true, error: null });

    try {
      const request: LoginRequest = { username, password };
      const response = await loginApi(request);

      if (response.code === 0 && response.data) {
        const { user, access_token, refresh_token } = response.data;

        updateState({
          user,
          accessToken: access_token,
          refreshToken: refresh_token,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      } else {
        throw new Error(response.message || '登录失败');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '登录失败，请稍后重试';
      updateState({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });
      throw error;
    }
  }, [updateState]);

  /**
   * 注册方法
   */
  const register = useCallback(async (username: string, email: string, password: string) => {
    updateState({ isLoading: true, error: null });

    try {
      const request: RegisterRequest = { username, email, password, confirm_password: password };
      const response = await registerApi(request);

      if (response.code === 0 && response.data) {
        const { user, access_token, refresh_token } = response.data;

        updateState({
          user,
          accessToken: access_token,
          refreshToken: refresh_token,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      } else {
        throw new Error(response.message || '注册失败');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '注册失败，请稍后重试';
      updateState({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });
      throw error;
    }
  }, [updateState]);

  /**
   * 登出方法
   */
  const logout = useCallback(() => {
    updateState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });

    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);

    window.location.href = '/login';
  }, [updateState]);

  // ====== 设置 axios 拦截器的登出回调 ======
  useEffect(() => {
    setLogoutCallback(() => {
      logout();
    });
  }, [logout]);

  /**
   * 刷新 Token 方法
   */
  const refreshToken = useCallback(async (): Promise<boolean> => {
    const currentRefreshToken = state.refreshToken || localStorage.getItem(REFRESH_TOKEN_KEY);

    if (!currentRefreshToken) {
      logout();
      return false;
    }

    try {
      const response = await refreshTokenApi({ refresh_token: currentRefreshToken });

      if (response.code === 0 && response.data) {
        const { access_token, refresh_token } = response.data;

        updateState({
          accessToken: access_token,
          refreshToken: refresh_token,
          isAuthenticated: true,
          error: null,
        });

        // 刷新成功后，重置过期提示状态
        setShowExpiryWarning(false);
        setExpiryWarningDismissed(false);

        return true;
      } else {
        throw new Error(response.message || '刷新 Token 失败');
      }
    } catch (error) {
      console.error('Failed to refresh token:', error);
      logout();
      return false;
    }
  }, [state.refreshToken, logout, updateState]);

  /**
   * 清除错误
   */
  const clearError = useCallback(() => {
    updateState({ error: null });
  }, [updateState]);

  /**
   * 处理 Token 过期提示的"立即刷新"按钮
   */
  const handleRefreshToken = useCallback(async () => {
    setShowExpiryWarning(false);
    await refreshToken();
  }, [refreshToken]);

  /**
   * 处理 Token 过期提示的"稍后提醒"按钮
   */
  const handleDismissWarning = useCallback(() => {
    setShowExpiryWarning(false);
    setExpiryWarningDismissed(true);

    // 2分钟后再次提示
    setTimeout(() => {
      setExpiryWarningDismissed(false);
    }, 2 * 60 * 1000);
  }, []);

  /**
   * 初始化：从 localStorage 加载认证状态
   */
  useEffect(() => {
    const loadedState = loadAuthState();

    if (loadedState.accessToken && loadedState.user) {
      setState((prev) => ({
        ...prev,
        ...loadedState,
        isLoading: false,
      }));

      getMe()
        .then((response) => {
          if (response.code === 0 && response.data) {
            updateState({ user: response.data, isAuthenticated: true, isLoading: false });
          }
        })
        .catch(() => {
          if (loadedState.refreshToken) {
            refreshToken();
          } else {
            logout();
          }
        });
    } else if (loadedState.refreshToken) {
      refreshToken().then((success) => {
        if (!success) {
          logout();
        }
      });
    } else {
      setState((prev) => ({
        ...prev,
        isLoading: false,
      }));
    }
  }, []);

  /**
   * 自动刷新 Token 和过期提示
   */
  useEffect(() => {
    if (!state.accessToken) {
      return;
    }

    const checkTokenExpiry = async () => {
      if (state.accessToken && isTokenExpiringSoon(state.accessToken)) {
        if (!expiryWarningDismissed) {
          setShowExpiryWarning(true);
        }

        await refreshToken();
      }
    };

    checkTokenExpiry();

    const interval = setInterval(checkTokenExpiry, 60 * 1000);

    return () => clearInterval(interval);
  }, [state.accessToken, refreshToken, expiryWarningDismissed]);

  /**
   * 上下文值
   */
  const contextValue: AuthContextType = {
    user: state.user,
    accessToken: state.accessToken,
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    error: state.error,
    login,
    register,
    logout,
    refreshToken,
    clearError,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
      {/* Token 过期提示 */}
      <TokenExpiryWarning
        show={showExpiryWarning}
        onRefresh={handleRefreshToken}
        onDismiss={handleDismissWarning}
      />
    </AuthContext.Provider>
  );
}

export default AuthContext;
