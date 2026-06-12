"""Strip a configurable list of dotted-path keys from a JSON document.

Used for ``strings.json`` and ``translations/en.json`` — the same
vistapool / migration UI strings need to disappear from both, and
they're easier to manage as a flat list of paths than as scattered
markers inside JSON (which has no comment syntax).

Each output style is its own helper because HA core uses two distinct
formatting conventions for these files (verified against esphome,
peblar, mqtt, shelly, hue, tplink):

- ``strings.json`` is human-edited → 2-space indent, raw Unicode,
  trailing newline
- ``translations/en.json`` is a Lokalise build artefact → 4-space
  indent, ASCII-escaped Unicode, no trailing newline
"""

from __future__ import annotations

import json
from typing import Any

from .config import JSON_DROP_KEYS


def _drop_path(obj: Any, path: tuple[str, ...]) -> None:
    """Mutate ``obj`` to remove the value at the dotted ``path``.

    Walks the path, popping the last segment off whichever container it
    lands in. Missing intermediate segments are tolerated — a path that
    no longer applies (e.g. after a previous strip) is a no-op rather
    than an error, so the strip table can stay slightly larger than
    what's actually present.
    """
    if not path:
        return
    *parents, last = path
    cursor = obj
    for segment in parents:
        if not isinstance(cursor, dict) or segment not in cursor:
            return
        cursor = cursor[segment]
    if isinstance(cursor, dict):
        cursor.pop(last, None)


def _strip_paths(raw: str, paths: tuple[str, ...]) -> Any:
    """Parse ``raw``, drop every dotted path in ``paths``, return the dict."""
    data = json.loads(raw)
    for path in paths:
        _drop_path(data, tuple(path.split(".")))
    return data


def strip_strings_json(raw: str, *, paths: tuple[str, ...] = JSON_DROP_KEYS) -> str:
    """Return ``raw`` with ``paths`` stripped, formatted for `strings.json`.

    Convention used by HA core's `strings.json` (verified 2026-06-12
    against esphome, peblar, mqtt, shelly, hue, tplink — all match):

    - 2-space indent
    - alphabetically sorted keys
    - **raw** non-ASCII characters preserved (``ensure_ascii=False``)
    - trailing newline

    `strings.json` is the source of truth that the integration author
    edits by hand, so it stays human-readable: shallow indent, native
    Unicode, line-final newline that POSIX text editors expect.
    """
    return (
        json.dumps(
            _strip_paths(raw, paths),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )


def strip_translations_en_json(
    raw: str, *, paths: tuple[str, ...] = JSON_DROP_KEYS
) -> str:
    """Return ``raw`` with ``paths`` stripped, formatted for `translations/en.json`.

    Convention used by HA core's `translations/en.json` (verified
    2026-06-12 against esphome, peblar, mqtt, shelly, hue, tplink —
    all match):

    - 4-space indent
    - alphabetically sorted keys
    - ASCII-escaped non-ASCII characters (``ensure_ascii=True``, the
      json default) — so ``→`` becomes ``\\u2192`` etc.
    - **no** trailing newline

    `translations/en.json` is a build artefact written by Lokalise
    (and our sync script for the English locale), so it follows the
    machine-friendly defaults Lokalise uses.
    """
    return json.dumps(_strip_paths(raw, paths), indent=4, sort_keys=True)
