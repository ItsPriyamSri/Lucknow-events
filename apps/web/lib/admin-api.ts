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
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AdminSource {
  id: string;
  name: string;
  platform: string | null;
  base_url: string;
  enabled: boolean;
  status: "active" | "whitelisted" | "blacklisted";
  crawl_strategy: string | null;
  trust_score: number;
  crawl_interval_hours: number;
  last_crawled_at: string | null;
  last_success_at: string | null;
  consecutive_failures: number;
  created_at: string;
}

export interface AdminEvent {
  id: string;
  slug: string;
  title: string;
  start_at: string;
  end_at: string | null;
  mode: string | null;
  event_type: string | null;
  city: string | null;
  locality: string | null;
  venue: string | null;
  community_name: string | null;
  canonical_url: string;
  registration_url: string | null;
  is_featured: boolean;
  is_cancelled: boolean;
  is_free: boolean;
  published_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminEventListResponse {
  items: AdminEvent[];
  page: number;
  limit: number;
  total: number;
}

export interface EventUpdate {
  title?: string;
  description?: string;
  short_description?: string;
  start_at?: string;
  end_at?: string;
  city?: string;
  locality?: string;
  venue_name?: string;
  mode?: string;
  event_type?: string;
  canonical_url?: string;
  registration_url?: string;
  poster_url?: string;
  is_free?: boolean;
  is_featured?: boolean;
  is_cancelled?: boolean;
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
  sources_blacklisted: number;
}

export interface CrawlRun {
  id: string;
  source_id: string;
  started_at: string;
  finished_at: string | null;
  status: string | null;
  events_found: number;
  events_new: number;
  events_published: number;
  error_summary: string | null;
  created_at: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export const adminService = {
  // Auth
  login: async (email: string, password: string): Promise<{ access_token: string }> => {
    const { data } = await adminApi.post<{ access_token: string }>("/admin/auth/login", { email, password });
    return data;
  },

  // Stats
  stats: async (): Promise<StatsOut> => {
    const { data } = await adminApi.get<StatsOut>("/admin/stats");
    return data;
  },

  // Sources
  listSources: async (): Promise<AdminSource[]> => {
    const { data } = await adminApi.get<AdminSource[]>("/admin/sources");
    return data;
  },
  createSource: async (payload: Partial<AdminSource> & { base_url: string; name: string }): Promise<AdminSource> => {
    const { data } = await adminApi.post<AdminSource>("/admin/sources", payload);
    return data;
  },
  patchSource: async (id: string, body: Partial<AdminSource>): Promise<AdminSource> => {
    const { data } = await adminApi.patch<AdminSource>(`/admin/sources/${id}`, body);
    return data;
  },
  setSourceStatus: async (id: string, status: "active" | "whitelisted" | "blacklisted"): Promise<AdminSource> => {
    const { data } = await adminApi.post<AdminSource>(`/admin/sources/${id}/status`, { status });
    return data;
  },
  deleteSource: async (id: string): Promise<void> => {
    await adminApi.delete(`/admin/sources/${id}`);
  },
  triggerCrawl: async (id: string): Promise<{ task_id: string }> => {
    const { data } = await adminApi.post<{ task_id: string }>(`/admin/sources/crawl/run/${id}`);
    return data;
  },
  triggerAll: async (): Promise<{ task_id: string }> => {
    const { data } = await adminApi.post<{ task_id: string }>("/admin/sources/crawl/run-all");
    return data;
  },
  crawlRuns: async (): Promise<CrawlRun[]> => {
    const { data } = await adminApi.get<CrawlRun[]>("/admin/sources/crawl/runs");
    return data;
  },

  // Events
  listEvents: async (page = 1, limit = 50, q?: string): Promise<AdminEventListResponse> => {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) });
    if (q) params.set("q", q);
    const { data } = await adminApi.get<AdminEventListResponse>(`/admin/events?${params}`);
    return data;
  },
  updateEvent: async (id: string, payload: EventUpdate): Promise<AdminEvent> => {
    const { data } = await adminApi.put<AdminEvent>(`/admin/events/${id}`, payload);
    return data;
  },
  rescrapeEvent: async (id: string): Promise<{ task_id: string }> => {
    const { data } = await adminApi.post<{ task_id: string }>(`/admin/events/${id}/rescrape`);
    return data;
  },
  featureEvent: async (id: string, featured: boolean): Promise<AdminEvent> => {
    const { data } = await adminApi.patch<AdminEvent>(`/admin/events/${id}/feature`, null, {
      params: { featured },
    });
    return data;
  },
  cancelEvent: async (id: string): Promise<AdminEvent> => {
    const { data } = await adminApi.patch<AdminEvent>(`/admin/events/${id}/cancel`);
    return data;
  },
  deleteEvent: async (id: string): Promise<void> => {
    await adminApi.delete(`/admin/events/${id}`);
  },

  // Moderation
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

  // Discovery
  runDiscovery: async (): Promise<{ task_id: string }> => {
    const { data } = await adminApi.post<{ task_id: string }>("/admin/discovery/run");
    return data;
  },
  runCustomDiscovery: async (queries: string[]): Promise<{ task_id: string }> => {
    const { data } = await adminApi.post<{ task_id: string }>("/admin/discovery/run-custom", { custom_queries: queries });
    return data;
  },
  submitUrl: async (event_url: string): Promise<{ submission_id: string }> => {
    const { data } = await adminApi.post<{ submission_id: string }>(`/admin/discovery/submit-url`, null, {
      params: { event_url },
    });
    return data;
  },
};
