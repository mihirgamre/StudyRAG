import { fireEvent, render, screen } from '@testing-library/react';
import { CitationCard } from './CitationCard';
import type { Citation } from '../types';

const citation: Citation = {
  chunk_id: 'chunk-1',
  document_id: 'doc-1',
  filename: 'calculus-notes.pdf',
  page_number: 3,
  section_heading: 'Limits and continuity',
  snippet: 'A limit describes the value a function approaches as the input moves toward a point.',
  relevance_score: 0.87,
  storage_url: 'https://files.example.test/calculus-notes.pdf',
};

describe('CitationCard', () => {
  it('expands a citation chip into source details and a page-aware source link', () => {
    render(<CitationCard citation={citation} index={1} />);

    const chip = screen.getByRole('button', { name: /\[2\].*calculus-notes\.pdf.*p\.3/i });
    expect(chip).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(chip);

    expect(chip).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Limits and continuity')).toBeInTheDocument();
    expect(screen.getByText('Page 3')).toBeInTheDocument();
    expect(screen.getByText(/value a function approaches/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open source/i })).toHaveAttribute(
      'href',
      'https://files.example.test/calculus-notes.pdf#page=3',
    );
  });
});
