"""Discover skill manifests from child directories."""

import json
from pathlib import Path

from .registry import SkillDefinition, SkillRegistry

DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent


def load_skills(root: str | Path = DEFAULT_SKILLS_DIR) -> SkillRegistry:
    registry = SkillRegistry()
    for path in sorted(Path(root).glob("*/skill.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        required = set(SkillDefinition.__dataclass_fields__)
        if not isinstance(payload, dict) or set(payload) != required:
            raise ValueError(f"Invalid skill manifest: {path}")
        strings = ("name", "purpose", "execution_instructions",
                   "output_format", "error_handling")
        if (any(not isinstance(payload[key], str) for key in strings)
                or not isinstance(payload["input_requirements"], dict)
                or not isinstance(payload["permitted_tools"], list)):
            raise ValueError(f"Invalid skill field types: {path}")
        payload["permitted_tools"] = tuple(payload["permitted_tools"])
        registry.register(SkillDefinition(**payload))
    return registry
