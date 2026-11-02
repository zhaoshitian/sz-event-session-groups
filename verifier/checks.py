import json
import re
from pathlib import Path


def result(valid, message, **details):
    return {"valid": valid, "score": float(valid), "message": message, "details": details}


def identifier(value):
    return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", value) is not None


def destination_problem(value):
    p = Path(value)
    if not value or len(value) > 200 or p.is_absolute() or ".." in p.parts or "\\" in value:
        return "destination must be a relative JSON file inside the workspace"
    if p.as_posix() != value or p.suffix != ".json" or not all(identifier(part) for part in p.parts[:-1]):
        return "destination must be a canonical relative .json path with simple directory names"
    if not identifier(p.stem):
        return "destination filename is invalid"
    return None


def safe_path(workspace, destination):
    root = Path(workspace).resolve()
    path = root / destination
    if root not in path.resolve().parents:
        return None
    current = path
    while current != root:
        if current.is_symlink():
            return None
        current = current.parent
    return path


def encoded(rows, total):
    return (
        json.dumps({"records": rows, "total": total}, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    )
