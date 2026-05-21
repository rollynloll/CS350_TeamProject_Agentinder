import { Plus } from "lucide-react";
import { useSettings } from "@/api/endpoints/settings";
import { Button } from "@/design-system/components/Button";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";

export function ApiKeysPage() {
  const query = useSettings();

  return (
    <>
      <MobileHeader showBack title="API Key Management" />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        <QueryBoundary query={query}>
          {(s) => (
            <>
              <section className="rounded-2xl bg-surface shadow-card divide-y divide-border">
                {s.apiKeys.length === 0 ? (
                  <div className="px-4 py-6 text-center text-sm text-text-muted">
                    No API keys yet.
                  </div>
                ) : (
                  s.apiKeys.map((k) => (
                    <div
                      key={k.keyId}
                      className="flex items-center justify-between px-4 py-3 text-sm"
                    >
                      <div className="min-w-0">
                        <div className="font-medium text-text">{k.name}</div>
                        <div className="text-xs text-text-muted">
                          {k.lastUsedAt
                            ? `Last used ${new Date(k.lastUsedAt).toLocaleDateString()}`
                            : "Never used"}
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        Revoke
                      </Button>
                    </div>
                  ))
                )}
              </section>
              <Button variant="primary" size="md" className="w-full gap-1.5">
                <Plus className="w-4 h-4" /> Add new key
              </Button>
            </>
          )}
        </QueryBoundary>
      </div>
    </>
  );
}
