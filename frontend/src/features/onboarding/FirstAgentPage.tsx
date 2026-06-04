import { useNavigate } from "react-router-dom";
import { markOnboarded } from "@/lib/onboarding";
import { NewAgentForm } from "@/features/agents/components/NewAgentSheet";

/**
 * Final onboarding step: create the first agent. Reuses the same NewAgentForm
 * shown by the Profile tab's "Add profile" so the form is identical everywhere;
 * on close (create succeeded or skipped) we mark onboarding done and enter the app.
 */
export function FirstAgentPage() {
  const navigate = useNavigate();
  const finish = () => {
    markOnboarded();
    navigate("/", { replace: true });
  };

  return (
    <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-4 pb-8">
      <NewAgentForm onClose={finish} />
    </div>
  );
}
