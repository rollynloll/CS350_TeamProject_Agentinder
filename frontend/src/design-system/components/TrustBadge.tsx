import { Badge } from "./Badge";

/**
 * REQ-0504: agents with fewer than 5 dates display "New Agent" badge instead of
 * numeric score. REQ-0507: numeric score is shown to 2 decimals; tooltip carries
 * the breakdown (handled elsewhere).
 */
export function TrustBadge({ score }: { score: number | null | undefined }) {
  if (score == null) {
    return <Badge tone="info">New Agent</Badge>;
  }
  const tone = score >= 0.8 ? "success" : score >= 0.5 ? "primary" : "warning";
  return <Badge tone={tone}>Trust {score.toFixed(2)}</Badge>;
}
