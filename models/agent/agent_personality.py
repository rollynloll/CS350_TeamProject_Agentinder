from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class AgentPersonality:
    """Three-layer personality structure.

    surface  — bio, style sliders (presentation layer)
    deep     — thinking style, values, conflict handling (anchor layer)
    aspiration — collaboration goals, domains of interest (future layer)

    The deep and aspiration layers act as anchors preventing personality
    drift in long conversations.

    system_prompt_cache is pre-computed at create/update time so it is not
    regenerated on every LLM call.
    """

    # ------------------------------------------------------------------ #
    # Layer fields                                                          #
    # ------------------------------------------------------------------ #
    # surface keys: bio (str), style_sliders (dict[str, float])
    surface: Dict[str, Any] = field(default_factory=dict)
    # deep keys: thinking_style (str), values (list[str]), conflict_handling (str)
    deep: Dict[str, Any] = field(default_factory=dict)
    # aspiration keys: collaboration_goals (list[str]), interest_domains (list[str])
    aspiration: Dict[str, Any] = field(default_factory=dict)

    system_prompt_cache: Optional[str] = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------ #

    def toPrompt(self) -> str:
        """Returns the cached system prompt, building it if cache is empty."""
        if self.system_prompt_cache is None:
            self.system_prompt_cache = self._build_system_prompt()
        return self.system_prompt_cache

    def toSummary(self) -> str:
        """Compact text summary used by PersonalityConsistencyManager.check()."""
        parts: list[str] = []

        bio = self.surface.get("bio", "")
        if bio:
            parts.append(f"Bio: {bio}")

        sliders = self.surface.get("style_sliders", {})
        if sliders:
            slider_str = ", ".join(f"{k}={v:.1f}" for k, v in sliders.items())
            parts.append(f"Style: {slider_str}")

        thinking = self.deep.get("thinking_style", "")
        if thinking:
            parts.append(f"Thinking: {thinking}")

        values = self.deep.get("values", [])
        if values:
            parts.append(f"Values: {', '.join(values)}")

        conflict = self.deep.get("conflict_handling", "")
        if conflict:
            parts.append(f"Conflict: {conflict}")

        goals = self.aspiration.get("collaboration_goals", [])
        if goals:
            parts.append(f"Goals: {', '.join(goals)}")

        domains = self.aspiration.get("interest_domains", [])
        if domains:
            parts.append(f"Domains: {', '.join(domains)}")

        return " | ".join(parts)

    def update(self, fields: dict) -> None:
        allowed = {"surface", "deep", "aspiration"}
        changed = False
        for key, value in fields.items():
            if key in allowed:
                setattr(self, key, value)
                changed = True
        if changed:
            self.system_prompt_cache = self._build_system_prompt()
            self.updated_at = datetime.now(timezone.utc)

    def _build_system_prompt(self) -> str:
        bio = self.surface.get("bio", "")
        sliders = self.surface.get("style_sliders", {})
        thinking = self.deep.get("thinking_style", "")
        values = self.deep.get("values", [])
        conflict = self.deep.get("conflict_handling", "")
        goals = self.aspiration.get("collaboration_goals", [])
        domains = self.aspiration.get("interest_domains", [])

        lines = ["You are an AI agent with the following personality. Stay in character throughout the entire conversation.\n"]

        if bio:
            lines.append(f"## About you\n{bio}\n")

        if sliders:
            style_desc = "\n".join(f"- {k}: {v:.1f}/1.0" for k, v in sliders.items())
            lines.append(f"## Communication style\n{style_desc}\n")

        if thinking or values or conflict:
            lines.append("## Core character")
            if thinking:
                lines.append(f"- Thinking style: {thinking}")
            if values:
                lines.append(f"- Core values: {', '.join(values)}")
            if conflict:
                lines.append(f"- Conflict handling: {conflict}")
            lines.append("")

        if goals or domains:
            lines.append("## Aspirations")
            if goals:
                lines.append(f"- Collaboration goals: {', '.join(goals)}")
            if domains:
                lines.append(f"- Interest domains: {', '.join(domains)}")
            lines.append("")

        lines.append(
            "Maintain this personality consistently. "
            "Do not break character or acknowledge that you are an AI unless directly asked."
        )
        return "\n".join(lines)
