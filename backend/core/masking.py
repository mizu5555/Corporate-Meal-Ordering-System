"""Mask a personal display name for vendor-facing responses.

De-identification helper: vendors see a masked employee name plus the employee
number (badge), never the raw name or the internal user id.

Rules:
- Names containing whitespace are treated as Western names: every word except the
  last (the surname) is reduced to its first letter + a single ``*``; the surname
  is kept in full. ``John Smith`` -> ``J* Smith``.
- Names without whitespace and length >= 2 (typically CJK): keep the first and
  last character, single ``*`` between. ``王小明`` -> ``王*明``; ``王明`` -> ``王*``.
- A single character is returned unchanged.
- Empty / None returns an empty string.

A single ``*`` is always used (never length-proportional) so the masked form does
not leak the original length.
"""
from __future__ import annotations


def mask_name(name: str | None) -> str:
    if not name:
        return ""
    name = name.strip()
    if not name:
        return ""

    if " " in name:
        words = name.split()
        surname = words[-1]
        masked_given = [f"{w[0]}*" for w in words[:-1]]
        return " ".join(masked_given + [surname])

    if len(name) == 1:
        return name
    if len(name) == 2:
        return f"{name[0]}*"
    return f"{name[0]}*{name[-1]}"
