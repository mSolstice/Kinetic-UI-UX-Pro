#!/usr/bin/env python3
"""
Conservative license gate for vendorable code.

The checker only marks a package allowed when it reads an explicit license from
a file. Unknown, missing, or ambiguous licenses are reported as UNVERIFIED.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ALLOWLIST = {
    "MIT",
    "Apache-2.0",
    "ISC",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CC0-1.0",
}

PACKAGE_SECTIONS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)

SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".ds-index",
    "__pycache__",
    "dist",
    "build",
    "out",
}

VENDORED_DIR_NAMES = {
    "vendor",
    "vendored",
    "third_party",
    "third-party",
    "external",
}

SOURCE_EXTS = {
    ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".html", ".md",
    ".py", ".json", ".yml", ".yaml",
}

LICENSE_TOKEN_RE = re.compile(
    r"\b(?:MIT|Apache-2\.0|ISC|BSD-2-Clause|BSD-3-Clause|CC0-1\.0|"
    r"GPL-[\w.+-]+|LGPL-[\w.+-]+|AGPL-[\w.+-]+|MPL-[\w.+-]+|"
    r"BUSL-[\w.+-]+|CC-BY-[\w.+-]+|UNLICENSED|SEE LICENSE IN [A-Za-z0-9_.-]+)\b"
)
NOTICE_LINE_RE = re.compile(
    r"(?i)(SPDX-License-Identifier:\s*[^\n\r*]+|"
    r"copyright\s+(?:\(c\)\s*)?[^.\n\r]{0,160}|"
    r"(?:copied|adapted|derived)\s+from\s+https?://[^\s)]+|"
    r"based\s+on\s+code\s+from\s+https?://[^\s)]+|"
    r"source:\s+https?://[^\s)]+)"
)
HEADER_PREFIX_RE = re.compile(r"^\s*(?:#|//|/\*|\*|<!--|-->|;|REM\b|::)?\s*", re.I)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"skip invalid json {path}: {e}", file=sys.stderr)
        return None


def rel(path):
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def package_json_paths(root):
    for path in root.rglob("package.json"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def dependency_names(pkg):
    names = set()
    for section in PACKAGE_SECTIONS:
        deps = pkg.get(section, {})
        if isinstance(deps, dict):
            names.update(deps.keys())
    return sorted(names)


def package_dir(root, package):
    node_modules = root / "node_modules"
    parts = package.split("/")
    return node_modules.joinpath(*parts)


def read_dependency_license(root, package):
    pkg_path = package_dir(root, package) / "package.json"
    if not pkg_path.exists():
        return "", "UNVERIFIED", f"{rel(pkg_path)} missing"
    pkg = read_json(pkg_path)
    if not pkg:
        return "", "UNVERIFIED", rel(pkg_path)
    value = pkg.get("license")
    if isinstance(value, dict):
        value = value.get("type")
    if isinstance(value, list):
        value = " OR ".join(
            item.get("type", "") if isinstance(item, dict) else str(item)
            for item in value
        )
    if not isinstance(value, str) or not value.strip():
        return "", "UNVERIFIED", f"{rel(pkg_path)} license field missing"
    return value.strip(), license_verdict(value.strip()), rel(pkg_path)


def license_verdict(license_text):
    if not license_text:
        return "UNVERIFIED"
    upper = license_text.upper()
    if upper.startswith("SEE LICENSE") or upper == "UNLICENSED":
        return "UNVERIFIED" if upper.startswith("SEE LICENSE") else "BLOCKED"
    tokens = LICENSE_TOKEN_RE.findall(license_text)
    if not tokens:
        return "UNVERIFIED"
    normalized = [token.strip() for token in tokens]
    if all(token in ALLOWLIST for token in normalized):
        return "ALLOWED"
    return "BLOCKED"


def add_row(rows, package, license_text, verdict, source):
    rows.append({
        "package": package,
        "license": license_text or "UNVERIFIED",
        "verdict": verdict,
        "source": source,
    })


def scan_dependencies(root):
    rows = []
    for pkg_path in package_json_paths(root):
        pkg = read_json(pkg_path)
        if not pkg:
            continue
        for name in dependency_names(pkg):
            license_text, verdict, source = read_dependency_license(pkg_path.parent, name)
            add_row(rows, name, license_text, verdict, source)
    return rows


def vendored_dirs(root):
    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in VENDORED_DIR_NAMES:
            yield path


def license_from_text_file(path):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    m = re.search(r"SPDX-License-Identifier:\s*([A-Za-z0-9().+\- OR AND]+)", text)
    if m:
        return m.group(1).strip()
    first = text[:4000]
    if "MIT License" in first:
        return "MIT"
    if "Apache License" in first and "Version 2.0" in first:
        return "Apache-2.0"
    if "ISC License" in first:
        return "ISC"
    if "Creative Commons Zero" in first or "CC0 1.0" in first:
        return "CC0-1.0"
    return ""


def scan_vendored(root):
    rows = []
    for directory in vendored_dirs(root):
        license_files = [
            p for p in directory.rglob("*")
            if p.is_file() and p.name.lower() in {"license", "license.md", "license.txt", "copying"}
        ]
        if not license_files:
            add_row(rows, f"vendored:{rel(directory)}", "", "UNVERIFIED",
                    f"{rel(directory)} has no license file")
            continue
        for path in license_files:
            license_text = license_from_text_file(path)
            add_row(rows, f"vendored:{rel(path.parent)}", license_text,
                    license_verdict(license_text), rel(path))
    return rows


def is_probably_text(path):
    if path.suffix not in SOURCE_EXTS:
        return False
    try:
        chunk = path.read_bytes()[:2048]
    except Exception:
        return False
    return b"\0" not in chunk


def scan_notices(root):
    rows = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if not is_probably_text(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:80]
        except Exception:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            header_like = (
                stripped.startswith(("#", "//", "/*", "*", "<!--", ";"))
                or lower.startswith(("copyright", "spdx-license-identifier"))
            )
            if not header_like:
                continue
            candidate = HEADER_PREFIX_RE.sub("", stripped)
            match = NOTICE_LINE_RE.search(candidate)
            if not match:
                continue
            notice = " ".join(match.group(1).split())
            add_row(rows, f"notice:{rel(path)}", notice, "UNVERIFIED", rel(path))
            break
    return rows


def print_table(rows):
    headers = ("package", "declared license", "allowlist verdict", "source")
    widths = [len(h) for h in headers]
    data = [
        (row["package"], row["license"], row["verdict"], row["source"])
        for row in rows
    ]
    for row in data:
        for i, cell in enumerate(row):
            widths[i] = min(max(widths[i], len(cell)), 72)
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for row in data:
        cells = [cell if len(cell) <= widths[i] else cell[:widths[i] - 1] + "…" for i, cell in enumerate(row)]
        print(fmt.format(*cells))


def explain(target, rows):
    matches = [row for row in rows if row["package"] == target]
    if not matches:
        if target in ALLOWLIST:
            print(f"{target}: this SPDX identifier is in the allowlist, but no package license was read from a file for this scan.")
        else:
            verdict = license_verdict(target)
            if verdict == "BLOCKED":
                print(f"{target}: this license expression contains at least one identifier outside the allowlist, but no package row was read from a file.")
            else:
                print(f"{target}: UNVERIFIED because no package row or recognized SPDX license was read from a file.")
        return 1
    code = 0
    for row in matches:
        if row["verdict"] == "ALLOWED":
            print(f"{row['package']}: ALLOWED. Read {row['license']} from {row['source']}; all detected SPDX identifiers are allowlisted.")
        elif row["verdict"] == "BLOCKED":
            code = 1
            print(f"{row['package']}: BLOCKED. Read {row['license']} from {row['source']}; at least one identifier is outside {', '.join(sorted(ALLOWLIST))}.")
        else:
            code = 1
            print(f"{row['package']}: UNVERIFIED. Could not read an explicit allowlisted license from {row['source']}.")
    return code


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repository root to scan")
    ap.add_argument("--explain", help="package name or SPDX identifier to explain")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    rows = scan_dependencies(root) + scan_vendored(root) + scan_notices(root)
    rows.sort(key=lambda row: (row["verdict"], row["package"]))

    if args.explain:
        return explain(args.explain, rows)

    if rows:
        print_table(rows)
    else:
        print("package  declared license  allowlist verdict  source")
        print("-------  ----------------  -----------------  ------")
        print("(none)   n/a               PASS              no package.json dependencies, vendored directories, or notices found")
    return 1 if any(row["verdict"] != "ALLOWED" for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
