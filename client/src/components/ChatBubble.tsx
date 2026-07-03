import type { Message } from '../types';
import { CitationCard } from './CitationCard';
import { ConfidenceBadge } from './ConfidenceBadge';

interface ChatBubbleProps {
  message: Message;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isAssistant = message.role === 'assistant';
  const isPending = isAssistant && message.pending && !message.content;

  return (
    <article className={`chat-bubble ${isAssistant ? 'assistant-bubble' : 'user-bubble'}`}>
      <div className="bubble-header">
        <span>{isAssistant ? 'Tutor' : 'You'}</span>
        {isAssistant ? <ConfidenceBadge confidence={message.confidence} refused={message.refused} /> : null}
      </div>
      {isPending ? (
        <div className="thinking-indicator" aria-label="Tutor is preparing a response">
          <span />
          <span />
          <span />
        </div>
      ) : (
        <p className="bubble-text">{message.content}</p>
      )}
      {isAssistant && message.citations.length > 0 ? (
        <div className="citation-list" aria-label="Citations">
          {message.citations.map((citation, index) => (
            <CitationCard key={citation.chunk_id} citation={citation} index={index} />
          ))}
        </div>
      ) : null}
    </article>
  );
}
