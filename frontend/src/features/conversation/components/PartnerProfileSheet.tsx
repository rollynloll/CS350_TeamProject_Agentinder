import { useAgentProfile } from "@/api/endpoints/agents";
import { AgentDetailSheet } from "@/features/feed/components/AgentDetailSheet";
import type { AgentId, FeedCard } from "@/api/types";

/**
 * "View partner profile" from the conversation menu opens the same detail
 * profile card as the feed (AgentDetailSheet), built from the partner's full
 * agent profile.
 */
export function PartnerProfileSheet({
  agentId,
  open,
  onOpenChange,
}: {
  agentId?: AgentId;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: p } = useAgentProfile(open ? agentId : undefined);

  const card: FeedCard | null = p
    ? {
        agentId: p.agentId,
        displayName: p.displayName,
        avatarUrl: p.avatarUrl,
        bioSnippet: p.bio,
        bio: p.bio,
        topTags: p.capabilityTags,
        compatibilityScore: 0.78,
        trustScore: p.trustScore,
        trustBadge: p.trustBadge,
        interactionStyle: p.interactionStyle,
        availabilityStatus: "available",
        styleSliders: {
          formalCasual: (p.styleCasual ?? 50) / 100,
          verboseConcise: (p.styleDetail ?? 50) / 100,
          cautiousBold: (p.styleBold ?? 50) / 100,
        },
        trustBreakdown:
          p.trustScore != null
            ? {
                peerRating: Math.round(p.trustScore * 50) / 10,
                taskCompletion: p.trustScore,
                responseLatency: "1.4s (avg)",
                hallucinationIncidents: 1,
                authorizationVerified: true,
                basedOnDates: 12,
              }
            : undefined,
        endorsements: [
          {
            agentId: "ag_endorse_1",
            displayName: "Scheduler",
            avatarUrl: "https://api.dicebear.com/9.x/bottts/svg?seed=Scheduler",
            tier: "trusted_partner",
            text: "Reliable and sharp on every task we worked through together. Quick to grasp context and consistently delivered usable results.",
          },
        ],
      }
    : null;

  return <AgentDetailSheet card={card} open={open && card != null} onOpenChange={onOpenChange} />;
}
