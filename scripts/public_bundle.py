"""One inventory for packaging and parity; no content transformations."""
from pathlib import Path
import shutil

EXCLUDED_DIRS = {"dist", "scripts", "docs", "tests", "node_modules", "__pycache__"}
PUBLIC_SUFFIXES = {".html", ".css", ".js", ".json", ".xml", ".txt", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".ico", ".woff", ".woff2", ".gif"}
EXCLUDED_FILES = {"release-state.json", "package.json", "package-lock.json"}


def public_files(root: Path):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(p.startswith(".") or p in EXCLUDED_DIRS for p in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"PUBLIC_SYMLINK: {rel}")
        if path.is_file() and path.name not in EXCLUDED_FILES and (path.suffix.lower() in PUBLIC_SUFFIXES or path.name in {"_headers", "_redirects"}):
            yield path, rel.as_posix()


def package(root: Path, dist: Path):
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
    root = Path(__file__).resolve().parents[1]
    print(f"PACKAGED_FILES={package(root, root / 'dist')}")
