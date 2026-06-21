import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token && config.headers) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: async (username: string, password: string): Promise<string> => {
    const params = new URLSearchParams({ username, password });
    const { data } = await apiClient.post<{ access_token: string }>('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    localStorage.setItem('access_token', data.access_token);
    return data.access_token;
  },
  logout: () => localStorage.removeItem('access_token'),
};

export type ViolationStatus = 'pending' | 'approved' | 'rejected';
export type ViolationListItem = {
  id: string;
  violation_type: string;
  plate_number: string | null;
  timestamp: string;
  status: ViolationStatus;
  image_url: string;
};

export type PageMeta = { total: number; page: number; limit: number };

export type ViolationListResponse = { data: ViolationListItem[]; meta: PageMeta };

export type ViolationBoundingBoxes = {
  vehicles?: { x: number; y: number; w: number; h: number; label?: string }[];
  helmets?: { x: number; y: number; w: number; h: number; label?: string }[];
  plates?: { x: number; y: number; w: number; h: number; label?: string }[];
  violations?: { x: number; y: number; w: number; h: number; label?: string }[];
  rider_seats?: { x: number; y: number; w: number; h: number; label?: string }[];
  cargo?: { x: number; y: number; w: number; h: number; label?: string }[];
  direction_arrow?: { x: number; y: number; w: number; h: number; label?: string };
  stop_line?: { x: number; y: number; w: number; h: number; label?: string };
};

export type ViolationDetailItem = {
  id: string;
  violation_type: string;
  vehicle_type: string | null;
  plate_number: string | null;
  confidence_score: number | null;
  status: ViolationStatus;
  image_url: string;
  plate_image_url: string | null;
  camera_id: string | null;
  job_id: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  timestamp: string;
  bounding_boxes?: ViolationBoundingBoxes;
};

// ── Violations ────────────────────────────────────────────────────────────────
export const violationsApi = {
  list: async (params: {
    page?: number;
    limit?: number;
    status?: string;
    camera_id?: string;
    violation_type?: string;
    plate?: string;
  }): Promise<ViolationListResponse> => {
    const { data } = await apiClient.get<ViolationListResponse>('/violations', { params });
    return data;
  },

  get: async (id: string): Promise<ViolationDetailItem> => {
    const { data } = await apiClient.get<ViolationDetailItem>(`/violations/${id}`);
    return data;
  },

  updateStatus: async (
    id: string,
    payload: { status: ViolationStatus; notes?: string }
  ): Promise<void> => {
    await apiClient.patch(`/violations/${id}/status`, payload);
  },
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export type AnalyticsSummary = {
  total_violations: number;
  by_type: Record<string, number>;
};

export const analyticsApi = {
  summary: async (params?: { date_from?: string; date_to?: string }): Promise<AnalyticsSummary> => {
    const { data } = await apiClient.get<AnalyticsSummary>('/analytics/summary', { params });
    return data;
  },
};

export default apiClient;