import type { Message } from '../types';
import { CitationCard } from './CitationCard';
import { ConfidenceBadge } from './ConfidenceBadge';

interface ChatBubbleProps {
  message: Message;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isAssistant = message.role === 'assistant';

  return (
    <article className={`chat-bubble ${isAssistant ? 'assistant-bubble' : 'user-bubble'}`}>
      <div className="bubble-header">
        <span>{isAssistant ? 'Tutor' : 'You'}</span>
        {isAssistant ? <ConfidenceBadge confidence={message.confidence} refused={message.refused} /> : null}
      </div>
      <p className="bubble-text">{message.content}</p>
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
