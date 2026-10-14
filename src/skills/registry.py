"""Validated, reusable skill definitions."""

from dataclasses import dataclass
import re
from string import Template


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    purpose: str
    input_requirements: dict[str, str]
    permitted_tools: tuple[str, ...]
    execution_instructions: str
    output_format: str
    error_handling: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.name):
            raise ValueError("Invalid skill name")
        if not self.purpose.strip() or not self.execution_instructions.strip():
            raise ValueError("Skill purpose and instructions are required")
        if not self.input_requirements or any(
                not re.fullmatch(r"[a-z][a-z0-9_]*", key) or value != "string"
                for key, value in self.input_requirements.items()):
            raise ValueError("Skill inputs must be named strings")
        if (not self.permitted_tools
                or len(set(self.permitted_tools)) != len(self.permitted_tools)
                or any(not isinstance(name, str) or not re.fullmatch(
                    r"[a-z][a-z0-9_]*", name) for name in self.permitted_tools)):
            raise ValueError("Skill must declare unique permitted tools")
        if self.output_format not in {"json", "text"}:
            raise ValueError("Unsupported output format")
        if self.error_handling not in {"return_error", "raise"}:
            raise ValueError("Unsupported error handling")
        placeholders = set(Template(self.execution_instructions).get_identifiers())
        if not placeholders <= self.input_requirements.keys():
            raise ValueError("Instruction placeholder is not a declared input")
        Template(self.execution_instructions).substitute(
            {key: "sample" for key in self.input_requirements})


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        if skill.name in self._skills:
            raise ValueError(f"Duplicate skill: {skill.name}")
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition:
        return self._skills[name]

    def list_skills(self) -> list[str]:
        return sorted(self._skills)
