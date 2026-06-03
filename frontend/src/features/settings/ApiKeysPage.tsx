import { Plus } from "lucide-react";
import { Button } from "@/design-system/components/Button";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { useSettingsStore } from "@/store/settings";
import { uuid } from "@/lib/uuid";

export function ApiKeysPage() {
  const apiKeys = useSettingsStore((s) => s.apiKeys);
  const addApiKey = useSettingsStore((s) => s.addApiKey);
  const removeApiKey = useSettingsStore((s) => s.removeApiKey);

  const addQuick = () => {
    const n = apiKeys.length + 1;
    addApiKey({
      keyId: uuid(),
      name: `Key #${n}`,
      lastUsedAt: null,
      createdAt: new Date().toISOString(),
    });
  };

  return (
    <>
      <MobileHeader showBack title="API Key Management" />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        <section className="rounded-2xl bg-surface shadow-card divide-y divide-border">
          {apiKeys.length === 0 ? (
            <div className="px-4 py-6 text-center text-body1 text-text-muted">
              No API keys yet.
            </div>
          ) : (
            apiKeys.map((k) => (
              <div
                key={k.keyId}
                className="flex items-center justify-between px-4 py-3 text-body1"
              >
                <div className="min-w-0">
                  <div className="font-medium text-text">{k.name}</div>
                  <div className="text-body2 text-text-muted">
                    {k.lastUsedAt
                      ? `Last used ${new Date(k.lastUsedAt).toLocaleDateString()}`
                      : "Never used"}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeApiKey(k.keyId)}
                >
                  Revoke
                </Button>
              </div>
            ))
          )}
        </section>
        <Button
          variant="primary"
          size="md"
          className="w-full gap-1.5"
          onClick={addQuick}
        >
          <Plus className="w-4 h-4" /> Add new key
        </Button>
      </div>
    </>
  );
}
