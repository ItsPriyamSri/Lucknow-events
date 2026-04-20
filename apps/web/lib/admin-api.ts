import axios from "axios";

const DEFAULT = "http://localhost:8000/api/v1";

function baseUrl(): string {
  if (typeof window !== "undefined") return "/api/v1";
  return process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || DEFAULT;
}

export const adminApi = axios.create({
  baseURL: baseUrl(),
  headers: { "Content-Type": "application/json" },
});

adminApi.interceptors.request.use((config) => {
  if (typeof window === "undefined") return config;
  const t = localStorage.getItem("admin_token");
  if (t) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

export interface AdminSource {
  id: string;
  name: string;
  platform: string | null;
  base_url: string;
  enabled: boolean;
  crawl_strategy: string | null;
  trust_score: number;
  crawl_interval_hours: number;
  last_crawled_at: string | null;
  last_success_at: string | null;
  consecutive_failures: number;
  created_at: string;
}

export interface ModerationItem {
  id: string;
  entity_type: string | null;
  entity_id: string | null;
  reason: string | null;
  severity: string | null;
  status: string;
  created_at: string;
}

export interface StatsOut {
  events_total: number;
  events_this_week: number;
  pending_moderation: number;
  sources_active: number;
}

export const adminService = {
  login: async (email: string, password: string): Promise<{ access_token: string }> => {
    const { data } = await adminApi.post<{ access_token: string; token_type: string }>("/admin/auth/login", {
      email,
      password,
    });
    return data;
  },
  listSources: async (): Promise<AdminSource[]> => {
    const { data } = await adminApi.get<AdminSource[]>("/admin/sources");
    return data;
  },
  patchSource: async (id: string, body: { enabled?: boolean }): Promise<AdminSource> => {
    const { data } = await adminApi.patch<AdminSource>(`/admin/sources/${id}`, body);
    return data;
  },
  triggerCrawl: async (id: string): Promise<{ task_id: string }> => {
    const { data } = await adminApi.post<{ task_id: string }>(`/admin/sources/crawl/run/${id}`);
    return data;
  },
  triggerAll: async (): Promise<{ task_id: string }> => {
    const { data } = await adminApi.post<{ task_id: string }>("/admin/sources/crawl/run-all");
    return data;
  },
  listModeration: async (): Promise<ModerationItem[]> => {
    const { data } = await adminApi.get<ModerationItem[]>("/admin/moderation");
    return data;
  },
  approve: async (id: string): Promise<ModerationItem> => {
    const { data } = await adminApi.post<ModerationItem>(`/admin/moderation/${id}/approve`);
    return data;
  },
  reject: async (id: string): Promise<ModerationItem> => {
    const { data } = await adminApi.post<ModerationItem>(`/admin/moderation/${id}/reject`);
    return data;
  },
  stats: async (): Promise<StatsOut> => {
    const { data } = await adminApi.get<StatsOut>("/admin/stats");
    return data;
  },
};
