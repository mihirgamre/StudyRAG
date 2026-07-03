import { ArrowLeft, Send } from 'lucide-react';
import { FormEvent, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { ChatBubble } from '../components/ChatBubble';
import type { Conversation, Course, Message, StreamFinalPayload } from '../types';

interface ChatPageProps {
  token: string;
  course: Course;
  onBack: () => void;
}

export function ChatPage({ token, course, onBack }: ChatPageProps) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamIdRef = useRef<string | null>(null);

  useEffect(() => {
    async function startConversation() {
      const created = await api.createConversation(token, course.id);
      setConversation(created);
      setMessages(await api.listMessages(token, created.id));
    }
    void startConversation().catch((err) => setError(err instanceof Error ? err.message : 'Could not start chat'));
  }, [course.id, token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!conversation || !draft.trim() || streaming) {
      return;
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: draft.trim(),
      citations: [],
    };
    const assistantId = crypto.randomUUID();
    streamIdRef.current = assistantId;
    setMessages((current) => [
      ...current,
      userMessage,
      {
        id: assistantId,
        role: 'assistant',
        content: '',
        citations: [],
      },
    ]);
    setDraft('');
    setStreaming(true);
    setError(null);

    try {
      await api.streamMessage(token, conversation.id, userMessage.content, {
        onToken: (text) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === streamIdRef.current ? { ...message, content: `${message.content}${text}` } : message,
            ),
          );
        },
        onFinal: (payload: StreamFinalPayload) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === streamIdRef.current
                ? {
                    ...message,
                    id: payload.message_id,
                    content: payload.answer,
                    citations: payload.citations,
                    confidence: payload.confidence,
                    refused: payload.refused,
                  }
                : message,
            ),
          );
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Message failed');
    } finally {
      setStreaming(false);
      streamIdRef.current = null;
    }
  }

  return (
    <main className="chat-shell">
      <header className="topbar chat-topbar">
        <button className="icon-button" type="button" onClick={onBack} aria-label="Back to course">
          <ArrowLeft size={18} aria-hidden />
        </button>
        <div>
          <h1>{course.name}</h1>
          <p>Chat</p>
        </div>
      </header>

      <section className="message-list" aria-label="Conversation">
        {messages.map((message) => (
          <ChatBubble key={message.id} message={message} />
        ))}
      </section>

      <form className="composer" onSubmit={submit}>
        {error ? <p className="form-error">{error}</p> : null}
        <textarea value={draft} rows={2} onChange={(event) => setDraft(event.target.value)} placeholder="Ask from your course materials" />
        <button className="primary-button send-button" type="submit" disabled={streaming || !conversation}>
          <Send size={16} aria-hidden />
          Send
        </button>
      </form>
    </main>
  );
}
