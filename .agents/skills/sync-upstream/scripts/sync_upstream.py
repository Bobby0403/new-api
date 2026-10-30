#!/usr/bin/env python3
"""Merge QuantumNous/new-api main into a dp-router sync branch.

One policy, implemented here rather than in prose:

- A line changed by only one side is kept. An overlapping equal-length line follows the ledger.
- Unequal replacements whose base ranges overlap are one region and are emitted once.
  A multi-line delete is one of those replacements. A one-sided insert inside the other
  side's replacement is kept. When only one side's replacement also inserts a line,
  lines that still match are merged per line.
- Inserts at the same point are both kept, upstream block then ours. When one insertion
  is a subsequence of the other, only the longer block is kept. Otherwise both blocks
  stay intact even if they share a line. A unique line moved to the end of the file is
  not reinserted when the other side's edit of that line wins.
- Locale JSON is a three-way key merge. A key only one side changed follows that side.
- go.sum and web/bun.lock are regenerated, never hunk-merged.
- go.mod require lines, including a single-line require, are a union taken from both
  parents. Versions follow upstream unless pins.txt says otherwise. Differing module
  or go lines stop the merge.
- A conflict this module cannot classify stops the merge. Nothing is committed.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

ORIGIN_URLS = {
    "git@github.com:deeppatternai/dp-router.git",
    "https://github.com/deeppatternai/dp-router.git",
}
UPSTREAM_URLS = {
    "https://github.com/QuantumNous/new-api.git",
    "git@github.com:QuantumNous/new-api.git",
}
UPSTREAM_FETCH = "https://github.com/QuantumNous/new-api.git"

# A path is ledger when it equals an entry or lives under a directory entry.
LEDGER_PREFIXES = (
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "Dockerfile.dev",
    "common/constants.go",
    "common/endpoint_defaults.go",
    "controller/channel-billing.go",
    "controller/misc.go",
    "docs/site",
    "electron/package.json",
    "main.go",
    "middleware/openai_video_api.go",
    "middleware/task_plugin.go",
    "model/option.go",
    "plugins/embed.go",
    "plugins/other",
    "router/task-plugin-protocol-router.go",
    "service/distlock.go",
    "service/distributed_poll.go",
    "service/system_task.go",
    "service/task_polling.go",
    "web/Jenkinsfile",
    "web/src/components/layout/components/footer.tsx",
    "web/src/features/home/components/sections/hero.tsx",
    "web/src/features/system-settings",
    "web/src/lib/status-query.ts",
)

REQUIRE_BLOCK_RE = re.compile(r"(?ms)^require \((.*?)^\)")
REQUIRE_LINE_RE = re.compile(r"^\s*([A-Za-z0-9_][A-Za-z0-9_./-]*)\s+(\S+)", re.M)
SINGLE_REQUIRE_RE = re.compile(r"(?m)^require[ \t]+([A-Za-z0-9_./-]+)[ \t]+(\S+)[ \t]*(?://.*)?$")


class Stop(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def _repo_path(path: str) -> str:
    name = path.replace("\\", "/")
    if name.startswith("./"):
        name = name[2:]
    return name


def merge_kind(path: str) -> str:
    name = _repo_path(path)
    if name.endswith(("go.sum", "bun.lock", "bun.lockb")):
        return "regen"
    if name.startswith("web/src/i18n/locales/") and name.endswith(".json"):
        return "locale"
    if name.endswith("go.mod"):
        return "go.mod"
    if name.endswith((".json", ".yml", ".yaml", ".toml")):
        return "human"
    return "text"


def is_ledger(path: str) -> bool:
    name = _repo_path(path)
    for prefix in LEDGER_PREFIXES:
        if name == prefix or name.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def parse_unmerged_z(blob: bytes) -> list[tuple[str, str]]:
    """Parse `git ls-files -u -z` into (stage, path). Paths may contain spaces."""
    found: list[tuple[str, str]] = []
    for record in blob.split(b"\0"):
        if not record:
            continue
        meta, sep, path_b = record.partition(b"\t")
        if sep != b"\t":
            raise Stop(1, "git ls-files -u record has no tab: " + record.decode("utf-8", "replace"))
        parts = meta.decode("utf-8", "replace").split(" ")
        if len(parts) < 3:
            raise Stop(1, "git ls-files -u record is not mode/sha/stage")
        found.append((parts[2], path_b.decode("utf-8", "surrogateescape")))
    return found


def _opcodes(base: list[str], other: list[str]) -> list[tuple[str, int, int, int, int]]:
    matcher = difflib.SequenceMatcher(a=base, b=other, autojunk=False)
    exploded: list[tuple[str, int, int, int, int]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace" and (i2 - i1) == (j2 - j1):
            for offset in range(i2 - i1):
                exploded.append(("replace", i1 + offset, i1 + offset + 1, j1 + offset, j1 + offset + 1))
            continue
        if tag == "delete" and i2 - i1 == 1:
            exploded.append(("delete", i1, i2, j1, j2))
            continue
        if tag == "equal":
            for offset in range(i2 - i1):
                exploded.append(("equal", i1 + offset, i1 + offset + 1, j1 + offset, j1 + offset + 1))
            continue
        exploded.append((tag, i1, i2, j1, j2))
    return exploded


def _describe(base: list[str], other: list[str]) -> tuple[list[list[str]], dict[int, tuple], list[tuple[int, int, list[str]]]]:
    inserts = [[] for _ in range(len(base) + 1)]
    line_op: dict[int, tuple] = {}
    spans: list[tuple[int, int, list[str]]] = []
    for tag, i1, i2, j1, j2 in _opcodes(base, other):
        if tag == "insert":
            inserts[i1].extend(other[j1:j2])
        elif tag == "equal":
            line_op[i1] = ("equal", other[j1])
        elif tag == "delete" and i2 - i1 == 1:
            line_op[i1] = ("delete",)
        elif tag == "replace" and i2 - i1 == 1 and j2 - j1 == 1:
            line_op[i1] = ("replace", other[j1:j2])
        else:
            spans.append((i1, i2, other[j1:j2]))
            for index in range(i1, i2):
                line_op[index] = ("span", len(spans) - 1)
    return inserts, line_op, spans


def _lines_of(op: tuple) -> list[str]:
    if op[0] == "equal":
        return [op[1]]
    if op[0] == "delete":
        return []
    if op[0] == "replace":
        return list(op[1])
    raise Stop(3, "internal merge saw an unresolved span")


def _dropped(lines: list[str]) -> str:
    return "".join(lines) or "(deleted)\n"


def _is_prefix(short: list[str], long: list[str]) -> bool:
    return len(short) <= len(long) and long[: len(short)] == short


def _merge_inserts(ours: list[str], theirs: list[str]) -> tuple[list[str], list[str]]:
    """Keep both insertion blocks. An exact prefix extension is absorbed once."""
    if not ours:
        return list(theirs), []
    if not theirs or ours == theirs:
        return list(ours), []
    if _is_prefix(ours, theirs):
        return list(theirs), []
    if _is_prefix(theirs, ours):
        return list(ours), []
    if not theirs[-1].endswith(("\n", "\r")):
        raise Stop(3, "same-point EOF inserts without a separating newline require human resolution")
    return list(theirs) + list(ours), []


def _op_removed_line(op: tuple, spans: list[tuple[int, int, list[str]]], base_line: str) -> bool:
    if op[0] == "delete":
        return True
    if op[0] == "span":
        return base_line not in spans[op[1]][2]
    return False


def _op_replaced_line(op: tuple, spans: list[tuple[int, int, list[str]]], base_line: str) -> bool:
    if op[0] == "replace":
        return True
    if op[0] == "span":
        return base_line not in spans[op[1]][2]
    return False


def _has_ambiguous_insert_move(
    inserts: list[str],
    base_lines: list[str],
    own_ops: dict[int, tuple],
    opposite_ops: dict[int, tuple],
    own_spans: list[tuple[int, int, list[str]]],
    opposite_spans: list[tuple[int, int, list[str]]],
) -> bool:
    if not inserts:
        return False
    for position, base_line in enumerate(base_lines):
        if base_lines.count(base_line) != 1:
            continue
        if position not in own_ops or position not in opposite_ops:
            continue
        moved_copy = base_line in inserts and _op_removed_line(own_ops[position], own_spans, base_line)
        reused_context = (
            len(inserts) >= 2
            and own_ops[position][0] == "equal"
            and _op_replaced_line(opposite_ops[position], opposite_spans, base_line)
        )
        if moved_copy or reused_context:
            return True
    return False


def _take_inserts(
    index: int,
    base_lines: list[str],
    our_ins: list[list[str]],
    their_ins: list[list[str]],
    our_ops: dict[int, tuple],
    their_ops: dict[int, tuple],
    our_spans: list[tuple[int, int, list[str]]],
    their_spans: list[tuple[int, int, list[str]]],
    keep_ours: bool,
    dropped: list[str],
) -> list[str]:
    del keep_ours, dropped
    our_lines = our_ins[index]
    their_lines = their_ins[index]
    ambiguous_ours = _has_ambiguous_insert_move(
        our_lines, base_lines, our_ops, their_ops, our_spans, their_spans
    )
    ambiguous_theirs = _has_ambiguous_insert_move(
        their_lines, base_lines, their_ops, our_ops, their_spans, our_spans
    )
    if ambiguous_ours or ambiguous_theirs:
        raise Stop(3, "ambiguous moved or reused base line in an insertion requires human resolution")
    chosen, _lost = _merge_inserts(our_lines, their_lines)
    return chosen


def _choose_line(our_op: tuple, their_op: tuple, keep_ours: bool) -> tuple[list[str], list[str]]:
    if our_op == their_op or our_op[0] == "equal":
        return _lines_of(their_op if our_op[0] == "equal" else our_op), []
    if their_op[0] == "equal":
        return _lines_of(our_op), []
    if keep_ours:
        return _lines_of(our_op), [_dropped(_lines_of(their_op))]
    return _lines_of(their_op), [_dropped(_lines_of(our_op))]


def _best_alignment(base_lines: list[str], repl_lines: list[str], cutoff: float = 0.8) -> dict[int, int] | None:
    """Pair each base line with one replacement line. Fail when a pair is weak or crossed."""
    mapping: dict[int, int] = {}
    used: set[int] = set()
    for offset, base in enumerate(base_lines):
        best_j: int | None = None
        best_ratio = 0.0
        second = 0.0
        for repl_index, repl in enumerate(repl_lines):
            if repl_index in used:
                continue
            ratio = difflib.SequenceMatcher(None, base, repl, autojunk=False).ratio()
            if ratio > best_ratio:
                second = best_ratio
                best_ratio, best_j = ratio, repl_index
            elif ratio > second:
                second = ratio
        if best_j is None or best_ratio < cutoff or (second >= cutoff and best_ratio - second < 0.05):
            return None
        if used and best_j <= max(used):
            return None
        mapping[offset] = best_j
        used.add(best_j)
    return mapping


def _single_span(
    ops: dict[int, tuple],
    spans: list[tuple[int, int, list[str]]],
    index: int,
    end: int,
) -> list[str] | None:
    op = ops[index]
    if op[0] != "span":
        return None
    start, span_end, lines = spans[op[1]]
    if start != index or span_end != end:
        return None
    return lines


def _as_line(base_line: str, repl_line: str) -> tuple:
    if repl_line == base_line:
        return ("equal", repl_line)
    return ("replace", [repl_line])


def _emit_split(
    out: list[str],
    dropped: list[str],
    base_lines: list[str],
    our_ops: dict[int, tuple],
    their_ops: dict[int, tuple],
    our_ins: list[list[str]],
    their_ins: list[list[str]],
    index: int,
    repl: list[str],
    mapping: dict[int, int],
    span_side: str,
    keep_ours: bool,
) -> None:
    previous = -1
    for offset, repl_index in sorted(mapping.items()):
        out.extend(repl[previous + 1 : repl_index])
        base_index = index + offset
        if base_index != index:
            if span_side == "theirs":
                out.extend(our_ins[base_index])
            else:
                out.extend(their_ins[base_index])
        span_op = _as_line(base_lines[base_index], repl[repl_index])
        if span_side == "theirs":
            chosen, lost = _choose_line(our_ops[base_index], span_op, keep_ours)
        else:
            chosen, lost = _choose_line(span_op, their_ops[base_index], keep_ours)
        out.extend(chosen)
        dropped.extend(lost)
        previous = repl_index
    out.extend(repl[previous + 1 :])


def _try_split(
    out: list[str],
    dropped: list[str],
    base_lines: list[str],
    our_ops: dict[int, tuple],
    their_ops: dict[int, tuple],
    our_spans: list[tuple[int, int, list[str]]],
    their_spans: list[tuple[int, int, list[str]]],
    our_ins: list[list[str]],
    their_ins: list[list[str]],
    index: int,
    end: int,
    keep_ours: bool,
) -> bool:
    """Split one side's replacement when its lines still match the base. Both spans stay atomic."""
    our_span = any(our_ops[pos][0] == "span" for pos in range(index, end))
    their_span = any(their_ops[pos][0] == "span" for pos in range(index, end))
    if our_span == their_span:
        return False
    if their_span:
        repl = _single_span(their_ops, their_spans, index, end)
        side = "theirs"
    else:
        repl = _single_span(our_ops, our_spans, index, end)
        side = "ours"
    if repl is None:
        return False
    mapping = _best_alignment(base_lines[index:end], repl)
    if mapping is None:
        return False
    _emit_split(out, dropped, base_lines, our_ops, their_ops, our_ins, their_ins, index, repl, mapping, side, keep_ours)
    return True


def merge_texts(base: str, ours: str, theirs: str, keep_ours: bool) -> tuple[str, list[str]]:
    """Merge by line. A line only one side changed is kept. Overlap follows the ledger."""
    base_lines = base.splitlines(keepends=True)
    our_lines = ours.splitlines(keepends=True)
    their_lines = theirs.splitlines(keepends=True)
    our_ins, our_ops, our_spans = _describe(base_lines, our_lines)
    their_ins, their_ops, their_spans = _describe(base_lines, their_lines)
    out: list[str] = []
    dropped: list[str] = []
    index = 0
    while index < len(base_lines):
        out.extend(
            _take_inserts(
                index,
                base_lines,
                our_ins,
                their_ins,
                our_ops,
                their_ops,
                our_spans,
                their_spans,
                keep_ours,
                dropped,
            )
        )
        our_op = our_ops[index]
        their_op = their_ops[index]
        if our_op[0] == "span" or their_op[0] == "span":
            end = _region_end(index, our_ops, their_ops, our_spans, their_spans)
            _reject_insert_inside_deletion(index, end, our_ops, their_ops, our_spans, their_spans, our_ins, their_ins)
            if _try_split(out, dropped, base_lines, our_ops, their_ops, our_spans, their_spans, our_ins, their_ins, index, end, keep_ours):
                index = end
                continue
            our_base = any(our_ops[pos][0] != "equal" for pos in range(index, end))
            their_base = any(their_ops[pos][0] != "equal" for pos in range(index, end))
            our_body = _span_body(base_lines, our_ops, our_spans, our_ins, index, end)
            their_body = _span_body(base_lines, their_ops, their_spans, their_ins, index, end)
            if our_base and not their_base:
                out.extend(our_body)
                for pos in range(index + 1, end):
                    out.extend(their_ins[pos])
            elif their_base and not our_base:
                out.extend(their_body)
                for pos in range(index + 1, end):
                    out.extend(our_ins[pos])
            elif our_body == their_body or not our_base:
                out.extend(their_body)
            elif keep_ours:
                out.extend(our_body)
                dropped.append(_dropped(their_body))
            else:
                out.extend(their_body)
                dropped.append(_dropped(our_body))
            index = end
            continue
        chosen, lost = _choose_line(our_op, their_op, keep_ours)
        out.extend(chosen)
        dropped.extend(lost)
        index += 1
    out.extend(
        _take_inserts(
            len(base_lines),
            base_lines,
            our_ins,
            their_ins,
            our_ops,
            their_ops,
            our_spans,
            their_spans,
            keep_ours,
            dropped,
        )
    )
    return "".join(out), dropped


def _reject_insert_inside_deletion(
    index: int,
    end: int,
    our_ops: dict[int, tuple],
    their_ops: dict[int, tuple],
    our_spans: list[tuple[int, int, list[str]]],
    their_spans: list[tuple[int, int, list[str]]],
    our_ins: list[list[str]],
    their_ins: list[list[str]],
) -> None:
    sides = (
        (our_ops, our_spans, their_ins, "ours"),
        (their_ops, their_spans, our_ins, "theirs"),
    )
    for operations, spans, opposite_inserts, side in sides:
        span_ids = {
            operations[pos][1]
            for pos in range(index, end)
            if operations[pos][0] == "span"
        }
        for span_id in span_ids:
            span_start, span_end, replacement = spans[span_id]
            if replacement:
                continue
            interior_start = max(index, span_start + 1)
            interior_end = min(end, span_end)
            if any(opposite_inserts[pos] for pos in range(interior_start, interior_end)):
                raise Stop(3, f"one-sided insert inside {side} deletion span requires human resolution")


def _region_end(
    index: int,
    our_ops: dict[int, tuple],
    their_ops: dict[int, tuple],
    our_spans: list[tuple[int, int, list[str]]],
    their_spans: list[tuple[int, int, list[str]]],
) -> int:
    """Cover every replacement span that overlaps the region. Adjacent spans stay outside."""
    end = index + 1
    if our_ops[index][0] == "span":
        end = max(end, our_spans[our_ops[index][1]][1])
    if their_ops[index][0] == "span":
        end = max(end, their_spans[their_ops[index][1]][1])
    grew = True
    while grew:
        grew = False
        for pos in range(index, end):
            for ops, spans in ((our_ops, our_spans), (their_ops, their_spans)):
                op = ops[pos]
                if op[0] != "span":
                    continue
                span_end = spans[op[1]][1]
                if span_end > end:
                    end = span_end
                    grew = True
    return end


def _span_body(
    base: list[str],
    ops: dict[int, tuple],
    spans: list[tuple[int, int, list[str]]],
    inserts: list[list[str]],
    start: int,
    end: int,
) -> list[str]:
    body: list[str] = []
    pos = start
    seen: set[int] = set()
    while pos < end:
        op = ops[pos]
        if op[0] == "span":
            span_id = op[1]
            if span_id not in seen:
                seen.add(span_id)
                _start, span_end, lines = spans[span_id]
                if _start != start:
                    body.extend(inserts[_start])
                body.extend(lines)
                for cursor in range(_start + 1, min(span_end, end)):
                    body.extend(inserts[cursor])
            pos += 1
            continue
        body.extend(inserts[pos] if pos != start else [])
        body.extend(_lines_of(op))
        pos += 1
    return body


def _translation_map(text: str, label: str) -> dict:
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Stop(3, f"{label} locale JSON is not parseable: {exc}") from exc
    if set(doc) != {"translation"} or not isinstance(doc["translation"], dict):
        raise Stop(3, f"{label} locale JSON is not a single translation object")
    return doc["translation"]


def merge_locale(base: str, ours: str, theirs: str) -> tuple[str, list[str]]:
    """Three-way key merge. A key only one side changed follows that side. Both changed keeps ours."""
    base_map = _translation_map(base, "base")
    our_map = _translation_map(ours, "ours")
    their_map = _translation_map(theirs, "theirs")
    merged: dict = {}
    dropped: list[str] = []
    ordered = list(their_map) + [key for key in our_map if key not in their_map]
    ordered += [key for key in base_map if key not in their_map and key not in our_map]
    for key in ordered:
        in_base, in_ours, in_theirs = key in base_map, key in our_map, key in their_map
        base_value, our_value, their_value = base_map.get(key), our_map.get(key), their_map.get(key)
        if in_ours and in_theirs:
            if our_value == their_value:
                merged[key] = our_value
            elif in_base and our_value == base_value:
                merged[key] = their_value
            elif in_base and their_value == base_value:
                merged[key] = our_value
            else:
                merged[key] = our_value
                dropped.append(f"{key}={their_value}")
        elif in_ours and in_base and our_value == base_value:
            dropped.append(f"{key} deleted upstream")
        elif in_ours:
            merged[key] = our_value
            if in_base:
                dropped.append(f"{key} deleted upstream")
        elif in_theirs and not in_base:
            merged[key] = their_value
        elif in_theirs and their_value != base_value:
            dropped.append(f"{key}={their_value}")
    return json.dumps({"translation": merged}, ensure_ascii=False, indent=2) + "\n", dropped


def _require_map(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for block in REQUIRE_BLOCK_RE.findall(text):
        for match in REQUIRE_LINE_RE.finditer(block):
            found[match.group(1)] = match.group(2)
    for match in SINGLE_REQUIRE_RE.finditer(text):
        found[match.group(1)] = match.group(2)
    return found


def _outside_requires(text: str) -> str:
    """Blank every require form the same way so single-line and block forms compare equal."""
    without_blocks = REQUIRE_BLOCK_RE.sub("\n", text)
    without_requires = SINGLE_REQUIRE_RE.sub("", without_blocks)
    return re.sub(r"\n{3,}", "\n\n", without_requires)


def pin_drift(before: dict[str, str], after: dict[str, str], pins: dict[str, str]) -> list[str]:
    """Pins that were in the merged module list and tidy removed or rewrote."""
    drifted = []
    for module, version in pins.items():
        if module in before and (module not in after or after[module] != version):
            drifted.append(module)
    return sorted(drifted)


def passed_top_level_tests(output: str) -> list[str]:
    names = []
    for line in output.splitlines():
        if not line.startswith("--- PASS: "):
            continue
        name = line[len("--- PASS: ") :].split()[0]
        if "/" in name:
            continue
        names.append(name)
    return names


def require_named_passes(output: str, names: list[str]) -> None:
    found = passed_top_level_tests(output)
    if set(found) != set(names) or len(found) != len(set(found)):
        raise Stop(1, "expected tests " + ", ".join(names) + "; saw " + ", ".join(found))


def merge_go_mod(ours: str, theirs: str, pins: dict[str, str]) -> str:
    if _outside_requires(ours) != _outside_requires(theirs):
        raise Stop(3, "go.mod differs outside require blocks; not merging it")
    our_reqs = _require_map(ours)
    their_reqs = _require_map(theirs)
    chosen: dict[str, str] = dict(their_reqs)
    for module, version in our_reqs.items():
        if module not in chosen:
            chosen[module] = version
    for module, version in pins.items():
        if module in chosen:
            chosen[module] = version
    lines = [f"\t{module} {chosen[module]}" for module in chosen]
    block = "require (\n" + "\n".join(lines) + "\n)\n"
    base = SINGLE_REQUIRE_RE.sub("", REQUIRE_BLOCK_RE.sub("\n", theirs))
    base = re.sub(r"\n{3,}", "\n\n", base)
    if not base.endswith("\n"):
        base += "\n"
    return base + block


def load_pins(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pins: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise Stop(1, f"pin must be 'module version': {line}")
        pins[parts[0]] = parts[1]
    return pins


def decide_delete(code: str, path: str) -> str:
    """Return keep-ours, accept-delete, or take-theirs for a porcelain code."""
    if code == "UD":
        return "keep-ours" if is_ledger(path) else "accept-delete"
    if code == "DU":
        return "keep-deleted" if is_ledger(path) else "take-theirs"
    if code in {"AA", "UA", "AU", "DD"}:
        return "human"
    return "human"


def _identity_args() -> list[str]:
    """Use the existing git identity. Fall back only when no identity is configured."""
    name = subprocess.run(["git", "config", "--get", "user.name"], text=True, capture_output=True)
    email = subprocess.run(["git", "config", "--get", "user.email"], text=True, capture_output=True)
    if name.returncode == 0 and email.returncode == 0 and name.stdout.strip() and email.stdout.strip():
        return []
    return ["-c", "user.name=dp-router sync", "-c", "user.email=sync-upstream@deeppattern.local"]


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = ["git", *_identity_args(), "-C", str(root), *args]
    result = subprocess.run(command, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise Stop(1, (result.stderr or result.stdout or "git failed").strip())
    return result


def unmerged(root: Path) -> dict[str, set[str]]:
    result = git(root, "ls-files", "-u", "-z")
    stages: dict[str, set[str]] = {}
    for stage, path in parse_unmerged_z(result.stdout.encode("utf-8", "surrogateescape")):
        stages.setdefault(path, set()).add(stage)
    return stages


def _stage_blob(root: Path, stage: str, path: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), "show", f":{stage}:{path}"], capture_output=True)
    if result.returncode != 0:
        raise Stop(3, f"missing stage {stage} for {path}")
    return result.stdout


def _stage_mode(root: Path, stage: str, path: str) -> str:
    result = git(root, "ls-files", "-s", "--", path)
    for line in result.stdout.splitlines():
        metadata, separator, candidate = line.partition("\t")
        parts = metadata.split()
        if separator and candidate == path and len(parts) >= 3 and parts[2] == stage:
            return parts[0]
    raise Stop(3, f"missing stage {stage} mode for {path}")


def parse_status_z(blob: bytes) -> list[tuple[str, str]]:
    """Return unmerged (code, path) records from `git status --porcelain=v1 -z`."""
    parts = blob.split(b"\0")
    rows: list[tuple[str, str]] = []
    index = 0
    while index < len(parts):
        record = parts[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2:3] != b" ":
            raise Stop(1, "git status record is not 'XY path'")
        code = record[:2].decode("ascii", "replace")
        path = record[3:].decode("utf-8", "surrogateescape")
        if code[0] in {"R", "C"}:
            if index >= len(parts) or not parts[index]:
                raise Stop(1, "git status rename record is missing its old path")
            index += 1
        if "U" in code or code in {"AA", "DD"}:
            rows.append((code, path))
    return rows


def porcelain_unmerged(root: Path) -> list[tuple[str, str]]:
    result = git(root, "status", "--porcelain=v1", "-z", "-uall")
    return parse_status_z(result.stdout.encode("utf-8", "surrogateescape"))


def _report_file(root: Path) -> Path:
    path = Path(git(root, "rev-parse", "--git-path", "sync-upstream-report.txt").stdout.strip())
    if not path.is_absolute():
        path = root / path
    return path


def write_report(root: Path, lines: list[str]) -> Path:
    path = _report_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_report(root: Path, resume: bool) -> list[str]:
    """A fresh sync drops the previous report. A resume keeps it."""
    path = _report_file(root)
    if not resume:
        if path.exists():
            path.unlink()
        return []
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines == ["no conflict hunks"]:
        return []
    return lines


def assert_ledger(root: Path) -> None:
    checks: list[tuple[str, Path, str | None, str | None]] = [
        ("video default is false", root / "middleware/openai_video_api.go", r"GetEnvOrDefaultBool\(OpenAIVideoAPIEnabledEnv, false\)", None),
        ("video routes stay gated", root / "router/task-plugin-protocol-router.go", r"RestrictOpenAIVideoAPI", None),
        ("video endpoint template", root / "common/endpoint_defaults.go", r"EndpointTypeOpenAIVideo", None),
        ("job lock prefix", root / "service/distlock.go", r"dp:lock:job:", None),
        ("poll lock prefix", root / "service/distlock.go", r"dp:lock:poll:", None),
        ("channel balance uses the lock", root / "controller/channel-billing.go", r"RunExclusiveJob", None),
        ("brand name", root / "common/constants.go", r'SystemName = "DeepPattern API"', None),
        ("copyright defaults off", root / "common/constants.go", r"FooterCopyrightEnabled = false", None),
        ("status exposes copyright", root / "controller/misc.go", r"footer_copyright_enabled", None),
        ("hero docs switch", root / "web/src/features/home/components/sections/hero.tsx", r"docsEnabled", None),
        ("private plugins stay out of the factory", root / "plugins/embed.go", None, r"plugins/other"),
        ("image does not copy NOTICE", root / "Dockerfile", None, r"NOTICE"),
        ("dev image does not copy NOTICE", root / "Dockerfile.dev", None, r"NOTICE"),
    ]
    for label, path, required, forbidden in checks:
        if not path.is_file():
            raise Stop(1, f"ledger file missing: {label}: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if required and re.search(required, text) is None:
            raise Stop(1, f"ledger check failed: {label}")
        if forbidden and re.search(forbidden, text):
            raise Stop(1, f"ledger check found forbidden text: {label}")
    for prefix in LEDGER_PREFIXES:
        if not (root / prefix).exists():
            raise Stop(1, f"ledger path missing: {prefix}")
    extra_checks = [
        ("video flag documented", root / ".env.example", r"OPENAI_VIDEO_API_ENABLED=false", None),
        ("desktop brand", root / "electron/package.json", r"DeepPattern API", None),
        ("distributed poll is registered", root / "main.go", r"RegisterDistributedPoll", None),
        ("video generations stays off the public videos route", root / "middleware/task_plugin.go", r"/v1/video/generations", None),
        ("copyright option is stored", root / "model/option.go", r"FooterCopyrightEnabled", None),
        ("poll registration exists", root / "service/distributed_poll.go", r"func RegisterDistributedPoll", None),
        ("system task runner exists", root / "service/system_task.go", r"func StartSystemTaskRunner", None),
        ("task polling entry exists", root / "service/task_polling.go", r"func RunTaskPollingOnce", None),
        ("footer hides copyright unless enabled", root / "web/src/components/layout/components/footer.tsx", r"footerCopyrightEnabled !== true", None),
        ("settings default copyright off", root / "web/src/features/system-settings/site/index.tsx", r"FooterCopyrightEnabled: false", None),
        ("status reads the copyright flag", root / "web/src/lib/status-query.ts", r"footer_copyright_enabled", None),
    ]
    for label, path, required, forbidden in extra_checks:
        if not path.is_file():
            raise Stop(1, f"ledger file missing: {label}: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if required and re.search(required, text) is None:
            raise Stop(1, f"ledger check failed: {label}")
        if forbidden and re.search(forbidden, text):
            raise Stop(1, f"ledger check found forbidden text: {label}")
    for rel in ("plugins/other/alibaba/plugin.js", "plugins/other/muleroute/plugin.js", "web/Jenkinsfile"):
        if not (root / rel).is_file():
            raise Stop(1, f"ledger file missing: {rel}")
    if not (root / "docs/site").is_dir():
        raise Stop(1, "ledger directory missing: docs/site")
    ignore = (root / ".gitignore").read_text(encoding="utf-8", errors="replace").splitlines()
    if ".aqg" not in ignore:
        raise Stop(1, "ledger check failed: .gitignore must contain a .aqg line")
    gated = (root / "router/task-plugin-protocol-router.go").read_text(encoding="utf-8", errors="replace")
    if gated.count("RestrictOpenAIVideoAPI") < 3:
        raise Stop(1, "ledger check failed: OpenAI video routes are not all gated")


def _run_checked(root: Path, command: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd or root, text=True, capture_output=True)
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise Stop(1, output.strip() or "command failed")
    return output


def run_verification(root: Path) -> None:
    checks = [
        (
            [
                "TestDistLockSingleOwnerRenewAndRelease",
                "TestRunExclusiveJobSkipsWhilePeerHoldsLock",
                "TestBackgroundJobsEnabledUsesRedisBeforeMasterFlag",
            ],
            ["go", "test", "./service/", "-count=1", "-v", "-run", "^(TestDistLockSingleOwnerRenewAndRelease|TestRunExclusiveJobSkipsWhilePeerHoldsLock|TestBackgroundJobsEnabledUsesRedisBeforeMasterFlag)$"],
        ),
        (["TestOpenAIVideoAPIRejectsCallsWhenDisabled"], ["go", "test", "./router/", "-count=1", "-v", "-run", "^TestOpenAIVideoAPIRejectsCallsWhenDisabled$"]),
        (
            ["TestVideoGenerationsIsNotClaimedByOpenAIVideoProtocol", "TestVideoGenerationsClaimsOpenAIVideoModel"],
            ["go", "test", "./middleware/", "-count=1", "-v", "-run", "^TestVideoGenerations(IsNotClaimedByOpenAIVideoProtocol|ClaimsOpenAIVideoModel)$"],
        ),
        ([], ["go", "build", "./..."]),
    ]
    for names, command in checks:
        output = _run_checked(root, command)
        if names:
            require_named_passes(output, names)


def changed_names(root: Path) -> set[str]:
    diff = git(root, "diff", "--name-only", "HEAD")
    cached = git(root, "diff", "--cached", "--name-only")
    names = set(diff.stdout.splitlines()) | set(cached.stdout.splitlines())
    names.update(unmerged(root))
    return names


def regenerate(root: Path, names: set[str], pins: dict[str, str], report: list[str]) -> None:
    modules: set[Path] = set()
    for name in names:
        if name.endswith("go.mod") or name.endswith("go.sum"):
            modules.add(Path(name).parent)
    for module in modules:
        mod_file = root / module / "go.mod"
        before = _require_map(mod_file.read_text(encoding="utf-8")) if mod_file.is_file() else {}
        _run_checked(root, ["go", "mod", "tidy"], cwd=root / module)
        git(root, "add", "--", str(module / "go.mod"), str(module / "go.sum"))
        _run_checked(root, ["go", "mod", "tidy"], cwd=root / module)
        if git(root, "diff", "--exit-code", "--", str(module / "go.mod"), str(module / "go.sum"), check=False).returncode != 0:
            raise Stop(1, f"go mod tidy did not settle in {module}")
        after = _require_map(mod_file.read_text(encoding="utf-8")) if mod_file.is_file() else {}
        removed = sorted(set(before) - set(after))
        for module_name in removed:
            report.append(f"go.mod\t{module / 'go.mod'}\ttidy removed {module_name}")
        drifted = pin_drift(before, after, pins)
        if drifted:
            raise Stop(1, "go mod tidy did not keep pins: " + ", ".join(drifted))
    if any(name.startswith("web/") and name.endswith(("package.json", "bun.lock", "bun.lockb")) for name in names):
        _run_checked(root, ["bun", "install"], cwd=root / "web")
        _run_checked(root, ["bun", "install", "--frozen-lockfile"], cwd=root / "web")
        git(root, "add", "--", "web/package.json", "web/bun.lock")
    if any(name.startswith("web/src/i18n/locales/") for name in names):
        _run_checked(root, ["bun", "run", "i18n:sync"], cwd=root / "web")
        git(root, "add", "--", "web/src/i18n/locales")
        _run_checked(root, ["bun", "run", "i18n:sync"], cwd=root / "web")
        if git(root, "diff", "--exit-code", "--", "web/src/i18n/locales", check=False).returncode != 0:
            raise Stop(1, "i18n:sync did not settle")


def resolve_worktree(root: Path, pins: dict[str, str], report: list[str]) -> None:
    stages = unmerged(root)
    for code, path in porcelain_unmerged(root):
        if code == "UU":
            continue
        action = decide_delete(code, path)
        report.append(f"{code}\t{path}\t{action}")
        if action == "human":
            raise Stop(3, f"unresolved {code} {path}")
        if action == "keep-ours":
            git(root, "checkout", "--ours", "--", path)
            git(root, "add", "--", path)
        elif action == "accept-delete" or action == "keep-deleted":
            git(root, "rm", "-f", "--", path)
        elif action == "take-theirs":
            git(root, "checkout", "--theirs", "--", path)
            git(root, "add", "--", path)
    stages = unmerged(root)
    for path, path_stages in list(stages.items()):
        if "1" not in path_stages or "2" not in path_stages or "3" not in path_stages:
            raise Stop(3, f"missing one side of {path}")
        kind = merge_kind(path)
        if kind == "regen":
            git(root, "checkout", "--ours", "--", path)
            git(root, "add", "--", path)
            report.append(f"regen\t{path}")
            continue
        if kind == "human":
            raise Stop(3, f"will not text-merge {path}")
        modes = {stage: _stage_mode(root, stage, path) for stage in ("1", "2", "3")}
        if any(mode != "100644" for mode in modes.values()):
            raise Stop(3, f"will not text-merge non-regular file {path}")
        blobs = {stage: _stage_blob(root, stage, path) for stage in ("1", "2", "3")}
        if any(b"\0" in blob for blob in blobs.values()):
            raise Stop(3, f"will not text-merge {path}")
        decoded = {stage: blob.decode("utf-8", "surrogateescape") for stage, blob in blobs.items()}
        if kind == "locale":
            resolved, locale_dropped = merge_locale(decoded["1"], decoded["2"], decoded["3"])
            report.append(f"locale\t{path}\tone-sided edits kept, overlapping keys keep ours")
            for piece in locale_dropped:
                report.append("--- dropped ---")
                report.append(piece)
        elif kind == "go.mod":
            resolved = merge_go_mod(decoded["2"], decoded["3"], pins)
            report.append(f"go.mod\t{path}\tunion requires, upstream versions")
        else:
            resolved, dropped = merge_texts(decoded["1"], decoded["2"], decoded["3"], keep_ours=is_ledger(path))
            side = "kept ours" if is_ledger(path) else "kept upstream"
            report.append(f"merge\t{path}\t{side}\t{len(dropped)} dropped side(s)")
            for piece in dropped:
                report.append("--- dropped ---")
                report.append(piece.rstrip("\n"))
        (root / path).write_text(resolved, encoding="utf-8", errors="surrogateescape")
        git(root, "add", "--", path)


def _show_text(root: Path, spec: str) -> str | None:
    result = git(root, "show", spec, check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def reapply_go_mods(root: Path, pins: dict[str, str], report: list[str], resume: bool = False) -> None:
    """Rebuild every go.mod from its parents before any other conflict can stop the run."""
    names: set[str] = set()
    for rev in ("HEAD", "MERGE_HEAD"):
        listed = git(root, "ls-tree", "-r", "--name-only", rev, check=False)
        if listed.returncode != 0:
            continue
        for path in listed.stdout.splitlines():
            if path == "go.mod" or path.endswith("/go.mod"):
                names.add(path)
    conflicted = set(unmerged(root))
    for path in sorted(names):
        ours = _show_text(root, f"HEAD:{path}")
        theirs = _show_text(root, f"MERGE_HEAD:{path}")
        if ours is None or theirs is None or ours == theirs:
            continue
        try:
            resolved = merge_go_mod(ours, theirs, pins)
        except Stop as error:
            if error.code != 3 or not resume or path in conflicted:
                raise
            marker = f"go.mod-human\t{path}\taccepted staged resolution"
            if marker not in report:
                report.append(marker)
            continue
        target = root / path
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if current != resolved:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(resolved, encoding="utf-8")
            git(root, "add", "--", path)
        marker = f"go.mod\t{path}\tunion requires, upstream versions"
        if marker not in report:
            report.append(marker)


def _renamed_paths(root: Path) -> list[tuple[str, str]]:
    """Return (old, new) pairs from worktree and index renames against HEAD."""
    found: set[tuple[str, str]] = set()
    for args in (
        ("diff", "--name-status", "--find-renames", "HEAD"),
        ("diff", "--cached", "--name-status", "--find-renames", "HEAD"),
    ):
        for line in git(root, *args).stdout.splitlines():
            if not line.startswith("R"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                raise Stop(1, "git rename status is missing paths: " + line)
            found.add((parts[1], parts[2]))
    return sorted(found)


def _changed_paths(root: Path, change_filter: str) -> set[str]:
    paths: set[str] = set()
    for args in (
        ("diff", "--name-only", f"--diff-filter={change_filter}", "HEAD"),
        ("diff", "--cached", "--name-only", f"--diff-filter={change_filter}", "HEAD"),
    ):
        paths.update(git(root, *args).stdout.splitlines())
    return paths


def restore_ledger_deletes(root: Path, report: list[str], resume: bool = False) -> None:
    """Restore plain ledger deletions; stop once for explicit or possible renames."""
    renamed = {old: new for old, new in _renamed_paths(root) if is_ledger(old)}
    deleted = _changed_paths(root, "D") | set(renamed)
    added = sorted(_changed_paths(root, "A"))
    accepted_deletes: set[str] = set()
    for path in sorted(deleted):
        if not is_ledger(path):
            continue
        replacement = renamed.get(path)
        possible = [replacement] if replacement else added
        if possible:
            marker = f"ledger-rename\t{path}\t{'|'.join(possible)}"
            if marker not in report:
                report.append(marker)
                raise Stop(3, f"ledger path may have been renamed: {path} -> {' | '.join(possible)}")
            if not resume:
                raise Stop(3, f"ledger rename marker exists outside resume: {path}")
            accepted_deletes.add(path)
    for path in sorted(deleted - accepted_deletes):
        if not is_ledger(path):
            continue
        git(root, "checkout", "HEAD", "--", path)
        git(root, "add", "--", path)
        report.append(f"delete\t{path}\tkept ours")


def ensure_clean_resolution(root: Path) -> None:
    if unmerged(root):
        raise Stop(3, "unmerged paths remain")
    scanned = git(root, "grep", "-nE", r"^(<<<<<<<|=======|>>>>>>>)( |$)", check=False)
    if scanned.returncode == 0:
        raise Stop(1, "conflict markers remain:\n" + scanned.stdout)
    if scanned.returncode not in {0, 1}:
        raise Stop(1, scanned.stderr.strip() or "git grep failed")
    checked = git(root, "diff", "--cached", "--check", check=False)
    if checked.returncode != 0:
        raise Stop(1, (checked.stdout or checked.stderr).strip() or "cached diff check failed")


def _unstaged_status(root: Path) -> list[str]:
    status = git(root, "status", "--porcelain=v1").stdout.splitlines()
    return [line for line in status if len(line) < 2 or line[1] != " "]


def commit_merge(root: Path) -> None:
    status = _unstaged_status(root)
    if status:
        raise Stop(1, "unstaged changes remain:\n" + "\n".join(status))
    merge_head = git(root, "rev-parse", "MERGE_HEAD").stdout.strip()
    upstream = git(root, "rev-parse", "upstream/main").stdout.strip()
    if merge_head != upstream:
        raise Stop(1, "MERGE_HEAD is not upstream/main")
    ours = git(root, "rev-parse", "HEAD").stdout.strip()
    git(
        root,
        "commit",
        "--no-edit",
        "-m",
        "merge: update from QuantumNous/new-api main\n\nKeep overlapping ledger lines. Overlapping non-ledger lines follow upstream.\n",
    )
    parents = git(root, "rev-list", "--parents", "-n", "1", "HEAD").stdout.split()
    if parents != [git(root, "rev-parse", "HEAD").stdout.strip(), ours, merge_head]:
        raise Stop(1, "merge commit parents are not our branch and upstream/main")


def preflight(root: Path) -> None:
    if git(root, "status", "--porcelain").stdout.strip():
        raise Stop(1, "worktree is dirty")
    if git(root, "symbolic-ref", "-q", "HEAD", check=False).returncode != 0:
        raise Stop(1, "detached HEAD")
    if git(root, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0:
        raise Stop(1, "a merge is already in progress")
    for name in ("rebase-merge", "rebase-apply"):
        path = git(root, "rev-parse", "--git-path", name).stdout.strip()
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = root / candidate
        if candidate.exists():
            raise Stop(1, f"{name} is in progress")
    origin = git(root, "remote", "get-url", "origin").stdout.strip()
    if origin not in ORIGIN_URLS:
        raise Stop(1, f"origin is {origin}")
    upstream = git(root, "remote", "get-url", "upstream", check=False)
    if upstream.returncode != 0:
        git(root, "remote", "add", "upstream", UPSTREAM_FETCH)
    elif upstream.stdout.strip() not in UPSTREAM_URLS:
        raise Stop(1, f"upstream is {upstream.stdout.strip()}")
    git(root, "fetch", "origin", "main")
    git(root, "fetch", "upstream", "main")
    if git(root, "merge-base", "--is-ancestor", "upstream/main", "origin/main", check=False).returncode == 0:
        raise Stop(2, "origin/main already contains upstream/main")
    if git(root, "show-ref", "--verify", "--quiet", "refs/heads/main", check=False).returncode == 0:
        ahead = git(root, "rev-list", "--count", "origin/main..main").stdout.strip()
        if ahead != "0":
            raise Stop(1, "local main has commits that are not on origin/main")
    listed = subprocess.run(
        ["gh", "pr", "list", "--repo", "deeppatternai/dp-router", "--state", "open", "--limit", "200", "--json", "headRefName"],
        text=True,
        capture_output=True,
    )
    if listed.returncode != 0:
        raise Stop(1, (listed.stderr or "gh pr list failed").strip())
    names = [item.get("headRefName", "") for item in json.loads(listed.stdout or "[]")]
    if any(name.startswith("sync/upstream-") for name in names):
        raise Stop(1, "an open sync/upstream pull request already exists")
    previous = git(
        root,
        "log",
        "origin/main",
        "--grep=merge: update from QuantumNous/new-api main",
        "-1",
        "--format=%P",
        check=False,
    ).stdout.strip()
    if previous and len(previous.split()) < 2:
        raise Stop(1, "the last upstream sync on origin/main does not have two parents")


def start_branch(root: Path) -> str:
    short = git(root, "rev-parse", "--short", "upstream/main").stdout.strip()
    date = subprocess.run(["date", "+%Y%m%d"], text=True, capture_output=True, check=True).stdout.strip()
    branch = f"sync/upstream-{date}"
    if _branch_taken(root, branch):
        branch = f"sync/upstream-{date}-{short}"
    if _branch_taken(root, branch):
        raise Stop(1, f"{branch} already exists")
    git(root, "checkout", "-b", branch, "origin/main")
    return branch


def _branch_taken(root: Path, branch: str) -> bool:
    local = git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    if local.returncode == 0:
        return True
    remote = git(root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    return bool(remote.stdout.strip())


def finish(root: Path, skip_build: bool, resume: bool = False) -> str:
    pins = load_pins(Path(__file__).with_name("pins.txt"))
    report = load_report(root, resume)
    try:
        names_before = changed_names(root)
        reapply_go_mods(root, pins, report, resume=resume)
        resolve_worktree(root, pins, report)
        restore_ledger_deletes(root, report, resume=resume)
        names = names_before | changed_names(root)
        if not skip_build:
            regenerate(root, names, pins, report)
        ensure_clean_resolution(root)
        if not skip_build:
            assert_ledger(root)
            run_verification(root)
            if any(name.startswith("web/") for name in names):
                _run_checked(root, ["bun", "install", "--frozen-lockfile"], cwd=root / "web")
                _run_checked(root, ["bun", "run", "build"], cwd=root / "web")
                dirty = _unstaged_status(root)
                if dirty:
                    raise Stop(1, "web build changed files after the lockfile was frozen:\n" + "\n".join(dirty))
        write_report(root, report or ["no conflict hunks"])
        commit_merge(root)
    except Stop:
        if report:
            write_report(root, report)
        raise
    report_path = _report_file(root)
    branch = git(root, "branch", "--show-current").stdout.strip()
    print(f"BRANCH={branch}")
    print(f"REPORT={report_path}")
    return branch


def ledger_only(root: Path) -> str:
    status = git(root, "status", "--porcelain").stdout.splitlines()
    allowed = {
        ".agents/skills/sync-upstream/SKILL.md",
        ".agents/skills/sync-upstream/scripts/sync_upstream.py",
        ".agents/skills/sync-upstream/scripts/test_sync_upstream.py",
        ".agents/skills/sync-upstream/scripts/pins.txt",
    }
    dirty = {line[3:] for line in status if len(line) >= 4}
    if not dirty or not dirty <= allowed:
        raise Stop(1, "ledger-only accepts changes under .agents/skills/sync-upstream only")
    git(root, "fetch", "origin", "main")
    date = subprocess.run(["date", "+%Y%m%d"], text=True, capture_output=True, check=True).stdout.strip()
    branch = f"docs/sync-ledger-{date}"
    if _branch_taken(root, branch):
        raise Stop(1, f"{branch} already exists")
    git(root, "checkout", "-b", branch, "origin/main")
    for path in sorted(dirty):
        git(root, "add", "--", path)
    cached = set(git(root, "diff", "--cached", "--name-only").stdout.splitlines())
    if cached != dirty:
        raise Stop(1, "staged files are not the skill files")
    git(root, "commit", "-m", "docs(skill): record a focus change\n")
    if git(root, "status", "--porcelain").stdout.strip():
        raise Stop(1, "worktree is dirty after the ledger commit")
    print(f"BRANCH={branch}")
    return branch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-only", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    root = args.root or Path(git(Path.cwd(), "rev-parse", "--show-toplevel").stdout.strip())
    try:
        if args.ledger_only:
            ledger_only(root)
            return 0
        merging = git(root, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0
        if merging:
            branch = git(root, "branch", "--show-current").stdout.strip()
            if not branch.startswith("sync/upstream-"):
                raise Stop(1, "merge in progress outside a sync branch")
        else:
            preflight(root)
            start_branch(root)
            merged = git(
                root,
                "-c",
                "rerere.enabled=false",
                "-c",
                "merge.conflictStyle=merge",
                "merge",
                "--no-commit",
                "--no-ff",
                "upstream/main",
                check=False,
            )
            if merged.returncode > 1:
                raise Stop(1, (merged.stderr or merged.stdout).strip())
        finish(root, skip_build=args.skip_build, resume=merging)
    except Stop as exc:
        print(exc, file=sys.stderr)
        return exc.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
