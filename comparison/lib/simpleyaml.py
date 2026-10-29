"""Minimal YAML-subset loader (stdlib only).

Supports the subset used by this repo's config/manifest files:
  * nested dicts by indentation
  * block sequences: items start with '- ' at the same indent; an item may be a
    scalar or (when '- ' is alone) a nested dict at deeper indentation
  * scalars: int / float / bool / null / quoted / plain strings (plain strings
    may not contain ': ' or ' #')
  * '#' full-line and trailing comments

No anchors, aliases, flow maps `{a: b}`, multi-line `|` blocks, or sequences of
sequences. Avoid those in these files.
"""
from __future__ import annotations

_LEAD = "-"


def _parse_scalar(raw: str):
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        return raw[1:-1]
    low = raw.lower()
    if low in ("null", "~", "none"):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    if raw.startswith("[") and raw.endswith("]"):   # inline list
        body = raw[1:-1].strip()
        return [] if not body else [_parse_scalar(x) for x in body.split(",")]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _strip_comment(line: str) -> str:
    in_sq = in_dq = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_dq:
            in_sq = not in_sq
        elif ch == '"' and not in_sq:
            in_dq = not in_dq
        elif ch == "#" and not in_sq and not in_dq:
            return line[:i]
    return line


def _prepare(text: str):
    """Return [(indent, content)] for meaningful lines."""
    out = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        out.append((indent, line.strip()))
    return out


def load_yaml(text: str):
    lines = _prepare(text)
    if not lines:
        return {}
    root, _ = _block(lines, 0, lines[0][0])
    return root


def _scalar_or_map(raw: str):
    """'- rest' items: a bare scalar, or nothing meaning nested block."""
    rest = raw[len(_LEAD):].strip()
    if rest == "":
        return None  # sentinel: nested content follows
    return rest


def _block(lines, idx, indent):
    """Parse consecutive key: ... entries at exactly `indent`.

    Returns (dict, next_idx).
    """
    d = {}
    while idx < len(lines):
        ind, text = lines[idx]
        if ind != indent or text.startswith(_LEAD):
            break
        key, sep, rest = text.partition(":")
        key = key.strip()
        if not sep:
            # plain string line inside a block (e.g. description) -> skip support
            raise ValueError(f"expected 'key: value', got {text!r} (line-ish {idx})")
        rest = rest.strip()
        if rest == "":
            if idx + 1 < len(lines) and lines[idx + 1][0] > indent:
                nind, ntext = lines[idx + 1]
                if ntext.startswith(_LEAD):
                    d[key], idx = _seq(lines, idx + 1, nind)
                else:
                    d[key], idx = _block(lines, idx + 1, nind)
            else:
                d[key] = None
                idx += 1
        else:
            d[key] = _parse_scalar(rest)
            idx += 1
    return d, idx


def _seq(lines, idx, indent):
    """Parse list items at exactly `indent`, each starting with '- '.

    Item forms:
      '- scalar'
      '- key: value' (+ optional continuation keys at `indent + 2`)
      '- ' alone (nested dict/list at deeper indentation)
    """
    items = []
    while idx < len(lines):
        ind, text = lines[idx]
        if ind != indent or not text.startswith(_LEAD):
            break
        rest = text[len(_LEAD):].strip()
        if rest == "":
            if idx + 1 < len(lines) and lines[idx + 1][0] > indent:
                nind, ntext = lines[idx + 1]
                if ntext.startswith(_LEAD):
                    sub, idx = _seq(lines, idx + 1, nind)
                else:
                    sub, idx = _block(lines, idx + 1, nind)
                items.append(sub)
            else:
                items.append(None)
                idx += 1
        elif rest.find(":") > 0 and " " not in rest[:rest.find(":")].strip():
            # map item whose first key sits on the dash line
            item = {}
            k, _, v = rest.partition(":")
            item[k.strip()] = _parse_scalar(v.strip())
            key_indent = indent + len(_LEAD) + 1   # column after '- '
            if idx + 1 < len(lines) and lines[idx + 1][0] == key_indent \
                    and not lines[idx + 1][1].startswith(_LEAD):
                sub, idx2 = _block(lines, idx + 1, key_indent)
                item.update(sub)
                idx = idx2
            else:
                idx += 1
            items.append(item)
        else:
            items.append(_parse_scalar(rest))
            idx += 1
    return items, idx


def load_file(path: str):
    with open(path, encoding="utf-8") as fh:
        return load_yaml(fh.read())
