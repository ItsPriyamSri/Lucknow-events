import axios from "axios";

const DEFAULT_API_URL = "http://localhost:8000/api/v1";

function resolveBaseUrl(): string {
  // Browser: always go through Next.js rewrite (/api/v1/*).
  // Server (SSR/ISR/build): use INTERNAL_API_URL when available, else NEXT_PUBLIC_API_URL.
  if (typeof window !== "undefined") return "/api/v1";
  return process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
}

const api = axios.create({
  baseURL: resolveBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

export interface Event {
  id: string;
  slug: string;
  title: string;
  start_at: string;
  end_at: string | null;
  venue: string | null;
  locality: string | null;
  mode: "offline" | "online" | "hybrid" | string | null;
  event_type: string | null;
  community_name: string | null;
  organizer_name: string | null;
  poster_url: string | null;
  canonical_url: string;
  registration_url: string | null;
  is_free: boolean;
  is_student_friendly: boolean;
  topics: string[];
  audience?: string[];
  short_description?: string | null;
  description?: string | null;
  updated_at?: string;
}

export interface EventsResponse {
  items: Event[];
  total: number;
  page: number;
  limit: number;
}

export interface FacetItem {
  name: string;
  count: number;
}

export interface FacetsResponse {
  items: FacetItem[];
}

export const fetcher = (url: string) => api.get(url).then((res) => res.data);

export const facetService = {
  getTopics: async (): Promise<FacetItem[]> => {
    const { data } = await api.get<FacetsResponse>("/topics");
    return data.items;
  },
  getCommunities: async (): Promise<FacetItem[]> => {
    const { data } = await api.get<FacetsResponse>("/communities");
    return data.items;
  },
  getLocalities: async (): Promise<FacetItem[]> => {
    const { data } = await api.get<FacetsResponse>("/localities");
    return data.items;
  },
};

export const eventService = {
  getEvents: async (params?: Record<string, unknown>): Promise<EventsResponse> => {
    const { data } = await api.get<EventsResponse>("/events", { params });
    return data;
  },

  getEvent: async (slug: string): Promise<Event> => {
    const { data } = await api.get<Event>(`/events/${slug}`);
    return data;
  },

  getFeatured: async (): Promise<Event[]> => {
    const { data } = await api.get<Event[]>("/events/featured");
    return data;
  },

  getThisWeek: async (): Promise<Event[]> => {
    const { data } = await api.get<Event[]>("/events/this-week");
    return data;
  },

  getStudentFriendly: async (): Promise<Event[]> => {
    const { data } = await api.get<Event[]>("/events/student-friendly");
    return data;
  },

  submitEvent: async (payload: { url: string }): Promise<void> => {
    await api.post("/submissions", { event_url: payload.url });
  },
};
