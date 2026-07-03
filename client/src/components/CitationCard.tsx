import { ExternalLink } from 'lucide-react';
import { useState } from 'react';
import type { Citation } from '../types';

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const sourceUrl = citation.storage_url ? withPageAnchor(citation.storage_url, citation.page_number) : null;

  return (
    <div className="citation">
      <button
        className="citation-chip"
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
      >
        <span>[{index + 1}]</span>
        <span>{citation.filename}</span>
        {citation.page_number ? <span>p.{citation.page_number}</span> : null}
      </button>

      {expanded ? (
        <div className="citation-panel">
          <div className="citation-meta">
            <strong>{citation.section_heading ?? 'Source excerpt'}</strong>
            <span>{Math.round(citation.relevance_score * 100)}% match</span>
          </div>
          <div className="citation-source-line">
            <span>{citation.filename}</span>
            {citation.page_number ? <span>Page {citation.page_number}</span> : null}
          </div>
          <p>{citation.snippet}</p>
          {sourceUrl ? (
            <a className="source-link" href={sourceUrl} target="_blank" rel="noreferrer">
              <ExternalLink size={14} aria-hidden />
              Open source
            </a>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function withPageAnchor(url: string, page: number | null) {
  if (!page || !url.toLowerCase().includes('.pdf')) {
    return url;
  }
  return `${url}#page=${page}`;
}
