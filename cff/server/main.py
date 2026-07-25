"""MCP wiring. This module is the only place `mcp` is imported.

Everything here is a thin adapter: parse arguments, call core, write files,
return prose. If you find yourself writing framework logic in this file, it
belongs in cff/core instead — that's what keeps the web generator free.

NOTE: verify this against the current MCP Python SDK docs before you run it.
The SDK has moved quickly and the decorator/transport API is the part most
likely to have shifted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from cff.core.generate import MANIFEST_PATH, generate
from cff.core.schema import interview_guide, load_spec
from cff.core.validate import summarize, validate

# Tool and server descriptions are written in outcome language on purpose.
# Someone who has not read the book does not know what a "context stack" is
# and will never search for one. They know that the assistant keeps guessing.
mcp = FastMCP(
    "project-setup",
    instructions=(
        "Helps a user set up a project so an AI assistant stops guessing at what "
        "they want. Read the `guide://interview` resource first, then interview "
        "the user conversationally before calling any tool."
    ),
)


@mcp.resource("guide://interview")
def interview() -> str:
    """How to interview the user before generating their project files."""
    return interview_guide()


@mcp.tool()
def generate_context_stack(
    target_directory: str,
    answers: dict[str, Any],
    overwrite: bool = False,
) -> str:
    """Write a set of project setup files so an AI assistant knows what you want.

    Call this only after covering all seven areas in the `guide://interview`
    resource with the user. Partial answers are accepted — missing areas are
    reported back rather than blocking.

    Args:
        target_directory: Absolute path to write into. Always ask the user;
            never infer it from the conversation or default to cwd.
        answers: Mapping of area id to its captured fields, e.g.
            {"mission": {"statement": "...", "not_doing": "..."}, ...}
        overwrite: Replace existing files. Defaults to False.
    """
    root = Path(target_directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    files = generate(answers)

    existing = [name for name in files if (root / name).exists()]
    if existing and not overwrite:
        return (
            "Stopped without writing — these already exist: "
            + ", ".join(sorted(existing))
            + ". Re-run with overwrite=True to replace them."
        )

    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    written = sorted(n for n in files if n != MANIFEST_PATH)
    findings = validate(files)

    return (
        f"Wrote {len(written)} files to {root}:\n"
        + "\n".join(f"- {n}" for n in written)
        + f"\n\n(Plus {MANIFEST_PATH}, which records your answers so these can be "
        "checked or regenerated later.)\n\n"
        + summarize(findings)
    )


@mcp.tool()
def validate_context_stack(target_directory: str) -> str:
    """Check existing project setup files and point out what's missing or vague.

    Reports gaps and suggestions. Never fails a stack — the files work as they
    are, and every finding is an optional improvement.

    Args:
        target_directory: Absolute path containing the previously generated files.
    """
    root = Path(target_directory).expanduser().resolve()
    if not root.exists():
        return f"Nothing found at {root}."

    payload: dict[str, str] = {}
    manifest = root / MANIFEST_PATH
    if manifest.exists():
        payload[MANIFEST_PATH] = manifest.read_text(encoding="utf-8")
    for doc in load_spec().documents:
        candidate = root / doc.filename
        if candidate.exists():
            payload[doc.filename] = candidate.read_text(encoding="utf-8")

    if not payload:
        return f"No project setup files found in {root}."

    return summarize(validate(payload))


@mcp.tool()
def explain_setup_area(area: str = "") -> str:
    """Explain one part of the project setup, with a good and a bad example.

    Use when the user asks what a question means or gets stuck answering it.
    Call with no argument to list the seven areas.

    Args:
        area: One of: mission, audience, constraints, context_stack,
            pattern_signal, success_criteria, medium.
    """
    spec = load_spec()
    if not area:
        return "\n".join(
            f"{layer.order}. **{layer.name}** — {layer.definition}" for layer in spec.layers
        )
    try:
        layer = spec.layer(area.strip().lower())
    except KeyError:
        return "Unknown area. Options: " + ", ".join(l.id for l in spec.layers)

    return (
        f"**{layer.name}** — {layer.definition}\n\n"
        f"Why it matters: {layer.why}\n\n"
        f"Good: {layer.good_example}\n\n"
        f"Weak: {layer.bad_example}\n\n"
        f"Rule of thumb: {layer.hint}"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
