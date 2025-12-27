export interface Recipe {
  id: string;
  title: string;
  category?: string;
  rating?: number;
  total_time?: string;
  url: string;
  score: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  recipes?: Recipe[];
}

export interface ChatResponse {
  message: string;
  recipes: Recipe[];
  sources: any[];
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}