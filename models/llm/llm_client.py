from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, List, Optional

from ..types import Message
from .personality_consistency_manager import PersonalityConsistencyManager

if TYPE_CHECKING:
    from ..agent.agent import Agent

logger = logging.getLogger(__name__)


class LLMClient:
    """Agent's brain. Wraps GPT-4o and embeds the personality consistency system.

    Each agent owns its own LLMClient instance (not a singleton).
    The client holds a reference to the Agent so it always reads the latest
    personality — no manual sync required when personality is updated.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        agent: Optional[Agent] = None,
        anchor_interval: int = 5,
    ) -> None:
        self.model = model
        self.agent: Optional[Agent] = agent
        self.consistency_manager = PersonalityConsistencyManager(
            anchor_interval=anchor_interval
        )
        # Wire up the checker callback so the manager can trigger a check call
        self.consistency_manager.set_checker(self._check_call)
        self._openai_client = self._build_openai_client()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(self, history: List[Message], turn_count: int) -> str:
        """Generates a personality-consistent response.

        Flow:
          1. Fetch latest personality from agent
          2. Build messages (with optional anchor injection)
          3. Call LLM
          4. On anchor+1 turn: consistency check → regenerate once if FAIL
          5. Log FAIL events (not reflected in trust score)
        """
        if self.agent is None:
            raise RuntimeError("LLMClient has no agent attached")

        personality = self.agent.getPersonality()
        messages = self.consistency_manager.buildMessages(
            personality=personality,
            history=history,
            turn_count=turn_count,
        )

        response = self._call_llm(messages)

        if self.consistency_manager.is_check_turn(turn_count):
            passed = self.consistency_manager.check(personality, response)
            if not passed:
                self.consistency_manager.log_fail(turn_count, response)
                # One retry
                response_retry = self._call_llm(messages)
                passed_retry = self.consistency_manager.check(personality, response_retry)
                if passed_retry:
                    return response_retry
                # Both failed — return original (do not penalise trust score)
                logger.warning(
                    "Both original and retry failed consistency check at turn %d",
                    turn_count,
                )

        return response

    async def embed(self, text: str) -> List[float]:
        """Returns an embedding vector for the given text.

        Used by AgentService to compute capability_embedding.
        Falls back to an empty list when the API key is unavailable (V1 testing).
        """
        try:
            import openai  # type: ignore
            client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
            resp = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return resp.data[0].embedding
        except Exception as exc:
            logger.warning("embed() failed (%s); returning empty vector", exc)
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_llm(self, messages: List[Message]) -> str:
        """Calls the OpenAI Chat Completions API.

        Returns an empty string and logs a warning when the API key is absent
        (useful for unit-testing without live credentials).
        """
        if self._openai_client is None:
            logger.warning(
                "OPENAI_API_KEY not set — LLMClient._call_llm() returning stub response"
            )
            return "[stub response: OPENAI_API_KEY not configured]"

        try:
            import openai  # type: ignore
            oai_messages = [{"role": m.role, "content": m.content} for m in messages]
            completion = self._openai_client.chat.completions.create(
                model=self.model,
                messages=oai_messages,
            )
            return completion.choices[0].message.content or ""
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            raise

    def _check_call(self, prompt: str) -> str:
        """Single-message LLM call used by PersonalityConsistencyManager.check()."""
        messages = [Message(role="user", content=prompt)]
        return self._call_llm(messages)

    def _build_openai_client(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            import openai  # type: ignore
            return openai.OpenAI(api_key=api_key)
        except ImportError:
            logger.warning("openai package not installed; LLMClient will return stubs")
            return None
