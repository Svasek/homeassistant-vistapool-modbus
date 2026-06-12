"""Strip a configurable list of dotted-path keys from a JSON document.

Used for ``strings.json`` and ``translations/en.json`` — the same
vistapool / migration UI strings need to disappear from both, and
they're easier to manage as a flat list of paths than as scattered
markers inside JSON (which has no comment syntax).
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


def strip_json_paths(raw: str, *, paths: tuple[str, ...] = JSON_DROP_KEYS) -> str:
    """Return ``raw`` with every dotted path in ``paths`` removed.

    Round-trips through ``json.loads``/``json.dumps`` so the result is
    deterministically reformatted with two-space indent and a trailing
    newline — matching how the custom and core repos store their JSON.
    """
    data = json.loads(raw)
    for path in paths:
        _drop_path(data, tuple(path.split(".")))
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
