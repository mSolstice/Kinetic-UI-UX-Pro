#!/usr/bin/env python3
"""
Write or emit safe file-creation commands from a JSON manifest.

Manifest forms:
  [{"path": "src/App.tsx", "content": "..."}]
  {"files": [{"path": "src/App.tsx", "content": "..."}]}

Paths must be relative and must not contain '..'.
"""

import argparse
import json
import shlex
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath


def fail(message):
    print(f"emit_files: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_manifest(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"could not read manifest: {e}")
    files = data.get("files") if isinstance(data, dict) else data
    if not isinstance(files, list):
        fail("manifest must be a list or an object with a 'files' list")
    out = []
    for i, item in enumerate(files, 1):
        if not isinstance(item, dict):
            fail(f"entry {i} must be an object")
        if "path" not in item or "content" not in item:
            fail(f"entry {i} must contain path and content")
        if not isinstance(item["path"], str) or not isinstance(item["content"], str):
            fail(f"entry {i} path and content must be strings")
        out.append({"path": item["path"], "content": item["content"]})
    return out


def safe_path(raw):
    if not raw or "\x00" in raw:
        fail(f"invalid path: {raw!r}")
    posix = PurePosixPath(raw.replace("\\", "/"))
    windows = PureWindowsPath(raw)
    if posix.is_absolute() or windows.is_absolute():
        fail(f"absolute paths are not allowed: {raw}")
    if any(part == ".." for part in posix.parts) or any(part == ".." for part in windows.parts):
        fail(f"path traversal is not allowed: {raw}")
    if any(part in ("", ".") for part in posix.parts):
        fail(f"path must not contain empty or current-directory segments: {raw}")
    return Path(*posix.parts)


def normalized_entries(files):
    out, seen = [], set()
    for item in files:
        path = safe_path(item["path"])
        key = path.as_posix()
        if key in seen:
            fail(f"duplicate path in manifest: {key}")
        seen.add(key)
        out.append((path, item["content"]))
    return out


def check_no_overwrite(entries, root):
    conflicts = [path for path, _content in entries if (root / path).exists()]
    if conflicts:
        for path in conflicts:
            print(f"would overwrite existing file: {path.as_posix()}", file=sys.stderr)
        raise SystemExit(1)


def bash_heredoc(path, content):
    quoted = shlex.quote(path.as_posix())
    parent = shlex.quote(path.parent.as_posix())
    marker = "__KINETIC_FILE__"
    while marker in content:
        marker += "_END"
    lines = []
    if path.parent.as_posix() != ".":
        lines.append(f"mkdir -p {parent}")
    lines.append(f"cat > {quoted} <<'{marker}'")
    lines.append(content)
    lines.append(marker)
    return "\n".join(lines)


def powershell_literal(value):
    return value.replace("'", "''")


def powershell_block(path, content):
    win_path = path.as_posix().replace("/", "\\")
    parent = path.parent.as_posix().replace("/", "\\")
    lines = []
    if path.parent.as_posix() != ".":
        lines.append(f"New-Item -ItemType Directory -Force '{powershell_literal(parent)}' | Out-Null")
    lines.append("@'")
    lines.append(content)
    lines.append(f"'@ | Set-Content -LiteralPath '{powershell_literal(win_path)}' -NoNewline")
    return "\n".join(lines)


def emit_shell(entries, shell):
    blocks = []
    for path, content in entries:
        if shell == "bash":
            blocks.append(bash_heredoc(path, content))
        else:
            blocks.append(powershell_block(path, content))
    print("\n\n".join(blocks))


def write_files(entries, root, dry_run):
    for path, content in entries:
        target = root / path
        if dry_run:
            print(f"would write {path.as_posix()} ({len(content.encode('utf-8'))} bytes)")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"wrote {path.as_posix()}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", help="JSON manifest path")
    ap.add_argument("--dry-run", action="store_true", help="show what would be written")
    ap.add_argument("--shell", choices=["bash", "powershell"],
                    help="print file-creation commands instead of writing")
    ap.add_argument("--check", action="store_true",
                    help="fail if any manifest path already exists")
    args = ap.parse_args()

    entries = normalized_entries(load_manifest(args.manifest))
    root = Path.cwd()
    if args.check:
        check_no_overwrite(entries, root)
        if not args.shell:
            print("no overwrite conflicts")
            return
    if args.shell:
        emit_shell(entries, args.shell)
        return
    write_files(entries, root, args.dry_run)


if __name__ == "__main__":
    main()
