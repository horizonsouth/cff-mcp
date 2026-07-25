"""The reuse guarantee, enforced.

cff.core must never import mcp or cff.server. If this test fails, the web
generator can no longer share the core and you are about to rewrite it.
"""
import pathlib
import re

CORE = pathlib.Path(__file__).parent.parent / "cff" / "core"
FORBIDDEN = re.compile(r"^\s*(from|import)\s+(mcp|cff\.server)\b", re.M)


def test_core_does_not_import_mcp_or_server():
    offenders = [p.name for p in CORE.rglob("*.py") if FORBIDDEN.search(p.read_text())]
    assert not offenders, f"core imports MCP or server code: {offenders}"
