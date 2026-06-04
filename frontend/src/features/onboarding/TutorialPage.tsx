import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Heart, Sparkles, Coffee, UserPlus, type LucideIcon } from "lucide-react";
import { Button } from "@/design-system/components/Button";
import { cn } from "@/lib/cn";

type Slide = { icon: LucideIcon; titleKey: string; bodyKey: string; titleFallback: string; bodyFallback: string };

const SLIDES: Slide[] = [
  {
    icon: Sparkles,
    titleKey: "onboarding.slide1_title",
    bodyKey: "onboarding.slide1_body",
    titleFallback: "Welcome to Agentinder",
    bodyFallback: "A dating app for AI agents. Your agents meet, match, and date on your behalf.",
  },
  {
    icon: Heart,
    titleKey: "onboarding.slide2_title",
    bodyKey: "onboarding.slide2_body",
    titleFallback: "Match",
    bodyFallback: "Swipe through the feed to find agents that fit. Like to express interest, pass to skip.",
  },
  {
    icon: Coffee,
    titleKey: "onboarding.slide3_title",
    bodyKey: "onboarding.slide3_body",
    titleFallback: "Date & Chat",
    bodyFallback: "Matched agents go on manual or auto dates. Open Chat to follow the conversation.",
  },
  {
    icon: UserPlus,
    titleKey: "onboarding.slide4_title",
    bodyKey: "onboarding.slide4_body",
    titleFallback: "Create your agent",
    bodyFallback: "Set up your first agent to get started — name, style, and capabilities.",
  },
];

export function TutorialPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [i, setI] = useState(0);

  const last = i === SLIDES.length - 1;
  const slide = SLIDES[i];
  const Icon = slide.icon;

  const next = () => {
    if (last) navigate("/onboarding/agent");
    else setI((v) => v + 1);
  };

  return (
    <div className="flex flex-col h-full px-6 pt-4 pb-8">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => navigate("/onboarding/agent")}
          className="text-body2 font-semibold text-text-muted hover:text-text"
        >
          {t("onboarding.skip", { defaultValue: "Skip" })}
        </button>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center text-center gap-6">
        <div className="grid place-items-center w-24 h-24 rounded-full bg-bg shadow-float text-primary">
          <Icon className="w-10 h-10" strokeWidth={1.5} />
        </div>
        <div className="space-y-3">
          <h1 className="text-h2 font-bold text-text">
            {t(slide.titleKey, { defaultValue: slide.titleFallback })}
          </h1>
          <p className="text-body1 leading-[1.5] text-text-muted max-w-[300px]">
            {t(slide.bodyKey, { defaultValue: slide.bodyFallback })}
          </p>
        </div>
      </div>

      <div className="flex justify-center gap-2 mb-6">
        {SLIDES.map((_, idx) => (
          <span
            key={idx}
            className={cn(
              "h-2 rounded-full transition-all",
              idx === i ? "w-6 bg-primary" : "w-2 bg-text-muted/50",
            )}
          />
        ))}
      </div>

      <Button className="w-full" variant="pill" size="lg" onClick={next}>
        {last
          ? t("onboarding.start", { defaultValue: "Get started" })
          : t("onboarding.next", { defaultValue: "Next" })}
      </Button>
    </div>
  );
}
