import axios from 'axios';
import type {
  Video, Tool, Task, ProcessRequest, ProcessResponse,
  BatchProcessRequest, SearchParams, SearchResult, Stats,
} from '../types';
import type {
  LoginRequest,
  RegisterRequest,
  RefreshTokenRequest,
  ApiResponse,
  User,
  TokenResponse,
} from '../types/auth';

// ====== 登出回调（由 AuthContext 设置）======
let logoutCallback: (() => void) | null = null;

export function setLogoutCallback(callback: () => void) {
  logoutCallback = callback;
}

// ====== Axios 实例创建 ======

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

// ====== 请求拦截器：自动添加 Token ======

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ====== 响应拦截器：处理 Token 过期 ======

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 如果是 401 错误且不是刷新 Token 的请求
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      originalRequest.url !== '/auth/refresh'
    ) {
      originalRequest._retry = true;

      // 尝试刷新 Token
      try {
        if (!isRefreshing) {
          isRefreshing = true;
          refreshPromise = refreshTokenOnly();
        }

        const success = await refreshPromise;

        if (success) {
          // 刷新成功，重试原请求
          const newToken = localStorage.getItem('access_token');
          if (newToken) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          return api(originalRequest);
        } else {
          // 刷新失败，清除 Token 并通知 AuthContext 处理登出
          clearAuthData();
          // 通过回调通知 AuthContext 处理登出，由 ProtectedRoute 控制重定向
          if (logoutCallback) {
            logoutCallback();
          } else {
            window.location.href = '/login';
          }
          return Promise.reject(new Error('会话已过期，请重新登录'));
        }
      } catch (refreshError) {
        clearAuthData();
        // 通过回调通知 AuthContext 处理登出，由 ProtectedRoute 控制重定向
        if (logoutCallback) {
          logoutCallback();
        } else {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
        refreshPromise = null;
      }
    }

    // 其他错误处理
    const message =
      error.response?.data?.detail ||
      error.response?.data?.error?.message ||
      error.response?.data?.message ||
      error.message ||
      '请求失败，请稍后重试';

    return Promise.reject(new Error(message));
  }
);

// ====== Token 刷新辅助函数 ======

/**
 * 仅刷新 Token（不更新状态）
 */
async function refreshTokenOnly(): Promise<boolean> {
  const refreshToken = localStorage.getItem('refresh_token');

  if (!refreshToken) {
    return false;
  }

  try {
    const response = await axios.post<ApiResponse<TokenResponse>>(
      '/api/auth/refresh',
      { refresh_token: refreshToken } as RefreshTokenRequest,
      { baseURL: '/api', timeout: 10000 }
    );

    if (response.data.code === 0 && response.data.data) {
      const { access_token, refresh_token } = response.data.data;
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      return true;
    }

    return false;
  } catch (error) {
    console.error('Failed to refresh token:', error);
    return false;
  }
}

/**
 * 清除认证数据
 */
function clearAuthData(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
}

// ====== 认证相关 API ======

/**
 * 用户登录
 */
export async function login(request: LoginRequest): Promise<ApiResponse<TokenResponse & { user: User }>> {
  const { data } = await api.post<ApiResponse<TokenResponse & { user: User }>>('/auth/login', request);
  return data;
}

/**
 * 用户注册
 */
export async function register(request: RegisterRequest): Promise<ApiResponse<TokenResponse & { user: User }>> {
  // 只发送后端需要的字段，排除 confirm_password
  const { data } = await api.post<ApiResponse<TokenResponse & { user: User }>>('/auth/register', {
    username: request.username,
    email: request.email,
    password: request.password,
  });
  return data;
}

/**
 * 刷新 Token
 */
export async function refreshToken(request: RefreshTokenRequest): Promise<ApiResponse<TokenResponse>> {
  const { data } = await api.post<ApiResponse<TokenResponse>>('/auth/refresh', request);
  return data;
}

/**
 * 获取当前用户信息
 */
export async function getMe(): Promise<ApiResponse<User>> {
  const { data } = await api.get<ApiResponse<User>>('/auth/me');
  return data;
}

/**
 * 修改密码
 */
export async function changePassword(oldPassword: string, newPassword: string): Promise<ApiResponse<null>> {
  const { data } = await api.post<ApiResponse<null>>('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  });
  return data;
}

/**
 * 用户登出
 */
export async function logout(): Promise<ApiResponse<null>> {
  const refreshToken = localStorage.getItem('refresh_token');
  const { data } = await api.post<ApiResponse<null>>('/auth/logout', {
    refresh_token: refreshToken,
  });
  return data;
}

// ====== 视频处理 API ======

export interface BatchProcessResponse {
  task_ids: Array<{ url: string; task_id: string }>;
  message: string;
}

export interface BatchStatusResponse {
  tasks: Array<{ task_id: string; status: string; error?: string }>;
}

export async function processVideo(request: ProcessRequest): Promise<ProcessResponse> {
  const { data } = await api.post<ProcessResponse>('/process', request, {
    timeout: 300000,
  });
  return data;
}

export async function batchProcessVideos(request: BatchProcessRequest): Promise<BatchProcessResponse> {
  const { data } = await api.post<BatchProcessResponse>('/batch/process', request);
  return data;
}

export async function getBatchStatus(taskIds: string[]): Promise<BatchStatusResponse> {
  const { data } = await api.get<BatchStatusResponse>('/batch/status', {
    params: { task_ids: taskIds.join(',') },
  });
  return data;
}

// ====== 任务查询 API ======

export async function getTask(taskId: string): Promise<Task> {
  const { data } = await api.get<Task>(`/tasks/${taskId}`);
  return data;
}

// ====== 视频列表 API ======

export async function getVideos(page = 1, pageSize = 10): Promise<{ videos: Video[]; total: number }> {
  const { data } = await api.get<{ videos: Video[]; total: number }>('/videos', {
    params: { limit: pageSize, offset: (page - 1) * pageSize },
  });
  return data;
}

export async function getVideo(videoId: number): Promise<Video> {
  const { data } = await api.get<Video>(`/videos/${videoId}`);
  return data;
}

// ====== 工具列表 API ======

export async function getTools(page = 1, pageSize = 20): Promise<{ tools: Tool[]; total: number }> {
  const { data } = await api.get<{ tools: Tool[]; total: number }>('/tools', {
    params: { limit: pageSize, offset: (page - 1) * pageSize },
  });
  return data;
}

export async function getTool(toolId: number): Promise<Tool> {
  const { data } = await api.get<Tool>(`/tools/${toolId}`);
  return data;
}

// ====== 搜索 API ======

export async function search(params: SearchParams): Promise<SearchResult> {
  const { data } = await api.get<SearchResult>('/search', {
    params: {
      query: params.q,
      type: params.type || 'video',
      limit: params.page_size || 10,
    },
  });
  return data;
}

// ====== 统计 API ======

export async function getStats(): Promise<Stats> {
  const { data } = await api.get<Stats>('/stats');
  return data;
}

export default api;
