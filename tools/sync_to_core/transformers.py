"""Source-to-source transforms applied to each Python file.

Everything is plain string/regex work — no AST. The transforms are
small, idempotent, and order-independent at the file level, which keeps
the script easy to reason about when something doesn't match.
"""

from __future__ import annotations

import re

from .config import (
    EXCLUDE_INTEGRATION_FILES,
    LICENSE_HEADER_PREFIX,
    PYTHON_REPLACEMENTS,
)

# Match `# CUSTOM-ONLY START` ... `# CUSTOM-ONLY END` (and the trailing
# newline of the END line) anywhere in the file. DOTALL so `.` spans
# newlines; non-greedy so adjacent blocks don't merge.
_CUSTOM_ONLY_BLOCK = re.compile(
    r"^[ \t]*#[ \t]*CUSTOM-ONLY START.*?#[ \t]*CUSTOM-ONLY END[^\n]*\n?",
    flags=re.DOTALL | re.MULTILINE,
)

# After a strip, three or more consecutive blank lines collapse to two.
# Saves us from having to be surgical about which whitespace each
# stripper consumes — we just normalise the result at the end.
_TRIPLE_BLANK = re.compile(r"\n{4,}")

# A `# pragma: no cover` trailing comment — we strip the comment but
# keep the code on that line. Whitespace before the `#` is also eaten
# so we don't leave dangling spaces.
_PRAGMA_NO_COVER = re.compile(r"[ \t]*#[ \t]*pragma:[ \t]*no cover[^\n]*")


# Module names we strip imports for, derived from EXCLUDE_INTEGRATION_FILES
# (e.g. {"migration"} → drop `from .migration import …` blocks). Using the
# exclude list as the source of truth keeps the two in lockstep — adding
# a new HACS-only module to EXCLUDE_INTEGRATION_FILES automatically makes
# the sync script remove its imports too.
_EXCLUDED_MODULES: frozenset[str] = frozenset(
    p[: -len(".py")] for p in EXCLUDE_INTEGRATION_FILES if p.endswith(".py")
)


def _excluded_import_pattern(module: str) -> re.Pattern[str]:
    """Match a `from .{module} import …` block (single- or multi-line).

    Captures any leading explanatory comments and the parenthesised or
    unparenthesised name list, plus a trailing newline. Surrounding
    blank lines are normalised by ``_collapse_blank_lines`` afterwards
    so we don't have to be surgical here.
    """
    return re.compile(
        # Optional contiguous comment lines directly above (description
        # of the import — they make no sense without the import below).
        r"(?:^[ \t]*#[^\n]*\n)*"
        # The import statement itself.
        rf"^[ \t]*from[ \t]+\.{re.escape(module)}[ \t]+import[ \t]+"
        # Either a parenthesised multi-line name list…
        r"(?:\([^)]*\)|[^\n]*)"
        # …or a single-line one. Trailing newline only — the
        # blank-line collapser cleans up the rest.
        r"[ \t]*\n",
        flags=re.MULTILINE,
    )


_EXCLUDED_IMPORT_PATTERNS = tuple(
    _excluded_import_pattern(module) for module in _EXCLUDED_MODULES
)


def strip_custom_only_blocks(source: str) -> str:
    """Remove every `# CUSTOM-ONLY START` … `# CUSTOM-ONLY END` block."""
    return _CUSTOM_ONLY_BLOCK.sub("", source)


def strip_excluded_module_imports(source: str) -> str:
    """Remove ``from .<module> import …`` for every excluded module.

    Excluded modules are the ``.py`` files in
    ``EXCLUDE_INTEGRATION_FILES`` — they don't ship to core, so importing
    from them would leave a dangling import. The matching strip in
    `CUSTOM-ONLY` markers on the call sites is still needed; this helper
    just keeps the import block out of the marker noise.
    """
    for pattern in _EXCLUDED_IMPORT_PATTERNS:
        source = pattern.sub("", source)
    return source


def collapse_blank_lines(source: str) -> str:
    """Collapse runs of 3+ consecutive newlines down to 2.

    PEP 8 allows up to two blank lines between top-level constructs;
    after stripping marker blocks and excluded imports we sometimes end
    up with three in a row. Normalising here lets every other transform
    stay simple instead of trying to be precise about whitespace.
    """
    return _TRIPLE_BLANK.sub("\n\n\n", source)


def strip_license_header(source: str) -> str:
    """Drop a leading copyright/license comment block, if present.

    The header is recognised by a first non-empty line that begins with
    ``LICENSE_HEADER_PREFIX``. From there, every contiguous line that
    starts with ``#`` (or is blank) is part of the header and is removed.
    A single blank line below the header is also consumed so the file
    starts cleanly with its docstring.
    """
    lines = source.splitlines(keepends=True)
    i = 0
    # Skip leading blank lines (rare, but tolerate them).
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines) or not lines[i].lstrip().startswith(LICENSE_HEADER_PREFIX):
        return source
    # Consume the comment block.
    while i < len(lines) and (
        lines[i].lstrip().startswith("#") or lines[i].strip() == ""
    ):
        # Stop at the first non-comment, non-blank line.
        if lines[i].strip() and not lines[i].lstrip().startswith("#"):
            break
        i += 1
    # Re-attach a single trailing blank if we landed on one — but the
    # join below skips up to here, so just drop everything before `i`.
    return "".join(lines[i:])


def strip_pragma_no_cover(source: str) -> str:
    """Drop trailing ``# pragma: no cover`` comments (keep the code)."""
    return _PRAGMA_NO_COVER.sub("", source)


def apply_python_replacements(source: str) -> str:
    """Apply every (old, new) pair from `PYTHON_REPLACEMENTS` in order."""
    for old, new in PYTHON_REPLACEMENTS:
        source = source.replace(old, new)
    return source


def transform_python(
    source: str,
    *,
    strip_license: bool,
    strip_pragma: bool,
) -> str:
    """Run every transform on a single Python source string."""
    # Order matters: drop CUSTOM-ONLY blocks *first* so the auto-import
    # stripper sees a clean import section without dangling markers
    # interleaved with the imports it wants to remove.
    source = strip_custom_only_blocks(source)
    source = strip_excluded_module_imports(source)
    if strip_license:
        source = strip_license_header(source)
    if strip_pragma:
        source = strip_pragma_no_cover(source)
    source = collapse_blank_lines(source)
    return apply_python_replacements(source)


def transform_yaml(source: str, *, strip_license: bool) -> str:
    """Run YAML-safe transforms on a single yaml source string.

    Only the license header and `CUSTOM-ONLY` marker blocks are touched
    here — both rely on `#` line comments, which YAML and Python share.
    The Python import replacements would be wrong inside YAML strings,
    so they are deliberately skipped.
    """
    source = strip_custom_only_blocks(source)
    if strip_license:
        source = strip_license_header(source)
    return collapse_blank_lines(source)
