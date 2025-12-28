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
  role: "user" | "assistant";
  content: string;
  recipes?: any[];
  facts?: string[];
}


export interface ChatResponse {
  response: string;
  recipes: Recipe[];
  facts?: string[];
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}