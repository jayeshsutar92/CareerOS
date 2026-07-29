from __future__ import annotations

from dataclasses import dataclass
from string import Formatter
from typing import Any

from app.ai.exceptions import AIPromptError


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    name: str
    template: str

    @property
    def variables(self) -> set[str]:
        return {
            field_name for _, field_name, _, _ in Formatter().parse(self.template) if field_name
        }

    def render(self, **values: Any) -> str:
        missing = self.variables - values.keys()
        if missing:
            missing_values = ", ".join(sorted(missing))
            raise AIPromptError(f"Missing prompt variables for {self.name}: {missing_values}")
        try:
            return self.template.format(**values)
        except Exception as exc:
            raise AIPromptError(f"Failed to render prompt {self.name}") from exc


class PromptRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> PromptTemplate:
        if template.name in self._templates:
            raise AIPromptError(f"Prompt template already registered: {template.name}")
        self._templates[template.name] = template
        return template

    def get(self, name: str) -> PromptTemplate:
        try:
            return self._templates[name]
        except KeyError as exc:
            raise AIPromptError(f"Prompt template is not registered: {name}") from exc

    def render(self, name: str, **values: Any) -> str:
        return self.get(name).render(**values)

    def names(self) -> list[str]:
        return sorted(self._templates)


prompt_registry = PromptRegistry()
