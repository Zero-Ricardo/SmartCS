/**
 * 管理后台 API 封装
 * 所有 /admin/* 接口，使用 JWT Bearer Token 鉴权
 */

const API_BASE_URL = ((import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || "") + "/api";

const TOKEN_KEY = "smartcs-admin-token";

// ====== Token 管理 ======

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token);
export const removeToken = () => localStorage.removeItem(TOKEN_KEY);

const authHeaders = (): Record<string, string> => {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
};

// ====== 认证接口 ======

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  company_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AdminUser {
  id: string;
  email: string;
  company_name: string | null;
  role: string;
  created_at: string;
}

export const login = async (data: LoginRequest): Promise<TokenResponse> => {
  const res = await fetch(`${API_BASE_URL}/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "登录失败" }));
    throw new Error(err.detail || "登录失败");
  }
  return res.json();
};

export const register = async (data: RegisterRequest): Promise<AdminUser> => {
  const res = await fetch(`${API_BASE_URL}/admin/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "注册失败" }));
    throw new Error(err.detail || "注册失败");
  }
  return res.json();
};

export const getMe = async (): Promise<AdminUser> => {
  const res = await fetch(`${API_BASE_URL}/admin/me`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("未授权");
  return res.json();
};

// ====== 知识库文档接口 ======

export interface KnowledgeDocument {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  ingest_progress: number;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  total: number;
  documents: KnowledgeDocument[];
}

export const listDocuments = async (skip = 0, limit = 20): Promise<DocumentListResponse> => {
  const res = await fetch(
    `${API_BASE_URL}/admin/knowledge/documents?skip=${skip}&limit=${limit}`,
    { headers: authHeaders() }
  );
  if (!res.ok) throw new Error("获取文档列表失败");
  return res.json();
};

export const getDocument = async (docId: string): Promise<KnowledgeDocument> => {
  const res = await fetch(`${API_BASE_URL}/admin/knowledge/documents/${docId}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("获取文档详情失败");
  return res.json();
};

export const uploadDocument = async (file: File): Promise<KnowledgeDocument> => {
  const formData = new FormData();
  formData.append("file", file);
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}/admin/knowledge/upload`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "上传失败" }));
    throw new Error(err.detail || "上传失败");
  }
  return res.json();
};

export const triggerIngest = async (docId: string): Promise<void> => {
  const res = await fetch(`${API_BASE_URL}/admin/knowledge/documents/${docId}/ingest`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "入库失败" }));
    throw new Error(err.detail || "入库失败");
  }
};

export const deleteVectors = async (docId: string): Promise<void> => {
  const res = await fetch(`${API_BASE_URL}/admin/knowledge/documents/${docId}/vectors`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("删除向量失败");
};

export const deleteDocument = async (docId: string): Promise<void> => {
  const res = await fetch(`${API_BASE_URL}/admin/knowledge/documents/${docId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("删除文档失败");
};
