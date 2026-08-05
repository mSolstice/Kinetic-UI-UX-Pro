#!/usr/bin/env python3
"""Adapt a registry component to Kinetic UI UX Pro conformance."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ds_search import BM25, best_value_token, color_tokens, extract_values, load_corpus, slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_DIR = ROOT / "templates" / "adapters"
DEFAULT_REGISTRY_INDEX = ROOT / ".registry" / "components.jsonl"
DEFAULT_DS_INDEX = ROOT / ".ds-index" / "corpus.jsonl"
SOURCE_EXTS = {".tsx", ".jsx", ".ts", ".js", ".css", ".scss"}
SOURCE_KEYS = {"content", "contents", "source", "code", "tsx", "jsx", "css"}
FILE_LIST_KEYS = ("files", "items")


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe_join(root: Path, raw: str) -> Path:
    raw = raw.replace("\\", "/").lstrip("/")
    if not raw or ".." in Path(raw).parts:
        raise ValueError(f"unsafe path in fetched registry item: {raw!r}")
    return root / raw


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            warn(f"skip malformed {path}:{i}: {exc}")
    return rows


def load_adapter(name: str) -> dict:
    candidates = [ADAPTER_DIR / f"{slug(name)}.json"]
    aliases = {
        "shadcn-ui": "shadcn-ui",
        "shadcn": "shadcn-ui",
        "magic-ui": "magic-ui",
        "radix": "radix-ui",
        "tremor-core": "tremor",
    }
    if slug(name) in aliases:
        candidates.append(ADAPTER_DIR / f"{aliases[slug(name)]}.json")
    for path in candidates:
        if path.exists():
            data = read_json(path)
            data["_id"] = path.stem
            return data
    raise SystemExit(f"adapter not found for {name!r} in {ADAPTER_DIR}")


def infer_adapter(record: dict, explicit: str | None) -> dict:
    return load_adapter(explicit or record.get("library", ""))


def find_component(component: str, registry_index: Path) -> dict:
    if re.match(r"https?://|file://", component):
        return {
            "id": slug(component.rsplit("/", 1)[-1]),
            "library": "",
            "name": slug(component),
            "registry_url": component,
            "license": "",
        }
    rows = load_jsonl(registry_index)
    for row in rows:
        if row.get("id") == component:
            return row
    for row in rows:
        if slug(row.get("name", "")) == slug(component):
            return row
    raise SystemExit(f"component {component!r} not found in {registry_index}")


def fetch_text(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in {"", "file"}:
        path = Path(urllib.request.url2pathname(parsed.path)) if parsed.scheme == "file" else Path(url)
        return path.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": "Kinetic-UI-UX-Pro component adapter"})
    with urllib.request.urlopen(req, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def source_from_item(item: dict) -> tuple[str, str] | None:
    path = item.get("path") or item.get("name") or item.get("target")
    content = None
    for key in SOURCE_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            content = value
            if not path:
                path = f"component.{key if key in {'tsx', 'jsx', 'css'} else 'tsx'}"
            break
    if content is None:
        return None
    if not Path(str(path)).suffix:
        path = f"{path}.tsx"
    return str(path), content


def extract_source_files(payload: str, url: str, temp_dir: Path) -> list[Path]:
    files = []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        suffix = Path(urllib.parse.urlparse(url).path).suffix or ".tsx"
        target = temp_dir / f"component{suffix}"
        target.write_text(payload, encoding="utf-8")
        return [target]

    queue = []
    if isinstance(data, dict):
        for key in FILE_LIST_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                queue.extend(value)
        if not queue:
            queue.append(data)
    elif isinstance(data, list):
        queue.extend(data)

    for item in queue:
        if not isinstance(item, dict):
            continue
        source = source_from_item(item)
        if not source:
            continue
        rel, content = source
        try:
            target = safe_join(temp_dir, rel)
        except ValueError as exc:
            warn(str(exc))
            continue
        if target.suffix not in SOURCE_EXTS:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        files.append(target)
    if not files:
        raise SystemExit("fetched registry item did not contain component source files")
    return files


def token_var(doc: dict) -> str:
    name = str(doc.get("name", "")).strip()
    name = name[2:] if name.startswith("--") else name
    return f"var(--{name})"


def rewrite_tokens(files: list[Path], ds_index: Path) -> tuple[list[dict], list[dict]]:
    corpus = load_corpus(ds_index)
    bm25, c_tokens = BM25(corpus), color_tokens(corpus)
    remapped, unmatched = [], []
    for path in files:
        if path.suffix not in SOURCE_EXTS:
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        items = extract_values(path)
        for item in sorted(items, key=lambda x: x["line"], reverse=True):
            verdict, doc, score, note = best_value_token(item, corpus, bm25, c_tokens)
            if verdict not in {"EXACT", "NEAR"} or not doc:
                unmatched.append({**item, "verdict": verdict, "note": note})
                continue
            idx = item["line"] - 1
            replacement = token_var(doc)
            old = lines[idx]
            if item["value"] not in old:
                unmatched.append({**item, "verdict": "UNMATCHED", "note": "line changed before rewrite"})
                continue
            lines[idx] = old.replace(item["value"], replacement, 1)
            remapped.append({
                "file": str(path),
                "line": item["line"],
                "value": item["value"],
                "token": replacement,
                "verdict": verdict,
                "note": note,
            })
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return remapped, unmatched


def first_source_dir(files: list[Path], temp_dir: Path) -> Path:
    parents = [p.parent for p in files]
    return parents[0] if parents else temp_dir


def patch_function_name(gap: str) -> str:
    return "KineticPatch" + "".join(part.title() for part in re.split(r"[^A-Za-z0-9]+", gap) if part)


def render_tsx_patch_function(gap: str, code: str) -> str:
    name = patch_function_name(gap)
    lines = [line.rstrip() for line in code.strip().splitlines() if line.strip()]
    prelude = [
        f"export function {name}(props: Record<string, any>) {{",
        "  const {",
        "    state = { status: 'idle' }, status = state.status, disabled = false, children = null,",
        "    label = '', loadingLabel = 'Loading', successLabel = 'Complete', successMessage = 'Complete',",
        "    errorId = 'kinetic-error', errorMessage = 'Something went wrong.', emptyMessage = 'No results.',",
        "    items = [], data = [], message = '', tableLabel = 'Table', summary = 'Chart',",
        "    Button = 'button', Card = 'section', Input = 'input', Table = 'table', BarChart = 'div', BaseRoot = 'div',",
        "    formatValue = (value: unknown) => String(value),",
        "  } = props;",
    ]
    if not lines:
        body = ["  return null;"]
    elif lines[0].startswith("if "):
        body = ["  " + line for line in lines] + ["  return null;"]
    else:
        expr_at = next((i for i, line in enumerate(lines) if line.startswith("<") or line.startswith("{")), None)
        if expr_at is None:
            body = ["  " + line for line in lines] + ["  return null;"]
        else:
            setup = ["  " + line for line in lines[:expr_at]]
            expr = lines[expr_at:]
            if expr[0].startswith("{"):
                body = setup + ["  return (", "    <>", *["      " + line for line in expr], "    </>", "  );"]
            else:
                body = setup + ["  return (", *["    " + line for line in expr], "  );"]
    return "\n".join(prelude + body + ["}"])


def inject_conformance(files: list[Path], adapter: dict) -> list[dict]:
    patched = []
    target_dir = first_source_dir(files, files[0].parent if files else Path.cwd())
    module_path = target_dir / "kinetic-conformance-patches.tsx"
    css_path = target_dir / "kinetic-conformance-patches.css"
    html_path = target_dir / "kinetic-conformance-patches.html"
    gaps = adapter.get("stateGaps", [])
    patches = adapter.get("conformancePatch", {})
    parts = [
        "import * as React from 'react';",
        "",
        "type KineticStatus = 'idle' | 'loading' | 'success' | 'error' | 'empty';",
        "type KineticPatchProps = {",
        "  status?: KineticStatus;",
        "  message?: string;",
        "  children?: React.ReactNode;",
        "};",
        "",
        "export function KineticConformancePatch({ status = 'idle', message = '', children }: KineticPatchProps) {",
        "  const busy = status === 'loading';",
        "  return (",
        "    <div data-kinetic-conformance=\"true\" aria-busy={busy || undefined}>",
        "      <div aria-live=\"polite\" className=\"sr-only\">",
        "        {status === 'loading' ? 'Loading' : status === 'success' ? message || 'Complete' : ''}",
        "      </div>",
        "      {status === 'error' ? <p role=\"alert\">{message || 'Something went wrong.'}</p> : null}",
        "      {status === 'empty' ? <div role=\"status\">{message || 'No results.'}</div> : null}",
        "      {children}",
        "    </div>",
        "  );",
        "}",
        "",
        "export function useKineticReducedMotion() {",
        "  const [reduce, setReduce] = React.useState(false);",
        "  React.useEffect(() => {",
        "    const media = window.matchMedia('(prefers-reduced-motion: reduce)');",
        "    setReduce(media.matches);",
        "    const onChange = () => setReduce(media.matches);",
        "    media.addEventListener('change', onChange);",
        "    return () => media.removeEventListener('change', onChange);",
        "  }, []);",
        "  return reduce;",
        "}",
        "",
    ]
    css_parts = [
        ".sr-only { position: absolute; width: 1px; height: 1px; padding: 0; "
        "margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }",
        "@media (prefers-reduced-motion: reduce) { [data-kinetic-conformance='true'] * { "
        "animation-duration: var(--duration-reduced-motion) !important; transition-duration: var(--duration-reduced-motion) !important; } }",
    ]
    html_parts = []
    for gap in gaps:
        patch = patches.get(gap)
        if not patch:
            continue
        language = patch.get("language", "")
        code = patch.get("code", "").rstrip()
        if language == "css":
            css_parts += [f"\n/* {adapter.get('library')} {gap} patch */", code]
            patched.append({"state": gap, "language": language, "file": str(css_path)})
        elif language == "html":
            html_parts += [f"<!-- {adapter.get('library')} {gap} patch -->", code]
            patched.append({"state": gap, "language": language, "file": str(html_path)})
        else:
            parts += [render_tsx_patch_function(gap, code), ""]
            patched.append({"state": gap, "language": language, "file": str(module_path)})
    module_path.write_text("\n".join(parts), encoding="utf-8")
    files.append(module_path)
    css_path.write_text("\n".join(css_parts) + "\n", encoding="utf-8")
    files.append(css_path)
    if html_parts:
        html_path.write_text("\n".join(html_parts) + "\n", encoding="utf-8")
        files.append(html_path)
    patched.append({"state": "reduced-motion", "language": "css", "file": str(css_path)})
    return patched


def run_audit(target: Path) -> list[dict]:
    cmd = [sys.executable, str(ROOT / "scripts" / "ast_audit.py"), str(target), "--format", "json"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if proc.returncode not in (0, 1):
        warn(f"ast_audit failed: {proc.stderr.strip() or proc.stdout.strip()}")
    try:
        data = json.loads(proc.stdout or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        warn("ast_audit did not return JSON")
        return []


def automated_fix_pass(files: list[Path]) -> list[str]:
    fixes = []
    for path in files:
        if path.suffix not in {".tsx", ".jsx", ".ts", ".js"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        new = text.replace("localStorage", "kineticMemoryStorage").replace("sessionStorage", "kineticMemoryStorage")
        if new != text and "const kineticMemoryStorage" not in new:
            new = (
                "const kineticMemoryStorage = new Map<string, string>();\n"
                "const kineticMemoryStorageApi = { getItem: kineticMemoryStorage.get.bind(kineticMemoryStorage), "
                "setItem: kineticMemoryStorage.set.bind(kineticMemoryStorage) };\n"
            ) + new.replace("kineticMemoryStorage.", "kineticMemoryStorageApi.")
            fixes.append(f"{path}: replaced browser storage with memory storage shim")
        if new != text:
            path.write_text(new, encoding="utf-8")
    return fixes


def copy_output(temp_dir: Path, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(temp_dir, out_dir)


def diff_summary(before: dict[Path, str], files: list[Path]) -> list[str]:
    out = []
    for path in files:
        old = before.get(path, "")
        new = path.read_text(encoding="utf-8", errors="replace")
        if old == new:
            continue
        diff = list(difflib.unified_diff(
            old.splitlines(), new.splitlines(),
            fromfile=f"fetched/{path.name}", tofile=f"adapted/{path.name}", lineterm=""))
        out.append(f"{path.name}: {sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))} additions, "
                   f"{sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))} removals")
    return out


def print_report(out_dir: Path, remapped, unmatched, patched, before_findings, after_findings, fixes, diffs) -> None:
    before_errors = [f for f in before_findings if f.get("severity") == "ERROR"]
    after_errors = [f for f in after_findings if f.get("severity") == "ERROR"]
    resolved = max(0, len(before_errors) - len(after_errors))
    print("# Component Adaptation Summary\n")
    print(f"Output: {out_dir}")
    print(f"Tokens remapped: {len(remapped)}")
    for item in remapped[:20]:
        print(f"- {Path(item['file']).name}:{item['line']} {item['value']} -> {item['token']} ({item['verdict']})")
    if len(remapped) > 20:
        print(f"- ... {len(remapped) - 20} more")
    print(f"\nUnmatched design values: {len(unmatched)}")
    for item in unmatched[:20]:
        print(f"- {Path(item['file']).name}:{item['line']} {item['value']} ({item['note']})")
    print(f"\nStates patched: {len(patched)}")
    for item in patched:
        print(f"- {item['state']} via {Path(item['file']).name}")
    print(f"\nFindings resolved: {resolved}")
    if fixes:
        print("Automated fix pass:")
        for fix in fixes:
            print(f"- {fix}")
    print(f"Findings remaining: {len(after_findings)} total, {len(after_errors)} ERROR")
    for finding in after_errors[:20]:
        print(f"- ERROR {finding.get('rule')} {finding.get('file')}:{finding.get('line')} {finding.get('message')}")
    if after_errors:
        print("\nERROR remains: adapted output was written, but it must not ship until these are fixed.")
    print("\nDiff summary:")
    for line in diffs or ["no source changes beyond copied files"]:
        print(f"- {line}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("component", help="component id from .registry/components.jsonl, registry URL, or local file URL")
    ap.add_argument("--adapter", help="adapter id override, e.g. shadcn-ui")
    ap.add_argument("--registry-index", default=str(DEFAULT_REGISTRY_INDEX))
    ap.add_argument("--ds-index", default=str(DEFAULT_DS_INDEX))
    ap.add_argument("--out", help="output directory; defaults to out/adapted/<component>")
    ap.add_argument("--redistribute", action="store_true", help="abort when adapter is not vendorable")
    args = ap.parse_args()

    record = find_component(args.component, Path(args.registry_index))
    adapter = infer_adapter(record, args.adapter)
    if args.redistribute and not adapter.get("vendorable", False):
        raise SystemExit(f"abort: {adapter['library']} adapter is not vendorable for redistribution")
    url = record.get("registry_url")
    if not url:
        raise SystemExit("component record has no registry_url to fetch source from")
    ds_index = Path(args.ds_index)
    if not ds_index.exists():
        raise SystemExit(f"design-system index not found: {ds_index}. Run scripts/ds_index.py first.")

    out_dir = Path(args.out) if args.out else ROOT / "out" / "adapted" / slug(record.get("id", args.component))
    with tempfile.TemporaryDirectory(prefix="kinetic-component-") as tmp:
        temp_dir = Path(tmp)
        payload = fetch_text(url)
        files = extract_source_files(payload, url, temp_dir)
        before = {path: path.read_text(encoding="utf-8", errors="replace") for path in files}
        before_findings = run_audit(temp_dir)
        remapped, unmatched = rewrite_tokens(files, ds_index)
        patched = inject_conformance(files, adapter)
        after_findings = run_audit(temp_dir)
        fixes = []
        if any(f.get("severity") == "ERROR" for f in after_findings):
            fixes = automated_fix_pass(files)
            after_findings = run_audit(temp_dir)
        diffs = diff_summary(before, files)
        copy_output(temp_dir, out_dir)
    print_report(out_dir, remapped, unmatched, patched, before_findings, after_findings, fixes, diffs)
    return 1 if any(f.get("severity") == "ERROR" for f in after_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
