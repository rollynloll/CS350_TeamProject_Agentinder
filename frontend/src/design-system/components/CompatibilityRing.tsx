/**
 * REQ-0208 + CO-5: shows compatibility as 0–100. The "Why this match?" UI
 * is rendered by the consumer; this component only renders the ring + number.
 */
export function CompatibilityRing({ score }: { score: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  const stroke = 6;
  const radius = 24;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={56} height={56} className="-rotate-90">
        <circle
          cx={28}
          cy={28}
          r={radius}
          stroke="currentColor"
          className="text-border"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={28}
          cy={28}
          r={radius}
          stroke="currentColor"
          className="text-primary"
          strokeWidth={stroke}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-body1 font-semibold tabular-nums">{pct}</span>
    </div>
  );
}
