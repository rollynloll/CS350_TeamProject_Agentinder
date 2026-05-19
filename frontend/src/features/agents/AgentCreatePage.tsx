import { useNavigate } from "react-router-dom";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { Button } from "@/design-system/components/Button";
import {
  DEFAULT_VALUES,
  ProfileForm,
  type ProfileFormValues,
} from "./components/ProfileForm";

const FORM_ID = "agent-profile-create";

export function AgentCreatePage() {
  const navigate = useNavigate();

  const handleSubmit = (values: ProfileFormValues) => {
    // Visual demo only — real POST /agents lands in a follow-up V1 mutation ticket.
    console.info("[AgentCreate] submit", values);
    navigate("/agents");
  };

  return (
    <>
      <MobileHeader
        showBack
        title="Add New Profile"
        action={
          <Button form={FORM_ID} type="submit" variant="pill" size="sm">
            Done
          </Button>
        }
      />
      <div className="flex-1 min-h-0 overflow-y-auto">
        <ProfileForm
          formId={FORM_ID}
          mode="create"
          defaultValues={DEFAULT_VALUES}
          onSubmit={handleSubmit}
        />
      </div>
    </>
  );
}
