"""Execute a skill with its declared input and MCP tool permissions."""

from dataclasses import dataclass
from string import Template
from typing import Any

from src.llm.base import Backend
from src.mcp.client import MCPIncidentAgent
from .registry import SkillRegistry


class SkillExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class SkillResult:
    skill: str
    ok: bool
    output: str | dict[str, Any] | None
    error: str | None
    trace: list[dict[str, Any]]


class SkillRunner:
    def __init__(self, registry: SkillRegistry, server: Any,
                 backend: Backend | None = None,
                 host_allowed: frozenset[str] | None = None):
        self.registry, self.server, self.backend = registry, server, backend
        self.host_allowed = (host_allowed if host_allowed is not None
                             else frozenset({"incident_record", "service_status"}))

    async def run(self, name: str, inputs: dict[str, Any]) -> SkillResult:
        skill = self.registry.get(name)
        if not set(skill.permitted_tools) <= self.host_allowed:
            raise PermissionError(f"Skill requests tools outside host policy: {name}")
        if not isinstance(inputs, dict) or set(inputs) != set(skill.input_requirements):
            raise ValueError("Skill inputs do not match requirements")
        if any(not isinstance(value, str) or not value.strip()
               for value in inputs.values()):
            raise ValueError("Skill inputs must be nonempty strings")
        request = Template(skill.execution_instructions).substitute(inputs)
        agent = MCPIncidentAgent(
            self.server, allowed=frozenset(skill.permitted_tools),
            backend=self.backend)
        try:
            state = await agent.run(request)
        except Exception as exc:
            if skill.error_handling == "raise":
                raise SkillExecutionError(str(exc)) from exc
            return SkillResult(name, False, None, str(exc), [])
        if not state.tool_results or not state.tool_results[-1].ok:
            error = (state.tool_results[-1].error if state.tool_results
                     else state.answer)
            if skill.error_handling == "raise":
                raise SkillExecutionError(error or "Skill failed")
            return SkillResult(name, False, None, error, state.trace)
        output: str | dict[str, Any] = (
            {"answer": state.answer, "tool": state.tool_results[-1].name,
             "data": state.tool_results[-1].content}
            if skill.output_format == "json" else state.answer)
        return SkillResult(name, True, output, None, state.trace)
