import { useSettings } from "@/api/endpoints/settings";
import { Button } from "@/design-system/components/Button";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { useAuth } from "@/store/auth";

export function AccountPage() {
  const query = useSettings();
  const { logout } = useAuth();

  return (
    <>
      <MobileHeader showBack title="Account" />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        <QueryBoundary query={query}>
          {(s) => (
            <>
              <section className="rounded-2xl bg-surface shadow-card divide-y divide-border">
                <Row label="Display name" value={s.account.displayName} />
                <Row label="Email" value={s.account.email} />
                <Row
                  label="Joined"
                  value={new Date(s.account.createdAt).toLocaleDateString()}
                />
              </section>
              <Button
                variant="secondary"
                size="md"
                className="w-full"
                onClick={() => logout()}
              >
                Log out
              </Button>
              <Button variant="danger" size="md" className="w-full">
                Delete account
              </Button>
            </>
          )}
        </QueryBoundary>
      </div>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 text-body1">
      <span className="text-text-muted">{label}</span>
      <span className="font-medium text-text truncate ml-3">{value}</span>
    </div>
  );
}
