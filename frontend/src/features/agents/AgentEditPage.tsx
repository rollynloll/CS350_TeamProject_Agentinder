import { useNavigate, useParams } from "react-router-dom";
import { useAgentProfile } from "@/api/endpoints/agents";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { Button } from "@/design-system/components/Button";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import {
  ProfileForm,
  type ProfileFormValues,
} from "./components/ProfileForm";

const FORM_ID = "agent-profile-edit";

export function AgentEditPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const query = useAgentProfile(agentId);

  const handleSubmit = (values: ProfileFormValues) => {
    // Visual demo only — real PUT /agents/{id} lands in a follow-up V1 ticket.
    console.info("[AgentEdit] submit", values);
    navigate(`/agents/${agentId}`);
  };

  return (
    <QueryBoundary query={query}>
      {(profile) => {
        const defaults: ProfileFormValues = {
          baseModel: profile.baseModel ?? "",
          apiKey: profile.apiKeyMasked ?? "",
          avatarUrl: profile.avatarUrl,
          displayName: profile.displayName,
          description: profile.bio,
          capabilityTags: profile.capabilityTags,
          styleCasual: profile.styleCasual ?? 50,
          styleDetail: profile.styleDetail ?? 50,
        };

        return (
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
                defaultValues={defaults}
                onSubmit={handleSubmit}
              />
            </div>
          </>
        );
      }}
    </QueryBoundary>
  );
}
