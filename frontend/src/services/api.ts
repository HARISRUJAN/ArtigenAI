import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Handle 401 Unauthorized responses - clear invalid token
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token is invalid or expired, clear it
      // Only log if it's not an expected auth check (to reduce console noise)
      const isAuthCheck = error.config?.url?.includes('/auth/me');
      if (!isAuthCheck) {
        console.warn('Unauthorized request - token cleared');
      }
      localStorage.removeItem('auth_token');
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const response = await axios.post(`${API_BASE_URL}/auth/login`, params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
    }
    return response.data;
  },
  
  logout: () => {
    localStorage.removeItem('auth_token');
  },
  
  getMe: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
};

// Search API
export const searchAPI = {
  query: async (question: string, topK: number = 5) => {
    const response = await apiClient.post('/search/query', {
      question,
      top_k: topK,
    });
    return response.data;
  },
};

// Content API
export const contentAPI = {
  ingest: async (document: {
    title: string;
    source: string;
    url?: string;
    content: string;
    metadata?: Record<string, any>;
  }) => {
    const response = await apiClient.post('/content/ingest', document);
    return response.data;
  },
};

// Admin API
export const adminAPI = {
  getOrigins: async () => {
    const response = await apiClient.get('/admin/origins');
    return response.data;
  },
  
  createOrigin: async (origin: {
    name: string;
    url: string;
    frequency_hours?: number;
    enabled?: boolean;
    country_code?: string | null;
    topic_tags?: string[];
    crawl_priority?: number;
    allowed_path_patterns?: string[];
    excluded_path_patterns?: string[];
    sitemap_url?: string | null;
  }) => {
    const response = await apiClient.post('/admin/origins', origin);
    return response.data;
  },
  
  updateOrigin: async (id: number, origin: {
    name?: string;
    url?: string;
    frequency_hours?: number;
    enabled?: boolean;
  }) => {
    const response = await apiClient.put(`/admin/origins/${id}`, origin);
    return response.data;
  },
  
  deleteOrigin: async (id: number) => {
    await apiClient.delete(`/admin/origins/${id}`);
  },
  
  getOriginStatus: async (id: number) => {
    const response = await apiClient.get(`/admin/origins/${id}/status`);
    return response.data;
  },
  
  getHealth: async () => {
    const response = await apiClient.get('/admin/health');
    return response.data;
  },
  
  triggerCrawl: async (originId: number) => {
    const response = await apiClient.post(`/admin/origins/${originId}/crawl`);
    return response.data;
  },
};

// Dashboard API
export const dashboardAPI = {
  getOverview: async () => {
    const response = await apiClient.get('/admin/dashboard/overview');
    return response.data;
  },
  
  getOverviewTimeseries: async (days: number = 7) => {
    const response = await apiClient.get(`/admin/dashboard/overview/timeseries?days=${days}`);
    return response.data;
  },
  
  getOrigins: async () => {
    const response = await apiClient.get('/admin/dashboard/origins');
    return response.data;
  },
  
  getOrigin: async (id: number) => {
    const response = await apiClient.get(`/admin/dashboard/origins/${id}`);
    return response.data;
  },
  
  updateOriginConfig: async (id: number, config: {
    enabled?: boolean;
    frequency_hours?: number;
    max_pages_per_run?: number;
    max_depth?: number;
    priority_score_threshold?: number;
  }) => {
    const response = await apiClient.patch(`/admin/dashboard/origins/${id}/config`, config);
    return response.data;
  },
  
  getJobs: async (filters?: {
    origin_id?: number;
    status?: string;
    date_from?: string;
    date_to?: string;
    mode?: string;
    page?: number;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString());
        }
      });
    }
    const response = await apiClient.get(`/admin/dashboard/jobs?${params.toString()}`);
    return response.data;
  },
  
  getJob: async (jobId: string) => {
    const response = await apiClient.get(`/admin/dashboard/jobs/${jobId}`);
    return response.data;
  },
  
  getDocuments: async (filters?: {
    origin_id?: number;
    source_type?: string;
    date_from?: string;
    date_to?: string;
    relevance_flag?: string;
    has_duplicates?: boolean;
    page?: number;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString());
        }
      });
    }
    const response = await apiClient.get(`/admin/dashboard/documents?${params.toString()}`);
    return response.data;
  },
  
  getDocument: async (id: number) => {
    const response = await apiClient.get(`/admin/dashboard/documents/${id}`);
    return response.data;
  },
  
  getSettings: async () => {
    const response = await apiClient.get('/admin/dashboard/settings');
    return response.data;
  },
  
  updateSettings: async (settings: {
    crawling?: Record<string, any>;
    realtime_web?: Record<string, any>;
    rag?: Record<string, any>;
    data_retention?: Record<string, any>;
  }) => {
    const response = await apiClient.patch('/admin/dashboard/settings', settings);
    return response.data;
  },
};

export default apiClient;

