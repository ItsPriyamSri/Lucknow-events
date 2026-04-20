import axios from 'axios';

const adminApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ? `${process.env.NEXT_PUBLIC_API_URL}/admin` : "http://localhost:8000/api/v1/admin",
  headers: {
    "Content-Type": "application/json",
  },
});

adminApi.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('admin_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export interface ModerationItem {
  id: string;
  entity_type: string | null;
  entity_id: string | null;
  reason: string | null;
  severity: string | null;
  status: string;
  ai_verdict: Record<string, any> | null;
  notes: string | null;
  created_at: string;
}

export const adminService = {
  login: async (email: string, password: string):Promise<{access_token: string}> => {
    const { data } = await adminApi.post('/auth/login', { email, password });
    return data;
  },

  getPendingModeration: async (): Promise<ModerationItem[]> => {
    const { data } = await adminApi.get('/moderation');
    return data;
  },

  approveItem: async (itemId: string): Promise<ModerationItem> => {
    const { data } = await adminApi.post(`/moderation/${itemId}/approve`);
    return data;
  },

  rejectItem: async (itemId: string): Promise<ModerationItem> => {
    const { data } = await adminApi.post(`/moderation/${itemId}/reject`);
    return data;
  },
  
  getStats: async (): Promise<{events_total: number; events_this_week: number; pending_moderation: number; sources_active: number}> => {
      const { data } = await adminApi.get('/stats');
      return data;
  }
};
