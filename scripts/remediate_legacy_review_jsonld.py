#!/usr/bin/env python3
"""
Fail-closed remediation for legacy review JSON-LD.

Default mode is DRY RUN.  The script only considers review/*.html pages and
removes these fields from JSON-LD objects whose @type includes "Review":

- itemReviewed.offers
- itemReviewed.aggregateRating
- reviewRating

The first-run candidate-page cardinality must be exactly 721 before any write.
Use --apply only after independent review of a successful dry run.

The patcher preserves every byte outside the exact JSON member spans removed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


EXPECTED_FIRST_RUN_PAGES = 721
REPORT_REL = Path("docs/recovery/legacy-review-jsonld-remediation-report.json")
SCRIPT_RE = re.compile(
    r'(<script\b[^>]*\btype\s*=\s*["\']application/ld\+json["\'][^>]*>)(.*?)(</script\s*>)',
    re.IGNORECASE | re.DOTALL,
)
DECODER = json.JSONDecoder()


@dataclass
class Member:
    key: str
    start: int
    key_end: int
    value_start: int
    value_end: int
    end: int
    value_node: "Node"


@dataclass
class Node:
    kind: str
    start: int
    end: int
    members: list[Member] = field(default_factory=list)
    items: list["Node"] = field(default_factory=list)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def skip_ws(src: str, i: int) -> int:
    while i < len(src) and src[i] in " \t\r\n":
        i += 1
    return i


def parse_value(src: str, i: int) -> Node:
    i = skip_ws(src, i)
    if i >= len(src):
        raise ValueError("unexpected EOF")
    ch = src[i]
    if ch == "{":
        return parse_object(src, i)
    if ch == "[":
        return parse_array(src, i)
    _, end = DECODER.raw_decode(src, i)
    return Node(kind="scalar", start=i, end=end)


def parse_object(src: str, i: int) -> Node:
    start = i
    i += 1
    members: list[Member] = []
    i = skip_ws(src, i)
    if i < len(src) and src[i] == "}":
        return Node(kind="object", start=start, end=i + 1, members=[])

    while True:
        i = skip_ws(src, i)
        pair_start = i
        key, key_end = DECODER.raw_decode(src, i)
        if not isinstance(key, str):
            raise ValueError(f"object key is not string at offset {i}")
        i = skip_ws(src, key_end)
        if i >= len(src) or src[i] != ":":
            raise ValueError(f"missing colon after object key {key!r}")
        i += 1
        value_start = skip_ws(src, i)
        value_node = parse_value(src, value_start)
        i = skip_ws(src, value_node.end)
        pair_end = value_node.end
        members.append(
            Member(
                key=key,
                start=pair_start,
                key_end=key_end,
                value_start=value_start,
                value_end=value_node.end,
                end=pair_end,
                value_node=value_node,
            )
        )
        if i >= len(src):
            raise ValueError("unexpected EOF in object")
        if src[i] == ",":
            i += 1
            continue
        if src[i] == "}":
            return Node(kind="object", start=start, end=i + 1, members=members)
        raise ValueError(f"unexpected character {src[i]!r} in object at {i}")


def parse_array(src: str, i: int) -> Node:
    start = i
    i += 1
    items: list[Node] = []
    i = skip_ws(src, i)
    if i < len(src) and src[i] == "]":
        return Node(kind="array", start=start, end=i + 1, items=[])

    while True:
        item = parse_value(src, i)
        items.append(item)
        i = skip_ws(src, item.end)
        if i >= len(src):
            raise ValueError("unexpected EOF in array")
        if src[i] == ",":
            i += 1
            continue
        if src[i] == "]":
            return Node(kind="array", start=start, end=i + 1, items=items)
        raise ValueError(f"unexpected character {src[i]!r} in array at {i}")


def member_map(node: Node) -> dict[str, Member]:
    if node.kind != "object":
        return {}
    return {m.key: m for m in node.members}


def scalar_value(src: str, node: Node) -> Any:
    return json.loads(src[node.start:node.end])


def object_is_review(src: str, node: Node) -> bool:
    if node.kind != "object":
        return False
    mm = member_map(node)
    t = mm.get("@type")
    if not t:
        return False
    try:
        value = scalar_value(src, t.value_node)
    except Exception:
        return False
    if value == "Review":
        return True
    if isinstance(value, list) and "Review" in value:
        return True
    return False


def walk(node: Node) -> Iterable[Node]:
    yield node
    if node.kind == "object":
        for m in node.members:
            yield from walk(m.value_node)
    elif node.kind == "array":
        for item in node.items:
            yield from walk(item)


def direct_member(node: Node, key: str) -> Member | None:
    for m in node.members:
        if m.key == key:
            return m
    return None


def spans_for_removed_members(node: Node, remove_keys: set[str]) -> list[tuple[int, int]]:
    """
    Return non-overlapping spans that remove selected members while keeping
    the surrounding JSON object valid. Bytes outside those spans are preserved.
    """
    if node.kind != "object":
        return []
    members = node.members
    remove_idx = {i for i, m in enumerate(members) if m.key in remove_keys}
    if not remove_idx:
        return []

    kept_idx = [i for i in range(len(members)) if i not in remove_idx]
    if not kept_idx:
        if not members:
            return []
        return [(members[0].start, members[-1].end)]

    spans: list[tuple[int, int]] = []
    i = 0
    while i < len(members):
        if i not in remove_idx:
            i += 1
            continue
        run_start = i
        while i + 1 < len(members) and (i + 1) in remove_idx:
            i += 1
        run_end = i

        next_kept = next((j for j in range(run_end + 1, len(members)) if j not in remove_idx), None)
        prev_kept = next((j for j in range(run_start - 1, -1, -1) if j not in remove_idx), None)

        if next_kept is not None:
            # Remove selected member(s) plus the separators/whitespace before
            # the next kept key.
            spans.append((members[run_start].start, members[next_kept].start))
        elif prev_kept is not None:
            # Selected run is at the end: remove the comma/whitespace after the
            # previous kept value plus the selected member(s).
            spans.append((members[prev_kept].value_end, members[run_end].end))
        else:
            spans.append((members[run_start].start, members[run_end].end))
        i += 1
    return spans


def target_spans(src: str, root: Node) -> tuple[list[tuple[int, int]], dict[str, int]]:
    spans: list[tuple[int, int]] = []
    counts = {"reviewRating": 0, "offers": 0, "aggregateRating": 0}

    for node in walk(root):
        if not object_is_review(src, node):
            continue

        rr = direct_member(node, "reviewRating")
        if rr is not None:
            spans.extend(spans_for_removed_members(node, {"reviewRating"}))
            counts["reviewRating"] += 1

        item = direct_member(node, "itemReviewed")
        if item is None:
            continue

        candidates: list[Node] = []
        if item.value_node.kind == "object":
            candidates = [item.value_node]
        elif item.value_node.kind == "array":
            candidates = [n for n in item.value_node.items if n.kind == "object"]

        for obj in candidates:
            mm = member_map(obj)
            keys = {k for k in ("offers", "aggregateRating") if k in mm}
            if keys:
                spans.extend(spans_for_removed_members(obj, keys))
                counts["offers"] += int("offers" in keys)
                counts["aggregateRating"] += int("aggregateRating" in keys)

    # Merge exact duplicates only. Overlap means the parser/planner made an
    # unsafe plan and must fail closed.
    unique = sorted(set(spans))
    for (a0, a1), (b0, b1) in zip(unique, unique[1:]):
        if b0 < a1:
            raise ValueError(f"overlapping edit spans: {(a0, a1)} and {(b0, b1)}")
    return unique, counts


def apply_spans(text: str, spans: list[tuple[int, int]]) -> str:
    out = text
    for start, end in sorted(spans, reverse=True):
        out = out[:start] + out[end:]
    return out


def process_ldjson_body(body: str) -> tuple[str, dict[str, int]]:
    root = parse_value(body, 0)
    if skip_ws(body, root.end) != len(body):
        raise ValueError("trailing non-whitespace after JSON value")

    # Ensure standard JSON parser agrees before planning edits.
    json.loads(body)

    spans, counts = target_spans(body, root)
    transformed = apply_spans(body, spans)

    # Validate transformed JSON and confirm no targeted Review fields remain.
    transformed_root = parse_value(transformed, 0)
    if skip_ws(transformed, transformed_root.end) != len(transformed):
        raise ValueError("transformed JSON has trailing non-whitespace")
    json.loads(transformed)
    remaining, _ = target_spans(transformed, transformed_root)
    if remaining:
        raise ValueError("targeted Review fields remain after transformation")

    return transformed, counts


def transform_page(text: str) -> tuple[str, dict[str, int]]:
    totals = {"reviewRating": 0, "offers": 0, "aggregateRating": 0}
    pieces: list[str] = []
    cursor = 0
    changed = False

    for match in SCRIPT_RE.finditer(text):
        pieces.append(text[cursor:match.start()])
        open_tag, body, close_tag = match.group(1), match.group(2), match.group(3)
        try:
            new_body, counts = process_ldjson_body(body)
        except Exception as exc:
            raise ValueError(f"malformed/relevant JSON-LD block at {match.start()}: {exc}") from exc

        if new_body != body:
            changed = True
        for k in totals:
            totals[k] += counts[k]
        pieces.extend([open_tag, new_body, close_tag])
        cursor = match.end()

    pieces.append(text[cursor:])
    transformed = "".join(pieces)

    # Guard: no bytes outside application/ld+json bodies may change.
    def skeleton(s: str) -> str:
        return SCRIPT_RE.sub(lambda m: m.group(1) + "__LDJSON_BODY__" + m.group(3), s)

    if skeleton(text) != skeleton(transformed):
        raise ValueError("non-JSON-LD bytes changed")

    if not changed:
        return text, totals
    return transformed, totals


def atomic_write(path: Path, content: str) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write validated transforms atomically")
    parser.add_argument("--root", default=None, help="repository root; defaults to parent of scripts/")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    review_dir = root / "review"
    report_path = root / REPORT_REL

    if not review_dir.is_dir():
        print(json.dumps({"ok": False, "error": f"missing review directory: {review_dir}"}))
        return 2

    pages = sorted(review_dir.glob("*.html"))
    plans: list[dict[str, Any]] = []
    aggregate = {"reviewRating": 0, "offers": 0, "aggregateRating": 0}

    for path in pages:
        original = path.read_text(encoding="utf-8")
        try:
            transformed, counts = transform_page(original)
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc), "file": str(path.relative_to(root))}, ensure_ascii=False))
            return 2

        if transformed != original:
            rel = str(path.relative_to(root)).replace(os.sep, "/")
            plans.append(
                {
                    "path": rel,
                    "before_sha256": sha256_text(original),
                    "after_sha256": sha256_text(transformed),
                    "content": transformed,
                    "removals": counts,
                }
            )
            for k in aggregate:
                aggregate[k] += counts[k]

    candidate_count = len(plans)
    idempotent_marker = report_path.exists()

    if candidate_count == 0:
        result = {
            "ok": bool(idempotent_marker),
            "mode": "APPLY" if args.apply else "DRY_RUN",
            "candidate_pages": 0,
            "expected_first_run_pages": EXPECTED_FIRST_RUN_PAGES,
            "idempotent_marker_present": idempotent_marker,
            "message": "idempotent no-op after prior apply" if idempotent_marker else "unexpected zero candidates without prior apply marker",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if idempotent_marker else 2

    if candidate_count != EXPECTED_FIRST_RUN_PAGES:
        print(
            json.dumps(
                {
                    "ok": False,
                    "mode": "APPLY" if args.apply else "DRY_RUN",
                    "candidate_pages": candidate_count,
                    "expected_first_run_pages": EXPECTED_FIRST_RUN_PAGES,
                    "error": "candidate cardinality mismatch; aborting before first write",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    public_report = {
        "ok": True,
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "candidate_pages": candidate_count,
        "expected_first_run_pages": EXPECTED_FIRST_RUN_PAGES,
        "aggregate_removals": aggregate,
        "files": [
            {
                "path": p["path"],
                "before_sha256": p["before_sha256"],
                "after_sha256": p["after_sha256"],
                "removals": p["removals"],
            }
            for p in plans
        ],
    }

    if not args.apply:
        print(json.dumps(public_report, ensure_ascii=False, indent=2))
        return 0

    # All 721 transforms have already been built and validated in memory.
    for p in plans:
        atomic_write(root / p["path"], p["content"])

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_payload = dict(public_report)
    report_payload["mode"] = "APPLY_COMPLETE"
    atomic_write(report_path, json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n")

    # Post-write verification.
    remaining_pages = 0
    for path in pages:
        current = path.read_text(encoding="utf-8")
        transformed, _ = transform_page(current)
        if transformed != current:
            remaining_pages += 1
    if remaining_pages != 0:
        print(json.dumps({"ok": False, "error": "post-apply verification found remaining candidates", "remaining_pages": remaining_pages}))
        return 3

    print(json.dumps(report_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
