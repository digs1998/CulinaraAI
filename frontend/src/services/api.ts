import axios from 'axios';
import { ChatRequest, ChatResponse, Recipe } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const feastronAPI = {
  // Health check
  healthCheck: async () => {
    const response = await api.get('/');
    return response.data;
  },

  // Get database statistics
  getStats: async () => {
    const response = await api.get('/api/stats');
    return response.data;
  },

  // Main chat endpoint
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/api/chat', request);
    return response.data;
  },

  // Search recipes
  searchRecipes: async (query: string, topK: number = 5) => {
    const response = await api.post('/api/search', {
      query,
      top_k: topK,
    });
    return response.data;
  },

  // Get recipe details
  getRecipe: async (recipeId: string) => {
    const response = await api.get(`/api/recipe/${recipeId}`);
    return response.data;
  },

  // Get similar recipes
  getSimilarRecipes: async (recipeId: string, topK: number = 5) => {
    const response = await api.get(`/api/similar/${recipeId}?top_k=${topK}`);
    return response.data;
  },
};

export default feastronAPI;