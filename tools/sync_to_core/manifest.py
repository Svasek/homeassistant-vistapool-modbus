"""manifest.json transform: drop HACS-only fields, sort keys."""

from __future__ import annotations

import json
from typing import Any

from .config import MANIFEST_DROP_KEYS

# Hassfest convention (verified against esphome, peblar, mqtt, shelly,
# hue, tplink): `domain` first, then `name`, then every other key in
# alphabetical order. The custom repo follows the same shape so this
# transform is a no-op on key order — only the HACS-only keys (version,
# issue_tracker) are dropped.
_LEADING_KEYS: tuple[str, ...] = ("domain", "name")


def transform_manifest(raw: str) -> str:
    """Return a core-friendly manifest.json string from a HACS one.

    - Drops keys listed in ``MANIFEST_DROP_KEYS`` (HACS-only).
    - Re-emits keys in hassfest order: ``domain`` and ``name`` first,
      then every remaining key alphabetically.
    - 2-space indent + trailing newline (core convention).
    """
    manifest: dict[str, Any] = json.loads(raw)
    cleaned = {k: v for k, v in manifest.items() if k not in MANIFEST_DROP_KEYS}
    ordered: dict[str, Any] = {}
    for k in _LEADING_KEYS:
        if k in cleaned:
            ordered[k] = cleaned[k]
    for k in sorted(cleaned):
        if k not in ordered:
            ordered[k] = cleaned[k]
    return json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"
