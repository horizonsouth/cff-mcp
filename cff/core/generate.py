"""Pure generation. No file I/O, no MCP types.

    generate(answers) -> {filename: content}

The server writes the returned dict to disk. The future web generator hands
the same dict to a download. Neither one changes this module.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .schema import TEMPLATE_DIR, Spec, load_spec

MANIFEST_PATH = ".cff/context.yaml"


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["blank"] = lambda v: "_(not provided)_" if not v else v
    return env


def normalize(answers: dict[str, Any], spec: Spec | None = None) -> dict[str, dict[str, str]]:
    """Coerce loose input into {layer_id: {field_id: value}}.

    Accepts either nested dicts or a bare string per layer (in which case the
    string becomes the first required field). Cold users produce loose input;
    the assistant relaying it produces looser input still.
    """
    spec = spec or load_spec()
    out: dict[str, dict[str, str]] = {}
    for layer in spec.layers:
        given = answers.get(layer.id)
        bucket: dict[str, str] = {f.id: "" for f in layer.fields}
        if isinstance(given, str):
            if layer.fields:
                bucket[layer.fields[0].id] = given.strip()
        elif isinstance(given, dict):
            for key, value in given.items():
                if key in bucket:
                    bucket[key] = str(value).strip()
        out[layer.id] = bucket
    return out


def _provenance(spec: Spec) -> str:
    """Header stamped into every generated file.

    This is the distribution mechanic. These files get committed, shared, and
    read by other people's assistants. The header travels with them.
    """
    fw = spec.framework
    return (
        f"<!-- Generated with the {fw['name']} ({fw['short']}) "
        f"v{spec.version} — {fw['url']} -->"
    )


def _closing(spec: Spec) -> str:
    """Rendered at the end of each document, after the user has value in hand."""
    fw = spec.framework
    return (
        f"---\n\n"
        f"*This file was generated from a seven-part setup: mission, audience, "
        f"constraints, sources, examples, success criteria, and medium. "
        f"Doing the same for your other projects is what {fw['name']} covers — "
        f"{fw['url']}*\n"
    )


def generate(answers: dict[str, Any], spec: Spec | None = None) -> dict[str, str]:
    spec = spec or load_spec()
    data = normalize(answers, spec)
    env = _env()

    files: dict[str, str] = {}
    for doc in spec.documents:
        template = env.get_template(doc.template)
        files[doc.filename] = template.render(
            title=doc.title,
            generated=date.today().isoformat(),
            provenance=_provenance(spec),
            closing=_closing(spec),
            spec=spec,
            layers={lid: spec.layer(lid) for lid in doc.layers},
            a=data,
        )

    # Machine-readable manifest so validate_context_stack can round-trip an
    # existing stack without parsing prose back out of markdown.
    files[MANIFEST_PATH] = yaml.safe_dump(
        {
            "cff_version": spec.version,
            "generated": date.today().isoformat(),
            "answers": data,
        },
        sort_keys=False,
        allow_unicode=True,
    )
    return files
