import { useRelationships } from "@/api/endpoints/relationships";
import { useAuth } from "@/store/auth";
import { ProfileTabs } from "@/design-system/components/ProfileTabs";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TopBar } from "@/design-system/components/TopBar";
import type { Tier } from "@/api/types";
import { RelationshipCard } from "./components/RelationshipCard";

const tierLabel: Record<Tier, string> = {
  trusted_partner: "Trusted Partner",
  colleague: "Colleague",
  acquaintance: "Acquaintance",
  stranger: "Stranger",
};

const tierBg: Record<Tier, string> = {
  trusted_partner: "bg-tier-trusted-bg text-tier-trusted-text",
  colleague: "bg-tier-colleague-bg text-tier-colleague-text",
  acquaintance: "bg-tier-acquaintance-bg text-tier-acquaintance-text",
  stranger: "bg-tier-stranger-bg text-tier-stranger-text",
};

// Figma summary order: Trusted Partner → Acquaintance → Stranger.
const tierOrder: Tier[] = ["trusted_partner", "colleague", "acquaintance", "stranger"];

export function RelationshipsPage() {
  const { activeAgentId } = useAuth();
  const query = useRelationships(activeAgentId ?? undefined);

  return (
    <>
      <TopBar />
      <ProfileTabs />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-4">
        <QueryBoundary query={query}>
          {(data) => {
            const groups = [...data.groups].sort(
              (a, b) => tierOrder.indexOf(a.tier) - tierOrder.indexOf(b.tier),
            );
            return (
              <>
                {/* Tier Summary (Figma node 2061:1145) */}
                <section className="rounded-[12px] bg-bg shadow-float px-3 py-2 flex flex-col gap-3">
                  <h2 className="text-h3 font-semibold text-text">Tier Summary</h2>
                  <div className="flex gap-2 items-stretch">
                    {groups.map((g) => (
                      <div
                        key={g.tier}
                        className={`flex-1 min-w-0 flex flex-col items-center justify-center gap-2.5 rounded-[8px] px-2 py-3 ${tierBg[g.tier]}`}
                      >
                        <span className="text-caption font-semibold text-center leading-[1.4]">
                          {tierLabel[g.tier]}
                        </span>
                        <span className="text-display font-semibold tabular-nums">
                          {g.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Grouped relationship lists */}
                {groups.map((g) => (
                  <section key={g.tier} className="space-y-3">
                    <h2 className="text-h3 font-semibold text-text">{tierLabel[g.tier]}</h2>
                    {g.relationships.map((r) => (
                      <RelationshipCard key={r.matchId} item={r} />
                    ))}
                  </section>
                ))}
              </>
            );
          }}
        </QueryBoundary>
      </div>
    </>
  );
}
