import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLiveDate } from "@/api/endpoints/dates";
import { useTopic } from "@/api/ws/hooks";
import { topics, type DateTopicEvent } from "@/api/ws/topics";
import type { WsFrame } from "@/api/types";
import { Card, CardBody } from "@/design-system/components/Card";
import { PageHeader } from "@/design-system/components/PageHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { Button } from "@/design-system/components/Button";
import { Badge } from "@/design-system/components/Badge";

type LiveMessage = { messageId: string; senderId: string; content: string; sentAt: string };

export function DateLivePage() {
  const { t } = useTranslation();
  const { dateId } = useParams<{ dateId: string }>();
  const query = useLiveDate(dateId);

  const [streamed, setStreamed] = useState<LiveMessage[]>([]);
  useEffect(() => setStreamed([]), [dateId]);

  const onFrame = useCallback((frame: WsFrame) => {
    const payload = frame.payload as DateTopicEvent | undefined;
    if (payload?.kind === "date_message") {
      setStreamed((prev) => [...prev, payload.message]);
    }
  }, []);
  useTopic(dateId ? topics.date(dateId) : null, onFrame);

  return (
    <>
      <PageHeader
        title={t("date_live.title")}
        description={t("date_live.description")}
        action={
          <Button variant="danger" size="sm">
            {t("common.end_date")}
          </Button>
        }
      />
      <QueryBoundary query={query}>
        {(data) => {
          const merged = [...data.recentMessages, ...streamed];
          return (
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="md:col-span-2">
                <CardBody className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{data.partnerAgent.displayName}</span>
                    <Badge tone="primary">{data.type}</Badge>
                  </div>
                  <ul className="space-y-2">
                    {merged.map((m) => (
                      <li
                        key={m.messageId}
                        className="rounded-md bg-surface-2 px-3 py-2 text-sm"
                      >
                        <div className="text-xs text-text-muted">{m.senderId}</div>
                        <div>{m.content}</div>
                      </li>
                    ))}
                  </ul>
                </CardBody>
              </Card>
              <Card>
                <CardBody>
                  <div className="text-sm font-semibold mb-2">Icebreakers</div>
                  <ul className="space-y-2 text-sm">
                    {data.icebreakers.map((p, i) => (
                      <li key={i} className="rounded-md bg-surface-2 p-2">
                        {p}
                      </li>
                    ))}
                  </ul>
                  <div className="text-xs text-text-muted mt-3">
                    {data.elapsedMinutes} / {data.maxDurationMinutes} min
                  </div>
                </CardBody>
              </Card>
            </div>
          );
        }}
      </QueryBoundary>
      <p className="text-xs text-text-muted mt-4">{t("common.scaffold_notice")}</p>
    </>
  );
}
