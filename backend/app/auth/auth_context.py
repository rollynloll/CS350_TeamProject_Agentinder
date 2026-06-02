from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID


@dataclass
class AuthContext:
    role: Literal["principal", "agent", "admin"]
    session_id: UUID
    principal_id: UUID | None = None
    agent_id: UUID | None = None
    email: str | None = None
    scopes: list[str] = field(default_factory=list)

    def is_principal(self) -> bool:
        return self.role == "principal"

    def is_agent(self) -> bool:
        return self.role == "agent"

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes
