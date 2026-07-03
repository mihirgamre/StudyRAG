interface ConfidenceBadgeProps {
  confidence?: number;
  refused?: boolean;
}

export function ConfidenceBadge({ confidence, refused }: ConfidenceBadgeProps) {
  if (refused) {
    return <span className="confidence confidence-refused">Not enough source support</span>;
  }
  if (confidence === undefined) {
    return null;
  }

  const level = confidence >= 0.65 ? 'High' : confidence >= 0.35 ? 'Medium' : 'Low';
  const className =
    confidence >= 0.65 ? 'confidence confidence-high' : confidence >= 0.35 ? 'confidence confidence-mid' : 'confidence confidence-low';

  return (
    <span className={className}>
      {level} confidence {Math.round(confidence * 100)}%
    </span>
  );
}
