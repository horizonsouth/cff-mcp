# cff-mcp

An MCP server that sets up a project so an AI assistant stops guessing.

Written for someone who has **not** read the book. The framework is taught
through the questions and the validation feedback, never announced up front.

## Run it

```bash
uv sync
uv run cff-mcp          # stdio, for local development
uv run pytest           # 9 tests, all should pass
```

Add to a client's MCP config as a stdio server pointing at `uv run cff-mcp`
with `cwd` set to this repo.

## What it exposes

| Surface | Purpose |
|---|---|
| `guide://interview` (resource) | The seven questions, with good/bad examples. The assistant reads this and runs the interview itself. |
| `generate_context_stack` | Writes the five documents plus a manifest to a directory you specify. |
| `validate_context_stack` | Reads an existing set and reports gaps. Never fails anything. |
| `explain_setup_area` | Explains one area when a user gets stuck. |

## Architecture rule

`cff/core` must never import `mcp` or `cff.server`. Enforced by
`tests/test_import_boundary.py`.

That single rule is what lets the same generation and validation logic power
the free web generator later without a rewrite. `generate()` returns
`{filename: content}` — the server writes it to disk, the web version hands it
to a download.

## Where to edit

Almost everything lives in `cff/core/layers.yaml`: definitions, the questions,
the examples, the thinness heuristics, and which layers feed which document.
One edit there changes the interview, the validator, and the future web form
at the same time.

Expect two or three passes on the wording in that file before the questions
come out right in a cold session — you're tuning model behavior, not code.

## Before you ship

- [ ] Replace the placeholder `framework.url` in `layers.yaml`
- [ ] Test in a fresh session with no explanation; watch whether the assistant
      interviews properly from the resource alone
- [ ] Add remote HTTP + OAuth (local stdio is a dev loop, not a distribution
      channel — a cold user will not clone a repo and hand-edit JSON)
- [ ] Publish to GitHub, then the official registry via `mcp-publisher`
      (registry stores metadata only; it does not host your code)
- [ ] Cross-list on mcp.so, Smithery, Glama
- [ ] Instrument: completed runs, and which layers get flagged most — that data
      is the outline for whatever you write next

## Web generator (`web/`)

Same core, second surface — a static page with FastAPI behind it. Chosen over
Gradio deliberately: the default Gradio look reads as a weekend demo, and this
tool's job is to look like a practitioner built it.

```bash
uvicorn web.app:app --reload      # local
```

For production, see [DEPLOY.md](DEPLOY.md) — a Docker + Caddy setup on a VPS
you rent, which is the whole deployment. The app is stateless, so the container
plus your domain is the entire owned artifact.

The page renders its seven questions from `/api/spec`, which reads
`layers.yaml` — the web form, the MCP interview, and the validator stay in
sync from one file.

Set `ESP_ENDPOINT` and `ESP_KEY` env vars for email capture. Without them the
app runs fine and logs addresses to stdout.

The generator is ungated. The email ask appears only after files exist and
buys the sample chapter, not the tool.
