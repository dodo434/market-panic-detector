"""File picker paths may be absolute, but must have the expected type and no traversal."""

from pathlib import Path


def selected_file(name: str, suffix: str) -> Path:
    path = Path(name).expanduser()
    if ".." in path.parts or path.suffix.lower() != suffix or path.is_symlink() or path.is_dir():
        raise ValueError(f"Choose a regular {suffix} file using the file picker.")
    if any(p.is_symlink() for p in path.parents):
        raise ValueError("Choose a folder directly instead of a linked folder.")
    return path.resolve()
