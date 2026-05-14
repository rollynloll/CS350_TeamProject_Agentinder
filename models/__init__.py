"""Agentinder domain models — Backend B."""

from .agent import Agent, AgentPersonality, AgentProfile, AgentService
from .enums import IssueEnum, PlanEnum, SwipeEnum, TierEnum, VisibilityEnum
from .llm import LLMClient, PersonalityConsistencyManager
from .principal import Principal, PrincipalProfile
from .rating import Rating
from .score import (
    CompatibilityScore,
    ScoreBreakdown,
    ScoreManager,
    TrustBreakdown,
    TrustDataPoint,
)
from .types import Match, Message

__all__ = [
    # Enums
    "SwipeEnum",
    "TierEnum",
    "VisibilityEnum",
    "PlanEnum",
    "IssueEnum",
    # Shared types
    "Message",
    "Match",
    # Principal
    "Principal",
    "PrincipalProfile",
    # Agent
    "Agent",
    "AgentProfile",
    "AgentPersonality",
    "AgentService",
    # LLM
    "LLMClient",
    "PersonalityConsistencyManager",
    # Score
    "ScoreManager",
    "CompatibilityScore",
    "ScoreBreakdown",
    "TrustBreakdown",
    "TrustDataPoint",
    # Rating
    "Rating",
]
