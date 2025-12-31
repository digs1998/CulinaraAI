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
  collection_pages?: CollectionPage[];
}

export interface CollectionPage {
  title: string;
  url: string;
}

export interface ChatResponse {
  response: string;
  recipes: Recipe[];
  facts?: string[];
  collection_pages?: CollectionPage[];
}

export interface UserPreferences {
  diets: string[];
  skill: string;
  servings: number;
  goal: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  preferences?: UserPreferences;
}