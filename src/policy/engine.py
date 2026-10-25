"""Host-side authorization for an exact tool invocation."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any


POLICY_VERSION = "governance-v1"


def arguments_digest(arguments: dict[str, Any]) -> str:
    """Canonical binding; raw arguments must never appear in audit events."""
    payload = json.dumps(arguments, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return sha256(payload).hexdigest()


@dataclass(frozen=True)
class Approval:
    reference: str
    actor_id: str
    operation: str
    resource: str
    arguments_digest: str
    expires_at: datetime

    def matches(self, actor_id: str, operation: str, resource: str,
                arguments: dict[str, Any], now: datetime) -> bool:
        return bool(self.reference and self.expires_at.tzinfo is not None
                    and self.actor_id == actor_id and self.operation == operation
                    and self.resource == resource
                    and self.arguments_digest == arguments_digest(arguments)
                    and now < self.expires_at)


@dataclass(frozen=True)
class PolicyContext:
    environment: str = "dev"
    actor_id: str = "anonymous"
    scopes: frozenset[str] = frozenset()
    approvals: tuple[Approval, ...] = ()
    # Retained only to fail closed for callers of the old teaching API.
    approved_tools: frozenset[str] = frozenset()
    allow_mutations: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    policy_version: str = POLICY_VERSION
    approval_reference: str | None = None


def decide(tool: object, context: PolicyContext, arguments: dict[str, Any],
           now: datetime | None = None) -> PolicyDecision:
    if context.environment not in tool.environments:
        return PolicyDecision(False, "environment_denied")
    if not tool.required_scopes <= context.scopes:
        return PolicyDecision(False, "missing_scopes")
    if not tool.side_effects:
        return PolicyDecision(True, "read_allowed")
    if tool.verifier is None:
        return PolicyDecision(False, "verifier_required")
    if not context.allow_mutations:
        return PolicyDecision(False, "mutations_disabled")
    if not context.actor_id or context.actor_id == "anonymous":
        return PolicyDecision(False, "actor_required")
    if tool.risk == "high" or (context.environment == "prod"
                               and tool.production_requires_approval):
        resource_arg = tool.resource_argument
        if not resource_arg or not isinstance(arguments.get(resource_arg), str):
            return PolicyDecision(False, "resource_binding_required")
        instant = now or datetime.now(timezone.utc)
        for approval in context.approvals:
            if approval.matches(context.actor_id, tool.name, arguments[resource_arg],
                                arguments, instant):
                return PolicyDecision(True, "scoped_approval", approval_reference=approval.reference)
        return PolicyDecision(False, "scoped_approval_required")
    return PolicyDecision(True, "mutation_allowed")


def authorize(tool: object, context: PolicyContext,
              arguments: dict[str, Any] | None = None) -> PolicyDecision:
    decision = decide(tool, context, arguments or {})
    if not decision.allowed:
        raise PermissionError(f"Policy denied {tool.name}: {decision.reason}")
    return decision
