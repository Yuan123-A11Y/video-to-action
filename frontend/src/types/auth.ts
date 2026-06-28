// 认证相关类型定义

/**
 * 用户角色类型
 */
export type UserRole = 'admin' | 'user';

/**
 * 用户接口
 */
export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  created_at: string;
  last_login_at?: string;
  is_active: boolean;
}

/**
 * Token 响应接口
 */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * 登录请求接口
 */
export interface LoginRequest {
  username: string;
  password: string;
  remember_me?: boolean;
}

/**
 * 注册请求接口
 */
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
}

/**
 * 刷新 Token 请求接口
 */
export interface RefreshTokenRequest {
  refresh_token: string;
}

/**
 * 修改密码请求接口
 */
export interface PasswordChangeRequest {
  old_password: string;
  new_password: string;
  confirm_password: string;
}

/**
 * API 响应包装接口
 */
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

/**
 * 认证状态接口
 */
export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

/**
 * 认证上下文类型接口
 */
export interface AuthContextType {
  // 状态
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // 方法
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<boolean>;
  clearError: () => void;
}

/**
 * JWT Payload 接口
 */
export interface JWTPayload {
  sub: string;
  exp: number;
  iat: number;
  user_id: number;
  username: string;
  role: UserRole;
}
