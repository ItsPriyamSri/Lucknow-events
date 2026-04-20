import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Event {
  id: string;
  source_id: string;
  slug: string;
  title: string;
  start_at: string;
  end_at: string;
  venue: string | null;
  locality: string | null;
  mode: 'offline' | 'online' | 'hybrid';
  event_type: string;
  community_name: string | null;
  organizer_name: string | null;
  poster_url: string | null;
  canonical_url: string;
  registration_url: string | null;
  is_free: boolean;
  is_student_friendly: boolean;
  audience: string | null;
  topics: string[];
}

export interface EventsResponse {
  items: Event[];
  total: number;
  page: number;
  limit: number;
}

export const fetcher = (url: string) => api.get(url).then((res) => res.data);

export const eventService = {
  getEvents: async (params?: Record<string, any>): Promise<EventsResponse> => {
    const { data } = await api.get<EventsResponse>('/events', { params });
    return data;
  },
  
  getEvent: async (slug: string): Promise<Event> => {
    const { data } = await api.get<Event>(`/events/${slug}`);
    return data;
  },

  getFeatured: async (): Promise<Event[]> => {
    const { data } = await api.get<Event[]>('/events/featured');
    return data;
  },

  getThisWeek: async (): Promise<Event[]> => {
    const { data } = await api.get<Event[]>('/events/this-week');
    return data;
  },

  getStudentFriendly: async (): Promise<Event[]> => {
    const { data } = await api.get<Event[]>('/events/student-friendly');
    return data;
  },

  submitEvent: async (payload: { url: string; poster?: File }): Promise<void> => {
    const formData = new FormData();
    formData.append('url', payload.url);
    if (payload.poster) {
      formData.append('poster', payload.poster);
    }
    // Using slowapi, so we must handle 429
    await api.post('/submissions', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  }
};
