from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from ..types import Message

if TYPE_CHECKING:
    from ..agent.agent_personality import AgentPersonality

logger = logging.getLogger(__name__)

_ANCHOR_TEMPLATE = (
    "\n[PERSONALITY REMINDER]\n{summary}\n[END REMINDER]\n"
)

_CHECK_PROMPT_TEMPLATE = (
    "You are a personality auditor. "
    "Given the personality summary and the agent's last response, "
    "answer only PASS or FAIL.\n\n"
    "Personality summary:\n{summary}\n\n"
    "Agent response:\n{response}\n\n"
    "Does the response match the personality? Answer PASS or FAIL only."
)


class PersonalityConsistencyManager:
    """Injects personality anchors and validates response consistency.

    Anchoring: every anchorInterval turns, a system reminder is inserted.
    Checking:  one turn *after* an anchor turn, the response is validated
               via a separate LLM call. Checking on the anchor+1 turn (not
               the anchor turn itself) gives the model time to internalize
               the reminder before we audit it.
    """

    def __init__(
        self,
        anchor_interval: int = 5,
    ) -> None:
        self.anchor_interval: int = anchor_interval
        self._fail_log: List[dict] = []

    # ------------------------------------------------------------------
    # Public interface (called by LLMClient)
    # ------------------------------------------------------------------

    def buildMessages(
        self,
        personality: AgentPersonality,
        history: List[Message],
        turn_count: int,
    ) -> List[Message]:
        """Builds the full message list for the LLM call.

        Inserts a personality anchor system message every anchorInterval turns.
        """
        system_prompt = personality.toPrompt()
        messages: List[Message] = [Message(role="system", content=system_prompt)]

        if self._is_anchor_turn(turn_count):
            anchor_content = _ANCHOR_TEMPLATE.format(summary=personality.toSummary())
            messages.append(Message(role="system", content=anchor_content))

        messages.extend(history)
        return messages

    def check(
        self,
        personality: AgentPersonality,
        response: str,
    ) -> bool:
        """Returns True (PASS) if response is consistent with personality.

        Makes a separate LLM call. The actual call is delegated to the
        LLMClient that owns this manager via a callback set at construction.
        If no checker is available (V1), always returns True.
        """
        if self._checker_fn is None:
            return True

        prompt = _CHECK_PROMPT_TEMPLATE.format(
            summary=personality.toSummary(),
            response=response,
        )
        try:
            verdict = self._checker_fn(prompt).strip().upper()
            return verdict.startswith("PASS")
        except Exception as exc:
            logger.warning("Consistency check failed with exception: %s", exc)
            return True  # fail-open: don't penalise on checker errors

    def is_check_turn(self, turn_count: int) -> bool:
        """True on the turn immediately after an anchor turn."""
        if self.anchor_interval <= 0:
            return False
        return turn_count > 1 and (turn_count - 1) % self.anchor_interval == 0

    def log_fail(self, turn_count: int, response: str) -> None:
        self._fail_log.append({"turn": turn_count, "response": response})
        logger.info(
            "Personality consistency FAIL logged (turn=%d). Total fails: %d",
            turn_count,
            len(self._fail_log),
        )

    def get_fail_log(self) -> List[dict]:
        return list(self._fail_log)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    # Set by LLMClient after construction so manager can call back for check
    _checker_fn: Optional[callable] = None

    def set_checker(self, fn: callable) -> None:
        self._checker_fn = fn

    def _is_anchor_turn(self, turn_count: int) -> bool:
        if self.anchor_interval <= 0:
            return False
        return turn_count % self.anchor_interval == 0
