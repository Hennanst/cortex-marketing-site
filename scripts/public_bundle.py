"""Package only the reviewed Córtex publication surface, without mutations."""
from __future__ import annotations

from html.parser import HTMLParser
import json
import posixpath
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit

MANIFEST = "data/publication-manifest.json"
ALLOWED_ASSET_SUFFIXES = {
    ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".ico",
    ".woff", ".woff2", ".gif", ".avif",
}
LINK_ASSET_RELS = {"stylesheet", "icon", "preload", "modulepreload", "manifest"}
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
FORBIDDEN_PUBLIC_TOPLEVEL = {".git", "dist", "docs", "node_modules", "scripts", "tests", "__pycache__"}


def _validate_manifest_rel(rel: str, field: str) -> None:
    normalized = posixpath.normpath(rel)
    if (
        not rel
        or rel.startswith("/")
        or "\\" in rel
        or normalized != rel
        or normalized in {".", ".."}
        or normalized.startswith("../")
        or normalized.split("/", 1)[0] in FORBIDDEN_PUBLIC_TOPLEVEL
    ):
        raise ValueError(f"PUBLICATION_MANIFEST_UNSAFE_PATH[{field}]: {rel}")


def _load_manifest(root: Path) -> dict:
    path = root / MANIFEST
    if not path.is_file():
        raise ValueError(f"PUBLICATION_MANIFEST_MISSING: {MANIFEST}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"PUBLICATION_MANIFEST_INVALID: {exc}") from exc
    if data.get("version") != 1:
        raise ValueError("PUBLICATION_MANIFEST_VERSION_UNSUPPORTED")
    if data.get("invariant") != "REVIEWED_PUBLICATION_MANIFEST_EQUALS_BUILD_OUTPUT":
        raise ValueError("PUBLICATION_MANIFEST_INVARIANT_INVALID")
    for field in ("html", "static"):
        values = data.get(field)
        if not isinstance(values, list) or not values or any(not isinstance(v, str) for v in values):
            raise ValueError(f"PUBLICATION_MANIFEST_FIELD_INVALID: {field}")
        if values != sorted(set(values)):
            raise ValueError(f"PUBLICATION_MANIFEST_FIELD_NOT_SORTED_UNIQUE: {field}")
        for rel in values:
            _validate_manifest_rel(rel, field)
    if any(not rel.endswith(".html") for rel in data["html"]):
        raise ValueError("PUBLICATION_MANIFEST_NON_HTML_ROUTE")
    if any(rel.endswith(".html") for rel in data["static"]):
        raise ValueError("PUBLICATION_MANIFEST_HTML_IN_STATIC")
    return data


def publication_html(root: Path) -> tuple[str, ...]:
    """Return the exact reviewed HTML inventory."""
    return tuple(_load_manifest(root)["html"])


class _AssetParser(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "link":
            rels = set((values.get("rel") or "").lower().split())
            if rels & LINK_ASSET_RELS and values.get("href"):
                self.references.append(values["href"])
        for key in ("src", "poster"):
            if values.get(key):
                self.references.append(values[key])
        if values.get("srcset"):
            self.references.extend(part.strip().split()[0] for part in values["srcset"].split(",") if part.strip())


def _local_reference(source_rel: str, value: str) -> str | None:
    parsed = urlsplit(value.strip())
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    raw = unquote(parsed.path)
    if raw.startswith("/"):
        normalized = posixpath.normpath(raw.lstrip("/"))
    else:
        normalized = posixpath.normpath(posixpath.join(posixpath.dirname(source_rel), raw))
    if normalized in {"", "."}:
        return None
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"PUBLIC_ASSET_ESCAPES_ROOT: {source_rel} -> {value}")
    return normalized


def _asset_references(path: Path, rel: str) -> list[str]:
    if path.suffix.lower() == ".html":
        return _AssetParser(path.read_text(encoding="utf-8")).references
    if path.suffix.lower() == ".css":
        text = path.read_text(encoding="utf-8")
        return [match.group(2) for match in CSS_URL_RE.finditer(text)]
    return []


def public_files(root: Path):
    """Yield the manifest plus its transitive local asset dependencies."""
    root = root.resolve()
    manifest = _load_manifest(root)
    inventory = set(manifest["html"] + manifest["static"])
    pending = list(inventory)
    while pending:
        rel = pending.pop()
        path = root / rel
        if path.is_symlink():
            raise ValueError(f"PUBLIC_SYMLINK: {rel}")
        if not path.is_file():
            raise ValueError(f"PUBLIC_MANIFEST_FILE_MISSING: {rel}")
        for value in _asset_references(path, rel):
            dependency = _local_reference(rel, value)
            if dependency is None:
                continue
            if dependency.endswith(".html"):
                if dependency not in manifest["html"]:
                    raise ValueError(f"PUBLIC_ASSET_REFERENCE_TO_UNPUBLISHED_HTML: {rel} -> {dependency}")
                continue
            suffix = Path(dependency).suffix.lower()
            if suffix not in ALLOWED_ASSET_SUFFIXES:
                raise ValueError(f"PUBLIC_ASSET_TYPE_NOT_ALLOWED: {rel} -> {dependency}")
            if dependency not in inventory:
                inventory.add(dependency)
                pending.append(dependency)
    for rel in sorted(inventory):
        yield root / rel, rel


def package(root: Path, dist: Path):
    root = root.resolve()
    dist = dist.resolve()
    if dist != root / "dist" or dist.is_symlink():
        raise ValueError("Only the repository dist directory may be rebuilt")
    inventory = list(public_files(root))
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir()
    for src, rel in inventory:
        out = dist / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out)
    return len(inventory)


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    print(f"PACKAGED_FILES={package(repo, repo / 'dist')}")
