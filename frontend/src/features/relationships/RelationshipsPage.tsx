import { useTranslation } from "react-i18next";
import { useRelationships } from "@/api/endpoints/relationships";
import { useAuth } from "@/store/auth";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { RelationshipCard } from "./components/RelationshipCard";

// Hash-based compat stand-in until API spec carries the score per relationship.
function pseudoCompat(matchId: string): number {
  let h = 0;
  for (let i = 0; i < matchId.length; i += 1) h = (h * 31 + matchId.charCodeAt(i)) | 0;
  return 30 + (Math.abs(h) % 60);
}

export function RelationshipsPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useRelationships(activeAgentId ?? undefined);

  return (
    <>
      <MobileHeader title={t("relationships.title")} />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        <QueryBoundary query={query}>
          {(data) => (
            <>
              {data.groups.flatMap((group) =>
                group.relationships.map((r) => (
                  <RelationshipCard
                    key={r.matchId}
                    item={r}
                    compatibilityScore={pseudoCompat(r.matchId)}
                  />
                )),
              )}
            </>
          )}
        </QueryBoundary>
      </div>
    </>
  );
}
