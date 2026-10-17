"""Host-side tool authorization, independent of model instructions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyContext:
    environment: str = "dev"
    scopes: frozenset[str] = frozenset()
    approved_tools: frozenset[str] = frozenset()
    allow_mutations: bool = False


def authorize(tool: object, context: PolicyContext) -> None:
    if context.environment not in tool.environments:
        raise PermissionError(f"Tool unavailable in {context.environment}: {tool.name}")
    if not tool.required_scopes <= context.scopes:
        raise PermissionError(f"Missing scopes for {tool.name}")
    if tool.side_effects:
        if tool.verifier is None:
            raise PermissionError(f"Post-action verifier required for {tool.name}")
        if not context.allow_mutations:
            raise PermissionError(f"Mutating tool disabled: {tool.name}")
        if tool.risk == "high" or (context.environment == "prod"
                                   and tool.production_requires_approval):
            if tool.name not in context.approved_tools:
                raise PermissionError(f"Approval required for {tool.name}")
