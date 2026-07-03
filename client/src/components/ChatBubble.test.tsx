import { fireEvent, render, screen } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { ChatBubble } from './ChatBubble';
import type { Message } from '../types';

function citation(index: number) {
  return {
    chunk_id: `chunk-${index}`,
    document_id: `doc-${index}`,
    filename: `source-${index}.pdf`,
    page_number: index,
    section_heading: `Section ${index}`,
    snippet: `Grounded excerpt ${index}`,
    relevance_score: 0.72,
    storage_url: `https://files.example.test/source-${index}.pdf`,
  };
}

describe('ChatBubble', () => {
  it('renders streamed assistant content with confidence and multiple citations', () => {
    const message: Message = {
      id: 'assistant-1',
      role: 'assistant',
      content: 'Differentiation estimates instantaneous change from the local slope.',
      confidence: 0.74,
      refused: false,
      citations: [citation(1), citation(2), citation(3), citation(4)],
    };

    render(<ChatBubble message={message} />);

    expect(screen.getByText('Tutor')).toBeInTheDocument();
    expect(screen.getByText(/instantaneous change/i)).toBeInTheDocument();
    expect(screen.getByText(/high confidence 74%/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Citations')).toHaveClass('citation-list');
    expect(screen.getAllByRole('button', { name: /\[\d\].*source-\d\.pdf/i })).toHaveLength(4);

    fireEvent.click(screen.getByRole('button', { name: /\[4\].*source-4\.pdf.*p\.4/i }));
    expect(screen.getByText('Grounded excerpt 4')).toBeInTheDocument();
  });

  it('keeps top_k=4 citation chips wrap-capable instead of forcing horizontal overflow', () => {
    const styles = readFileSync('src/styles.css', 'utf-8');

    expect(styles).toMatch(/\.citation-list\s*{[^}]*display:\s*flex;[^}]*flex-wrap:\s*wrap;/s);
    expect(styles).toMatch(/\.citation-chip\s*{[^}]*max-width:\s*min\(100%,\s*260px\);/s);
    expect(styles).toMatch(/\.citation-chip span\s*{[^}]*min-width:\s*0;[^}]*text-overflow:\s*ellipsis;/s);
  });

  it('surfaces the refusal confidence state for low-support answers', () => {
    const message: Message = {
      id: 'assistant-refusal',
      role: 'assistant',
      content: 'I do not have enough information in the provided course materials to answer that.',
      confidence: 0.12,
      refused: true,
      citations: [],
    };

    render(<ChatBubble message={message} />);

    expect(screen.getByText(/not enough source support/i)).toBeInTheDocument();
    expect(screen.getByText(/not have enough information/i)).toBeInTheDocument();
  });

  it('shows a pending indicator before the first streamed token arrives', () => {
    const message: Message = {
      id: 'assistant-pending',
      role: 'assistant',
      content: '',
      citations: [],
      pending: true,
    };

    render(<ChatBubble message={message} />);

    expect(screen.getByLabelText('Tutor is preparing a response')).toBeInTheDocument();
  });
});
