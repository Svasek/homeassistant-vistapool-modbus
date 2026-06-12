"""Compact JSON formatter — prettier-like inline-when-it-fits style.

Python's :func:`json.dumps` always expands collections onto separate
lines, which produces verbose output for short single-element lists
and tiny inline dicts. HA core uses prettier (with ``printWidth: 80``)
for its JSON files, so its manifest.json shows ``["@svasek"]`` on one
line and ``{"off": "...", "on": "..."}`` inline when short.

This module reimplements that style in pure Python so the sync script
stays self-contained — no Node.js / npm dependency:

- Try the value as a single-line ``json.dumps`` (separators ``", "`` and
  ``": "``).
- If the line — including its leading indent — fits in
  :data:`PRINT_WIDTH` (default 80), emit it inline.
- Otherwise expand onto multiple lines, recursing into each child so
  shorter sub-trees still collapse where they fit.

Empty containers (``{}``, ``[]``) always emit inline.
"""

from __future__ import annotations

import json
from typing import Any

PRINT_WIDTH = 80


def _format(value: Any, indent_level: int, indent: str) -> str:
    """Return ``value`` as a JSON fragment for the current indent level."""
    compact = json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
    current_indent = indent * indent_level
    if len(current_indent) + len(compact) <= PRINT_WIDTH:
        return compact
    if isinstance(value, dict):
        if not value:
            return "{}"
        child_indent = indent * (indent_level + 1)
        parts = [
            f"{child_indent}{json.dumps(k, ensure_ascii=False)}: "
            f"{_format(v, indent_level + 1, indent)}"
            for k, v in value.items()
        ]
        return "{\n" + ",\n".join(parts) + "\n" + current_indent + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        child_indent = indent * (indent_level + 1)
        parts = [f"{child_indent}{_format(v, indent_level + 1, indent)}" for v in value]
        return "[\n" + ",\n".join(parts) + "\n" + current_indent + "]"
    # Primitive — already encoded above; the compact form is the
    # canonical form. (Reaching this branch means the primitive was
    # too long for an "inline at this depth" check, but that doesn't
    # change how it's serialised.)
    return compact


def format_compact(value: Any, *, indent: str = "  ") -> str:
    """Serialise ``value`` to a compact-when-it-fits JSON string.

    Returns the body without a trailing newline — callers append one
    when the target convention requires it (strings.json does, the
    Lokalise translations style does not).
    """
    return _format(value, 0, indent)
