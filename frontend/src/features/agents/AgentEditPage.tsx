import { useNavigate, useParams } from "react-router-dom";
import { useAgentProfile } from "@/api/endpoints/agents";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { Button } from "@/design-system/components/Button";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import {
  DEFAULT_VALUES,
  ProfileForm,
  type ProfileFormValues,
} from "./components/ProfileForm";
import type { AgentProfile, AvailabilityWindow } from "@/api/types";

const FORM_ID = "agent-profile-edit";

function profileToDefaults(profile: AgentProfile): ProfileFormValues {
  const windows = profile.availability.windows;
  const uniqueDays = Array.from(
    new Set(windows.map((w) => w.day)),
  ) as Array<AvailabilityWindow["day"]>;
  const first = windows[0];

  return {
    baseModel: profile.baseModel ?? "",
    apiKey: profile.apiKeyMasked ?? "",
    avatarUrl: profile.avatarUrl,
    displayName: profile.displayName,
    description: profile.bio,
    capabilityTags: profile.capabilityTags,
    styleCasual: profile.styleCasual ?? DEFAULT_VALUES.styleCasual,
    styleDetail: profile.styleDetail ?? DEFAULT_VALUES.styleDetail,
    styleBold: profile.styleBold ?? DEFAULT_VALUES.styleBold,
    activeDays: uniqueDays,
    activeStart: first?.start ?? DEFAULT_VALUES.activeStart,
    activeEnd: first?.end ?? DEFAULT_VALUES.activeEnd,
  };
}

export function AgentEditPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const query = useAgentProfile(agentId);

  const handleSubmit = (values: ProfileFormValues) => {
    const windows = values.activeDays.map((day) => ({
      day,
      start: values.activeStart,
      end: values.activeEnd,
    }));
    // Visual demo only — real PUT /agents/{id} lands in a follow-up V1 ticket.
    console.info("[AgentEdit] submit", {
      ...values,
      availabilityWindows: windows,
    });
    navigate(`/agents/${agentId}`);
  };

  return (
    <QueryBoundary query={query}>
      {(profile) => (
        <>
          <MobileHeader
            showBack
            title="Edit Profile"
            action={
              <Button form={FORM_ID} type="submit" variant="pill" size="sm">
                Done
              </Button>
            }
          />
          <div className="flex-1 min-h-0 overflow-y-auto">
            <ProfileForm
              formId={FORM_ID}
              mode="edit"
              defaultValues={profileToDefaults(profile)}
              onSubmit={handleSubmit}
            />
          </div>
        </>
      )}
    </QueryBoundary>
  );
}
