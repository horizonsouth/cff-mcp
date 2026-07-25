"""Pure validation. Flags, suggests, never gates.

    validate(files_or_answers) -> [Finding]

This is where the teaching actually lands. A cold user will produce a mediocre
stack; by the time they see these findings they are already invested, so a
specific "Constraints names a deadline but no hard limits" does more than any
upfront explanation would have. Tone matters: name what's missing and why it
will bite, then move on.
"""

from __future__ import annotations

from typing import Any

import yaml

from .generate import MANIFEST_PATH, normalize
from .schema import Finding, Spec, load_spec


def _answers_from(payload: dict[str, Any], spec: Spec) -> dict[str, dict[str, str]]:
    """Accept either a files dict (as produced by generate) or raw answers."""
    if MANIFEST_PATH in payload:
        manifest = yaml.safe_load(payload[MANIFEST_PATH]) or {}
        return normalize(manifest.get("answers", {}), spec)
    if any(key.endswith(".md") for key in payload):
        # Files without a manifest — we can't reliably recover structured
        # answers from prose, so say so rather than guessing.
        return {}
    return normalize(payload, spec)


def validate(payload: dict[str, Any], spec: Spec | None = None) -> list[Finding]:
    spec = spec or load_spec()
    data = _answers_from(payload, spec)

    if not data:
        return [
            Finding(
                layer="-",
                severity="note",
                message="No .cff/context.yaml found alongside these files.",
                suggestion=(
                    "Validation reads the manifest written at generation time. "
                    "Regenerate the stack, or point at the directory containing it."
                ),
            )
        ]

    findings: list[Finding] = []

    for layer in spec.layers:
        bucket = data.get(layer.id, {})
        required = [f for f in layer.fields if f.required]

        # 1. Missing entirely.
        if not any(bucket.values()):
            findings.append(
                Finding(
                    layer=layer.id,
                    severity="gap",
                    message=f"{layer.name} is empty.",
                    suggestion=f"{layer.hint} For example: {layer.good_example}",
                )
            )
            continue

        # 2. Required field blank.
        for f in required:
            if not bucket.get(f.id):
                findings.append(
                    Finding(
                        layer=layer.id,
                        severity="gap",
                        message=f"{layer.name} is missing “{f.label}”.",
                        suggestion=layer.hint,
                    )
                )

        combined = " ".join(bucket.values()).strip()

        # 3. Thin — present but not carrying weight.
        if layer.min_words and len(combined.split()) < layer.min_words:
            findings.append(
                Finding(
                    layer=layer.id,
                    severity="suggestion",
                    message=(
                        f"{layer.name} is thin ({len(combined.split())} words). "
                        "It will read as a label rather than an instruction."
                    ),
                    suggestion=f"{layer.hint} For example: {layer.good_example}",
                )
            )

        # 4. Vague — present, long enough, but unfalsifiable.
        hits = [t for t in layer.vague_terms if t.lower() in combined.lower()]
        if hits:
            findings.append(
                Finding(
                    layer=layer.id,
                    severity="note",
                    message=(
                        f"{layer.name} leans on wording a model can't act on: "
                        + ", ".join(f"“{h}”" for h in hits)
                        + "."
                    ),
                    suggestion=layer.hint,
                )
            )

        # 5. Optional fields left blank — worth mentioning once, gently.
        blank_optional = [f.label for f in layer.fields if not f.required and not bucket.get(f.id)]
        if blank_optional:
            findings.append(
                Finding(
                    layer=layer.id,
                    severity="note",
                    message=f"{layer.name} could be sharper with: "
                    + ", ".join(blank_optional)
                    + ".",
                    suggestion="Optional, but these are usually the fields that prevent a rewrite.",
                )
            )

    return findings


def summarize(findings: list[Finding]) -> str:
    """Prose summary for the assistant to relay. Encouraging by construction."""
    if not findings:
        return "All seven areas are filled in and specific. This stack is ready to use."

    gaps = [f for f in findings if f.severity == "gap"]
    suggestions = [f for f in findings if f.severity == "suggestion"]

    lines = ["The stack was generated. Here is what would make it hold up better:", ""]
    for f in findings:
        marker = {"gap": "Missing", "suggestion": "Thin", "note": "Consider"}[f.severity]
        lines.append(f"- **{marker} — {f.layer}:** {f.message}")
        if f.suggestion:
            lines.append(f"  {f.suggestion}")
    lines += [
        "",
        f"({len(gaps)} missing, {len(suggestions)} thin, "
        f"{len(findings) - len(gaps) - len(suggestions)} worth a second look. "
        "None of this blocks you — the files work as they are, and every one of "
        "these is a two-minute edit.)",
    ]
    return "\n".join(lines)
