"""Types and spec loading for the Context First core.

Nothing in cff.core may import from cff.server or from `mcp`.
This is enforced by tests/test_import_boundary.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SPEC_PATH = Path(__file__).parent / "layers.yaml"
TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class FieldSpec:
    id: str
    label: str
    required: bool = False
    sample: str = ""


@dataclass(frozen=True)
class LayerSpec:
    id: str
    name: str
    order: int
    definition: str
    why: str
    prompt: str
    good_example: str
    bad_example: str
    fields: tuple[FieldSpec, ...] = ()
    min_words: int = 0
    vague_terms: tuple[str, ...] = ()
    hint: str = ""


@dataclass(frozen=True)
class DocumentSpec:
    filename: str
    title: str
    template: str
    layers: tuple[str, ...]


@dataclass(frozen=True)
class Spec:
    version: str
    framework: dict[str, Any]
    layers: tuple[LayerSpec, ...]
    documents: tuple[DocumentSpec, ...]

    def layer(self, layer_id: str) -> LayerSpec:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        raise KeyError(f"unknown layer: {layer_id}")


# Severity is deliberately three levels and none of them are "error".
# The validator advises. It never blocks generation. A first-time user who
# gets told they failed concludes the framework is fussy, not that they rushed.
Severity = str  # "note" | "suggestion" | "gap"


@dataclass
class Finding:
    layer: str
    severity: Severity
    message: str
    suggestion: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "layer": self.layer,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@lru_cache(maxsize=1)
def load_spec(path: Path | None = None) -> Spec:
    raw = yaml.safe_load((path or SPEC_PATH).read_text(encoding="utf-8"))

    layers = tuple(
        LayerSpec(
            id=item["id"],
            name=item["name"],
            order=item["order"],
            definition=item["definition"].strip(),
            why=item["why"].strip(),
            prompt=item["prompt"].strip(),
            good_example=item["good_example"].strip(),
            bad_example=item["bad_example"].strip(),
            fields=tuple(
                FieldSpec(
                    f["id"],
                    f["label"],
                    bool(f.get("required", False)),
                    f.get("sample", "").strip(),
                )
                for f in item.get("fields", [])
            ),
            min_words=int(item.get("thinness", {}).get("min_words", 0)),
            vague_terms=tuple(item.get("thinness", {}).get("vague_terms", [])),
            hint=item.get("thinness", {}).get("hint", "").strip(),
        )
        for item in sorted(raw["layers"], key=lambda i: i["order"])
    )

    documents = tuple(
        DocumentSpec(
            filename=d["filename"],
            title=d["title"],
            template=d["template"],
            layers=tuple(d["layers"]),
        )
        for d in raw["documents"]
    )

    return Spec(
        version=raw["version"],
        framework=raw["framework"],
        layers=layers,
        documents=documents,
    )


def interview_guide() -> str:
    """Human-readable rendering of the spec, served as the MCP resource.

    The assistant reads this and conducts the interview itself. Keeping the
    guidance here rather than in the tool descriptions means one edit to
    layers.yaml changes how every client asks the questions.
    """
    spec = load_spec()
    out: list[str] = [
        "# Setting up a project so an AI assistant stops guessing",
        "",
        "Work through the seven areas below with the user, one at a time, in a",
        "natural conversation. Do not lecture and do not name the framework",
        "unless asked. Ask, listen, and move on. If an answer is thin, offer the",
        "good example as a nudge, accept whatever they give, and continue.",
        "",
        "When all seven are covered, call `generate_context_stack`.",
        "",
    ]
    for layer in spec.layers:
        out += [
            f"## {layer.order}. {layer.name}",
            "",
            layer.definition,
            "",
            f"*Why it matters:* {layer.why}",
            "",
            f"**Ask:** {layer.prompt}",
            "",
            f"**Good answer:** {layer.good_example}",
            "",
            f"**Weak answer:** {layer.bad_example}",
            "",
            f"**If the answer is weak:** {layer.hint}",
            "",
            "**Capture:**",
        ]
        for f in layer.fields:
            flag = "required" if f.required else "optional"
            out.append(f"- `{f.id}` — {f.label} ({flag})")
        out.append("")
    return "\n".join(out)
