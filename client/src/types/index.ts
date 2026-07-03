export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface Course {
  id: string;
  name: string;
}

export type DocumentStatus = 'pending' | 'chunked' | 'embedded' | 'failed';

export interface CourseDocument {
  id: string;
  filename: string;
  source_type: string;
  status: DocumentStatus;
  storage_url: string | null;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  section_heading: string | null;
  snippet: string;
  relevance_score: number;
  storage_url?: string | null;
}

export interface Conversation {
  id: string;
  course_id: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  confidence?: number;
  refused?: boolean;
  pending?: boolean;
}

export interface StreamFinalPayload {
  message_id: string;
  answer: string;
  citations: Citation[];
  confidence: number;
  refused: boolean;
}
