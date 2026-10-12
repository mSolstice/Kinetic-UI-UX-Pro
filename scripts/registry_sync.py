#!/usr/bin/env python3
"""
Metadata-only component registry sync.

This script indexes component catalog metadata so Kinetic UI UX Pro can search
open registries without storing component source. Cached data is sanitized
records only; raw registry payloads are never persisted.
"""

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_DIR = ROOT / ".registry"
DEFAULT_ADAPTER_FILE = ROOT / "references" / "kinetic-ui-ux-pro.md"
COMPONENTS_FILE = "components.jsonl"
STALE_DAYS = 30

SOURCE_FIELD_NAMES = {
    "code", "content", "contents", "source", "source_code", "raw",
    "files", "file", "chunks", "template", "css", "tsx", "jsx",
}

ADAPTER_FALLBACKS = {
    "shadcn-ui": {"name": "shadcn/ui", "license": "MIT", "vendorable": True, "referenceable": True},
    "magic-ui": {"name": "Magic UI", "license": "MIT", "vendorable": True, "referenceable": True},
    "heroui": {"name": "HeroUI", "license": "MIT", "vendorable": True, "referenceable": True},
    "aceternity-free": {
        "name": "Aceternity free tier",
        "license": "URL-only",
        "vendorable": False,
        "referenceable": True,
    },
    "flowbite-core": {"name": "Flowbite core", "license": "MIT", "vendorable": True, "referenceable": True},
    "hyperui": {"name": "HyperUI", "license": "MIT", "vendorable": True, "referenceable": True},
    "daisyui": {"name": "DaisyUI", "license": "MIT", "vendorable": True, "referenceable": True},
    "tremor-core": {"name": "Tremor core", "license": "Apache-2.0", "vendorable": True, "referenceable": True},
    "radix-ui": {"name": "Radix UI", "license": "MIT", "vendorable": True, "referenceable": True},
    "base-ui": {"name": "Base UI", "license": "MIT", "vendorable": True, "referenceable": True},
    "react-aria": {"name": "React Aria", "license": "Apache-2.0", "vendorable": True, "referenceable": True},
    "ark-ui": {"name": "Ark UI", "license": "MIT", "vendorable": True, "referenceable": True},
    "reka-ui": {"name": "Reka UI", "license": "MIT", "vendorable": True, "referenceable": True},
    "aceternity-pro": {
        "name": "Aceternity Pro",
        "license": "PROHIBITED",
        "vendorable": False,
        "referenceable": False,
    },
    "flowbite-pro": {
        "name": "Flowbite Pro",
        "license": "PROHIBITED",
        "vendorable": False,
        "referenceable": False,
    },
    "tailwind-plus": {
        "name": "Tailwind Plus",
        "license": "PROHIBITED",
        "vendorable": False,
        "referenceable": False,
    },
}

DEFAULT_SOURCES = {
    "shadcn-ui": {
        "type": "registry",
        "url": "https://ui.shadcn.com/r/styles/default/registry.json",
        "framework": "react",
        "tags": ["tailwind", "radix", "registry"],
    },
    "magic-ui": {
        "type": "registry",
        "url": "https://magicui.design/r/registry.json",
        "framework": "react",
        "tags": ["tailwind", "motion", "registry"],
    },
    "heroui": {
        "type": "sitemap",
        "url": "https://www.heroui.com/sitemap.xml",
        "framework": "react",
        "tags": ["components", "sitemap"],
        "path_filter": "/docs/components/",
    },
    "aceternity-free": {
        "type": "sitemap",
        "url": "https://ui.aceternity.com/sitemap.xml",
        "framework": "react",
        "tags": ["components", "sitemap", "url-only"],
        "path_filter": "/components/",
    },
    "hyperui": {
        "type": "sitemap",
        "url": "https://www.hyperui.dev/sitemap.xml",
        "framework": "html",
        "tags": ["tailwind", "sitemap"],
        "path_filter": "/components/",
    },
    "flowbite-core": {
        "type": "sitemap",
        "url": "https://flowbite.com/sitemap.xml",
        "framework": "html",
        "tags": ["tailwind", "sitemap"],
        "path_filter": "/docs/components/",
    },
    "daisyui": {
        "type": "sitemap",
        "url": "https://daisyui.com/sitemap.xml",
        "framework": "html",
        "tags": ["tailwind", "sitemap"],
        "path_filter": "/components/",
    },
    "base-ui": {
        "type": "sitemap",
        "url": "https://base-ui.com/sitemap.xml",
        "framework": "react",
        "tags": ["unstyled", "sitemap"],
        "path_filter": "/react/components/",
    },
    "react-aria": {
        "type": "sitemap",
        "url": "https://react-spectrum.adobe.com/sitemap.xml",
        "framework": "react",
        "tags": ["hooks", "sitemap"],
        "path_filter": "/react-aria/",
    },
    "ark-ui": {
        "type": "sitemap",
        "url": "https://ark-ui.com/sitemap.xml",
        "framework": "multi",
        "tags": ["unstyled", "sitemap"],
        "path_filter": "/docs/components/",
    },
    "reka-ui": {
        "type": "sitemap",
        "url": "https://reka-ui.com/sitemap.xml",
        "framework": "vue",
        "tags": ["unstyled", "sitemap"],
        "path_filter": "/docs/components/",
    },
    "tremor-core": {
        "type": "sitemap",
        "url": "https://www.tremor.so/sitemap.xml",
        "framework": "react",
        "tags": ["dashboard", "charts", "sitemap"],
        "path_filter": "/docs/",
    },
}


def warn(message):
    print(f"warning: {message}", file=sys.stderr)


def slug(value):
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", str(value))
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "unknown"


def canonical_id(value):
    return slug(value.replace("/", "-"))


def today_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def parse_adapter_table(path):
    adapters = dict(ADAPTER_FALLBACKS)
    if not path.exists():
        warn(f"adapter file not found: {path}")
        return adapters
    section = ""
    current = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## "):
            section = line.strip().lower()
            heading = line.strip("# ").strip()
            if heading and heading.lower() not in {
                "agent routing & enforcement protocol",
                "approved library architecture",
                "deliberately excluded",
                "free but not mit",
            }:
                current = {
                    "key": canonical_id(heading),
                    "name": heading,
                    "license": "",
                    "vendorable": True,
                    "referenceable": True,
                }
            else:
                current = None
            continue
        if current and "**License Compliance:**" in line:
            license_match = re.search(r"SPDX:\s*([A-Za-z0-9.+-]+)", line)
            if license_match:
                current["license"] = license_match.group(1)
            elif "url-only" in line.lower():
                current["license"] = "URL-only"
            elif "prohibited" in line.lower():
                current["license"] = "PROHIBITED"
        if current and "**Vendor Policy:**" in line:
            policy = line.lower()
            current["vendorable"] = "may be vendored" in policy
            current["referenceable"] = "must never be vendored" not in policy or "url" in policy
            if current.get("license"):
                adapters[current["key"]] = {
                    "name": current["name"],
                    "license": current["license"],
                    "vendorable": current["vendorable"],
                    "referenceable": current["referenceable"],
                }
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() == "library":
            continue
        name = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cells[0]).strip()
        key = canonical_id(name)
        if "approved libraries" in section and len(cells) >= 6:
            license_match = re.search(r"SPDX:\s*([A-Za-z0-9.+-]+)", cells[4])
            license_id = license_match.group(1) if license_match else cells[4].split()[0]
            adapters[key] = {
                "name": name,
                "license": license_id,
                "vendorable": cells[5].lower().startswith("yes"),
                "referenceable": True,
            }
        elif "deliberately excluded" in section:
            adapters[key] = {
                "name": name,
                "license": "PROHIBITED",
                "vendorable": False,
                "referenceable": False,
            }
        elif "free but not mit" in section:
            adapters[key] = {
                "name": name,
                "license": "URL-only",
                "vendorable": False,
                "referenceable": True,
            }
    return adapters


def load_sources(path):
    sources = dict(DEFAULT_SOURCES)
    if not path:
        return sources
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"could not read sources file {path}: {exc}")
    if isinstance(data, list):
        data = {entry.get("id") or entry.get("library"): entry for entry in data}
    if not isinstance(data, dict):
        raise SystemExit("sources file must be a JSON object or list")
    for key, source in data.items():
        if not isinstance(source, dict):
            warn(f"skip malformed source {key}")
            continue
        item = dict(source)
        item.setdefault("type", "registry")
        sources[canonical_id(str(key))] = item
    return sources


def cache_paths(cache_dir, library_id):
    safe = slug(library_id)
    return cache_dir / f"{safe}.records.json", cache_dir / f"{safe}.meta.json"


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_text(url, meta):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in {"", "file"}:
        path = Path(urllib.request.url2pathname(parsed.path)) if parsed.scheme == "file" else Path(url)
        return path.read_text(encoding="utf-8"), {}

    headers = {"User-Agent": "Kinetic-UI-UX-Pro registry metadata sync"}
    if meta.get("etag"):
        headers["If-None-Match"] = meta["etag"]
    if meta.get("last_modified"):
        headers["If-Modified-Since"] = meta["last_modified"]
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
        return body, {
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return sorted(str(k) for k in value.keys())
    if isinstance(value, str):
        return [value]
    return [str(value)]


def text_value(item, *names):
    for name in names:
        value = item.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    links = item.get("links")
    if isinstance(links, dict):
        for name in names:
            value = links.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def absolute_url(value, base_url):
    if not value:
        return ""
    return urllib.parse.urljoin(base_url, value)


def component_registry_url(item, source, name):
    explicit = text_value(
        item,
        "registry_url", "registryUrl", "source_url", "sourceUrl",
        "item_url", "itemUrl", "fetch_url", "fetchUrl",
    )
    if explicit:
        return absolute_url(explicit, source["url"])
    if source.get("type") in {"registry", "catalog", "static"}:
        parsed = urllib.parse.urlparse(source["url"])
        if parsed.path.endswith("/registry.json"):
            return urllib.parse.urljoin(source["url"], f"{slug(name)}.json")
    return source["url"]


def dependency_list(item):
    deps = []
    for key in ("dependencies", "devDependencies", "peerDependencies", "registryDependencies"):
        deps.extend(as_list(item.get(key)))
    clean = []
    seen = set()
    for dep in deps:
        dep = str(dep).strip()
        if dep and dep not in seen:
            seen.add(dep)
            clean.append(dep)
    return clean


def iterable_items(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("items", "components", "registry", "blocks", "data", "results"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    nested = []
    for value in data.values():
        if isinstance(value, dict):
            nested.append(value)
    return nested


def has_source_payload(item):
    if not isinstance(item, dict):
        return False
    for key, value in item.items():
        if key in SOURCE_FIELD_NAMES and value:
            return True
    return False


def registry_records(library_id, source, body):
    try:
        data = json.loads(body)
    except Exception as exc:
        warn(f"{library_id}: malformed JSON skipped: {exc}")
        return []
    records = []
    for item in iterable_items(data):
        if not isinstance(item, dict):
            continue
        if has_source_payload(item):
            warn(f"{library_id}: stripped source-bearing fields from {item.get('name', 'unnamed item')}")
        name = text_value(item, "name", "title", "component", "label")
        if not name:
            continue
        category = text_value(item, "category", "type", "group") or "component"
        description = text_value(item, "description", "summary", "excerpt")
        docs_url = absolute_url(text_value(item, "docs_url", "docsUrl", "docs", "url", "href"), source["url"])
        registry_url = component_registry_url(item, source, name)
        tags = [slug(tag) for tag in as_list(item.get("tags") or item.get("keywords"))]
        tags.extend(slug(tag) for tag in source.get("tags", []))
        records.append({
            "id": f"{library_id}:{slug(name)}",
            "library": source.get("library_name", library_id),
            "name": name,
            "description": description,
            "category": category,
            "dependencies": dependency_list(item),
            "registry_url": registry_url,
            "docs_url": docs_url,
            "framework": source.get("framework", ""),
            "tags": sorted(set(tag for tag in tags if tag)),
        })
    return records


def sitemap_records(library_id, source, body):
    try:
        root = ET.fromstring(body.encode("utf-8"))
    except Exception as exc:
        warn(f"{library_id}: malformed sitemap skipped: {exc}")
        return []
    urls = []
    for loc in root.findall(".//{*}loc"):
        if loc.text:
            urls.append(loc.text.strip())
    path_filter = source.get("path_filter", "")
    records = []
    for url in urls:
        parsed = urllib.parse.urlparse(url)
        if path_filter and path_filter not in parsed.path:
            continue
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            continue
        name = parts[-1].replace("-", " ").replace("_", " ").title()
        category = parts[-2] if len(parts) > 1 else "component"
        tags = sorted(set([slug(category), *[slug(tag) for tag in source.get("tags", [])]]))
        records.append({
            "id": f"{library_id}:{slug(name)}",
            "library": source.get("library_name", library_id),
            "name": name,
            "description": "",
            "category": category,
            "dependencies": [],
            "registry_url": source["url"],
            "docs_url": url,
            "framework": source.get("framework", ""),
            "tags": tags,
        })
    return records


def parse_records(library_id, source, body):
    kind = source.get("type", "registry")
    if kind in {"registry", "catalog", "static"}:
        return registry_records(library_id, source, body)
    if kind == "sitemap":
        return sitemap_records(library_id, source, body)
    warn(f"{library_id}: unknown source type {kind}")
    return []


def sanitized_records_for(library_id, source, adapter, registry_dir):
    cache_dir = registry_dir / "cache"
    records_path, meta_path = cache_paths(cache_dir, library_id)
    meta = read_json(meta_path, {})
    source = dict(source)
    source["library_name"] = adapter["name"]
    try:
        body, headers = fetch_text(source["url"], meta)
        records = parse_records(library_id, source, body)
        refreshed = today_iso()
        for record in records:
            record["license"] = adapter["license"]
            record["refreshed_at"] = refreshed
        write_json(records_path, records)
        new_meta = {
            "url": source["url"],
            "source_type": source.get("type", "registry"),
            "record_count": len(records),
            "refreshed_at": refreshed,
            "body_sha256": hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest(),
        }
        new_meta.update({k: v for k, v in headers.items() if v})
        write_json(meta_path, new_meta)
        return records
    except urllib.error.HTTPError as exc:
        if exc.code != 304:
            return cached_or_empty(library_id, records_path, f"HTTP {exc.code}")
        records = read_json(records_path, [])
        if records:
            warn(f"{library_id}: not modified; used sanitized cache")
        return records
    except Exception as exc:
        return cached_or_empty(library_id, records_path, str(exc))


def cached_or_empty(library_id, records_path, reason):
    records = read_json(records_path, [])
    if records:
        warn(f"{library_id}: offline/error ({reason}); used last good sanitized cache")
        return records
    warn(f"{library_id}: offline/error ({reason}); no cache available")
    return []


def components_path(registry_dir):
    return registry_dir / COMPONENTS_FILE


def read_components(registry_dir):
    path = components_path(registry_dir)
    if not path.exists():
        return []
    records = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except Exception as exc:
            warn(f"skip malformed {path}:{line_no}: {exc}")
    return records


def write_components(registry_dir, records):
    registry_dir.mkdir(parents=True, exist_ok=True)
    path = components_path(registry_dir)
    records = sorted(records, key=lambda r: (r.get("library", ""), r.get("category", ""), r.get("name", "")))
    text = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
    path.write_text(text, encoding="utf-8")
    try:
        label = path.relative_to(ROOT)
    except ValueError:
        label = path
    print(f"wrote {len(records)} records to {label}")


def allowed_adapter(library_id, source, adapters):
    adapter_key = canonical_id(source.get("adapter") or source.get("library") or library_id)
    adapter = adapters.get(adapter_key) or adapters.get(library_id)
    if not adapter:
        warn(f"{library_id}: no library adapter found; refusing ingestion")
        return None
    if not adapter.get("referenceable", False):
        warn(f"{library_id}: adapter marks this library non-vendorable and non-referenceable")
        return None
    return adapter


def sync_libraries(library_ids, sources, adapters, registry_dir):
    existing = read_components(registry_dir)
    synced_ids = set()
    new_records = []
    for library_id in library_ids:
        library_id = canonical_id(library_id)
        source = sources.get(library_id)
        if not source:
            warn(f"unknown registry source: {library_id}")
            continue
        adapter = allowed_adapter(library_id, source, adapters)
        if not adapter:
            continue
        records = sanitized_records_for(library_id, source, adapter, registry_dir)
        synced_ids.add(library_id)
        new_records.extend(records)
        print(f"{library_id}: {len(records)} metadata records")
    kept = [r for r in existing if canonical_id(r.get("library", "")) not in synced_ids and not str(r.get("id", "")).split(":")[0] in synced_ids]
    write_components(registry_dir, kept + new_records)


def print_stats(records):
    if not records:
        print("No registry records found.")
        return
    library_counts = Counter(r.get("library", "unknown") for r in records)
    category_counts = Counter(r.get("category", "uncategorized") for r in records)
    print("## Registry Stats\n")
    print("| Library | Count |")
    print("| --- | ---: |")
    for key, count in sorted(library_counts.items()):
        print(f"| {key} | {count} |")
    print("\n| Category | Count |")
    print("| --- | ---: |")
    for key, count in sorted(category_counts.items()):
        print(f"| {key} | {count} |")


def parse_time(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def print_stale(records):
    now = dt.datetime.now(dt.timezone.utc)
    stale = []
    for record in records:
        refreshed = parse_time(record.get("refreshed_at"))
        if not refreshed:
            stale.append((9999, record))
            continue
        age = (now - refreshed).days
        if age > STALE_DAYS:
            stale.append((age, record))
    if not stale:
        print("No stale registry records.")
        return
    print("| Age (days) | Library | Component | Docs |")
    print("| ---: | --- | --- | --- |")
    for age, record in sorted(stale, key=lambda item: (-item[0], item[1].get("id", ""))):
        print(f"| {age} | {record.get('library', '')} | {record.get('name', '')} | {record.get('docs_url', '')} |")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sync component registry metadata without source code.")
    parser.add_argument("--sync", metavar="LIBRARY", help="sync one configured library")
    parser.add_argument("--sync-all", action="store_true", help="sync every configured safe library")
    parser.add_argument("--stats", action="store_true", help="show counts per library and category")
    parser.add_argument("--stale", action="store_true", help="list records not refreshed in over 30 days")
    parser.add_argument("--sources", help="optional JSON source map for additional registry/catalog/sitemap endpoints")
    parser.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY_DIR), help="registry output directory")
    parser.add_argument("--adapter-file", default=str(DEFAULT_ADAPTER_FILE), help="library adapter reference markdown")
    args = parser.parse_args(argv)

    registry_dir = Path(args.registry_dir)
    adapters = parse_adapter_table(Path(args.adapter_file))
    sources = load_sources(args.sources)

    sync_requested = bool(args.sync or args.sync_all)
    read_requested = bool(args.stats or args.stale)
    if args.stats and args.stale:
        parser.error("choose only one report mode: --stats or --stale")
    if args.sync and args.sync_all:
        parser.error("choose only one sync mode: --sync or --sync-all")
    if not sync_requested and not read_requested:
        parser.error("choose --sync, --sync-all, --stats, or --stale")

    if args.sync:
        sync_libraries([args.sync], sources, adapters, registry_dir)
    elif args.sync_all:
        safe_ids = [
            library_id for library_id, source in sources.items()
            if allowed_adapter(library_id, source, adapters)
        ]
        sync_libraries(safe_ids, sources, adapters, registry_dir)
    if sync_requested and not read_requested:
        return 0

    records = read_components(registry_dir)
    if args.stats:
        print_stats(records)
    elif args.stale:
        print_stale(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
