"""Static LookML sanity checks that run in CI without a Looker instance.

Checks: balanced braces, `;;` terminated sql blocks, every explore view/join resolves to a view file,
every `${view.field}` reference points at an existing view, and dashboard YAML parses (if PyYAML present).
This is NOT a replacement for Looker's validator; it catches the typos that break deploys.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def strip_comments(s: str) -> str:
    return re.sub(r"(?m)^\s*#.*$", "", s)  # full-line comments only ("#" appears inside format strings)


def check_braces(path: Path, text: str, errors: list[str]) -> None:
    depth, in_sql = 0, False
    for i, line in enumerate(strip_comments(text).splitlines(), 1):
        depth += line.count("{") - line.count("}")
        if depth < 0:
            errors.append(f"{path.name}:{i} unbalanced '}}'")
            return
    if depth != 0:
        errors.append(f"{path.name}: unbalanced braces (depth {depth})")


def main() -> int:
    errors: list[str] = []
    lkml = [p for p in ROOT.rglob("*.lkml")]
    views: dict[str, str] = {}
    for p in (ROOT / "views").glob("*.view.lkml"):
        t = strip_comments(p.read_text())
        check_braces(p, t, errors)
        m = re.findall(r"(?m)^view:\s*(\w+)", t)
        if len(m) != 1:
            errors.append(f"{p.name}: expected exactly one view, found {m}")
        for v in m:
            views[v] = t
    for p in lkml:
        t = strip_comments(p.read_text())
        check_braces(p, t, errors)
        if len(re.findall(r"\bsql\w*:", t)) and ";;" not in t and p.name != "manifest.lkml":
            errors.append(f"{p.name}: sql block without ';;'")

    # explore references
    explore_aliases: dict[str, set[str]] = {}
    for p in (ROOT / "explores").glob("*.explore.lkml"):
        t = strip_comments(p.read_text())
        for ex in re.finditer(r"(?m)^explore:\s*(\w+)\s*\{(.*?)(?=^explore:|\Z)", t, flags=re.S):
            body = ex.group(2)
            base = re.search(r"\bfrom:\s*(\w+)", body)
            names = {re.search(r"view_name:\s*(\w+)", body).group(1)} if re.search(r"view_name:", body) else {ex.group(1)}
            src = {(base.group(1) if base else ex.group(1))}
            for j in re.finditer(r"join:\s*(\w+)\s*\{(.*?)\n  \}", body, flags=re.S):
                names.add(j.group(1))
                f = re.search(r"\bfrom:\s*(\w+)", j.group(2))
                src.add(f.group(1) if f else j.group(1))
            explore_aliases[ex.group(1)] = names
            for s in src:
                if s not in views:
                    errors.append(f"{p.name}: explore '{ex.group(1)}' references unknown view '{s}'")

    # ${view.field} references inside views must target a known view or alias
    all_names = set(views) | {a for s in explore_aliases.values() for a in s}
    for name, t in views.items():
        for ref in re.findall(r"\$\{(\w+)\.\w+\}", t):
            if ref != "TABLE" and ref not in all_names:
                errors.append(f"views/{name}: reference to unknown view '{ref}'")

    # dashboards
    try:
        import yaml  # type: ignore
        for p in (ROOT / "dashboards").glob("*.dashboard.lookml"):
            data = yaml.safe_load(p.read_text())
            for dash in data:
                for el in dash.get("elements", []):
                    for key in ("name", "model", "explore", "type"):
                        if key not in el:
                            errors.append(f"{p.name}: element {el.get('name')} missing '{key}'")
    except ImportError:
        print("note: PyYAML not installed; skipping dashboard YAML parse")

    for e in errors:
        print("ERROR", e)
    print(f"checked {len(lkml)} .lkml files, {len(views)} views, {len(explore_aliases)} explores: "
          f"{'FAILED' if errors else 'OK'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
