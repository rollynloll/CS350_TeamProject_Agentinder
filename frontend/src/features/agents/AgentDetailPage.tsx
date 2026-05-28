import { Link, useParams } from "react-router-dom";
import { BarChart3, Pencil, Share2 } from "lucide-react";
import { useAgentProfile } from "@/api/endpoints/agents";
import { Avatar } from "@/design-system/components/Avatar";
import { Button } from "@/design-system/components/Button";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TrustBadge } from "@/design-system/components/TrustBadge";

export function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const query = useAgentProfile(agentId);

  return (
    <QueryBoundary query={query}>
      {(profile) => (
        <>
          <MobileHeader showBack title="Profile Details" />
          <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 flex flex-col gap-4">
            <article className="rounded-2xl bg-surface shadow-card p-5 flex flex-col gap-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-bold tracking-tight">
                  {profile.displayName}
                </h2>
                <TrustBadge score={profile.trustScore} />
              </div>

              <div className="aspect-square w-full overflow-hidden rounded-xl bg-surface-2">
                <Avatar
                  src={profile.avatarUrl}
                  name={profile.displayName}
                  size="xl"
                  className="!w-full !h-full !rounded-xl !text-4xl"
                />
              </div>

              <p className="text-sm text-text-muted leading-relaxed">
                {profile.bio}
              </p>

              {profile.capabilityTags.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {profile.capabilityTags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center rounded-full bg-surface-2 px-3 py-1 text-xs font-medium text-text-muted"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>

            <div className="grid grid-cols-3 gap-2">
              <Button asChild variant="secondary" size="md" className="gap-1.5">
                <Link to={`/agents/${profile.agentId}/edit`}>
                  <Pencil className="w-4 h-4" /> Edit
                </Link>
              </Button>
              <Button asChild variant="secondary" size="md" className="gap-1.5">
                <Link to="/analytics">
                  <BarChart3 className="w-4 h-4" /> Analysis
                </Link>
              </Button>
              <Button variant="secondary" size="md" aria-label="Share profile">
                <Share2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </QueryBoundary>
  );
}
