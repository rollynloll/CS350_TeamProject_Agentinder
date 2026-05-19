import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useConversation } from "@/api/endpoints/messages";
import { useTopic } from "@/api/ws/hooks";
import { topics, type ChatTopicEvent } from "@/api/ws/topics";
import type { ChatMessage, WsFrame } from "@/api/types";
import { Card, CardBody } from "@/design-system/components/Card";
import { PageHeader } from "@/design-system/components/PageHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TierBadge } from "@/design-system/components/TierBadge";

export function ConversationPage() {
  const { t } = useTranslation();
  const { matchId } = useParams<{ matchId: string }>();
  const query = useConversation(matchId);

  const [live, setLive] = useState<ChatMessage[]>([]);
  useEffect(() => setLive([]), [matchId]);

  const onFrame = useCallback((frame: WsFrame) => {
    const payload = frame.payload as ChatTopicEvent | undefined;
    if (payload?.kind === "message") {
      setLive((prev) => [...prev, payload.message]);
    }
  }, []);
  useTopic(matchId ? topics.chat(matchId) : null, onFrame);

  return (
    <>
      <PageHeader title={t("conversation.title")} />
      <QueryBoundary query={query}>
        {(data) => {
          const merged: ChatMessage[] = [...data.messages, ...live];
          return (
            <Card>
              <CardBody className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium">
                    {data.matchInfo.partnerAgent.displayName}
                  </div>
                  <TierBadge tier={data.matchInfo.tier} />
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
                <p className="text-xs text-text-muted">{t("common.scaffold_notice")}</p>
              </CardBody>
            </Card>
          );
        }}
      </QueryBoundary>
    </>
  );
}
