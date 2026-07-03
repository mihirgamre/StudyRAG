import { AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import type { DocumentStatus } from '../types';

interface DocumentStatusIndicatorProps {
  status: DocumentStatus;
}

export function DocumentStatusIndicator({ status }: DocumentStatusIndicatorProps) {
  const Icon = status === 'embedded' ? CheckCircle2 : status === 'failed' ? AlertCircle : status === 'pending' ? Clock : Loader2;
  return (
    <span className={`document-status status-${status}`}>
      <Icon size={14} aria-hidden />
      {status}
    </span>
  );
}
