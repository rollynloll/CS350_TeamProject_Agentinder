import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMatchDates } from "@/api/endpoints/relationships";
import { Card, CardBody } from "@/design-system/components/Card";
import { PageHeader } from "@/design-system/components/PageHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { Badge } from "@/design-system/components/Badge";

export function DateHistoryPage() {
  const { t } = useTranslation();
  const { matchId } = useParams<{ matchId: string }>();
  const query = useMatchDates(matchId);

  return (
    <>
      <PageHeader title={t("date_history.title")} />
      <QueryBoundary query={query}>
        {(data) => (
          <div className="space-y-3">
            <div className="text-sm text-text-muted">
              With {data.match.partnerAgent.displayName}
            </div>
            {data.dates.map((d) => (
              <Card key={d.dateId}>
                <CardBody className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-medium">{d.type}</div>
                    <div className="text-sm text-text-muted">{d.summary}</div>
                    <div className="text-xs text-text-muted mt-1">
                      {new Date(d.startedAt).toLocaleString()} · {d.durationMinutes} min
                    </div>
                  </div>
                  <div className="text-right space-y-1">
                    {d.outcome ? (
                      <Badge
                        tone={
                          d.outcome === "successful"
                            ? "trust"
                            : d.outcome === "neutral"
                              ? "info"
                              : "danger"
                        }
                      >
                        {d.outcome}
                      </Badge>
                    ) : null}
                    {d.mutualRating ? (
                      <div className="text-sm">★ {d.mutualRating.toFixed(1)}</div>
                    ) : null}
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </QueryBoundary>
      <p className="text-xs text-text-muted mt-4">{t("common.scaffold_notice")}</p>
    </>
  );
}
