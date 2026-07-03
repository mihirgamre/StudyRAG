import type {
  AuthResponse,
  Conversation,
  Course,
  CourseDocument,
  Message,
  StreamFinalPayload,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  token?: string | null;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`);
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const message = await readError(response);
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

export const api = {
  register: (email: string, password: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  demoLogin: () =>
    request<AuthResponse>('/auth/demo', {
      method: 'POST',
    }),

  createCourse: (token: string, name: string) =>
    request<Course>('/courses', {
      method: 'POST',
      token,
      body: JSON.stringify({ name }),
    }),

  listCourses: (token: string) => request<Course[]>('/courses', { token }),

  getCourse: (token: string, courseId: string) => request<Course>(`/courses/${courseId}`, { token }),

  listDocuments: (token: string, courseId: string) =>
    request<CourseDocument[]>(`/courses/${courseId}/documents`, { token }),

  uploadDocument: (token: string, courseId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<CourseDocument>(`/courses/${courseId}/documents`, {
      method: 'POST',
      token,
      body: form,
    });
  },

  getDocumentStatus: (token: string, documentId: string) =>
    request<CourseDocument>(`/documents/${documentId}/status`, { token }),

  createConversation: (token: string, courseId: string) =>
    request<Conversation>(`/courses/${courseId}/conversations`, {
      method: 'POST',
      token,
    }),

  listMessages: (token: string, conversationId: string) =>
    request<Message[]>(`/conversations/${conversationId}/messages`, { token }),

  streamMessage: async (
    token: string,
    conversationId: string,
    content: string,
    handlers: {
      onToken: (text: string) => void;
      onFinal: (payload: StreamFinalPayload) => void;
    },
  ) => {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      const message = await readError(response);
      throw new ApiError(response.status, message);
    }
    if (!response.body) {
      throw new ApiError(0, 'Streaming response was empty');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';
      for (const part of parts) {
        dispatchSseEvent(part, handlers);
      }
    }
    if (buffer.trim()) {
      dispatchSseEvent(buffer, handlers);
    }
  },
};

function dispatchSseEvent(
  block: string,
  handlers: {
    onToken: (text: string) => void;
    onFinal: (payload: StreamFinalPayload) => void;
  },
) {
  const lines = block.split(/\r?\n/);
  const event = lines.find((line) => line.startsWith('event: '))?.slice(7).trim();
  const dataLine = lines.find((line) => line.startsWith('data: '));
  if (!event || !dataLine) {
    return;
  }
  const payload = JSON.parse(dataLine.slice(6));
  if (event === 'token') {
    handlers.onToken(payload.text ?? '');
  }
  if (event === 'final') {
    handlers.onFinal(payload as StreamFinalPayload);
  }
}
