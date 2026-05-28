import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateAgent } from "@/api/endpoints/agents";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { Button } from "@/design-system/components/Button";
import {
  DEFAULT_VALUES,
  ProfileForm,
  type ProfileFormValues,
} from "./components/ProfileForm";
import { CredentialModal } from "./components/CredentialModal";

const FORM_ID = "agent-profile-create";

export function AgentCreatePage() {
  const navigate = useNavigate();
  const create = useCreateAgent();
  const [created, setCreated] = useState<{ agentId: string; apiKey: string } | null>(null);

  const handleSubmit = (values: ProfileFormValues) => {
    const windows = values.activeDays.map((day) => ({
      day,
      start: values.activeStart,
      end: values.activeEnd,
    }));
    create.mutate(
      {
        displayName: values.displayName,
        bio: values.description,
        capabilityTags: values.capabilityTags,
        interactionStyle: {},
        availability: { timezone: "UTC", windows },
      },
      {
        // REQ-0105: reveal the generated API credential exactly once.
        onSuccess: (profile) =>
          setCreated({ agentId: profile.agentId, apiKey: profile.apiKeyMasked ?? "" }),
      },
    );
  };

  return (
    <>
      <MobileHeader
        showBack
        title="Add New Profile"
        action={
          <Button form={FORM_ID} type="submit" variant="pill" size="sm" disabled={create.isPending}>
            Done
          </Button>
        }
      />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {create.isError ? (
          <div className="mx-4 mt-3 rounded-xl bg-danger-light px-4 py-2 text-sm text-danger">
            {(create.error as Error).message}
          </div>
        ) : null}
        <ProfileForm
          formId={FORM_ID}
          mode="create"
          defaultValues={DEFAULT_VALUES}
          onSubmit={handleSubmit}
        />
      </div>

      <CredentialModal
        open={created != null}
        apiKey={created?.apiKey ?? ""}
        onDone={() => {
          setCreated(null);
          navigate("/agents");
        }}
      />
    </>
  );
}
