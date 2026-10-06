#!/usr/bin/env python3
"""Deploy reviewed coordinator instructions without touching private runtime data."""

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "config" / "coordinator"
DEST = ROOT / "runtime" / "coordinator"
MANIFEST = DEST / ".deployed-files.json"
NAMES = ("MAP-IMPORTS.md", "AGENTS.md", "SOUL.md", "IDENTITY.md", "USER.md")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as tmp:
        temp_path = Path(tmp.name)
        tmp.write(data)
    try:
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def main() -> int:
    os.umask(0o077)
    DEST.mkdir(parents=True, exist_ok=True, mode=0o700)
    if DEST.is_symlink():
        print(f"Refusing symlinked workspace: {DEST}", file=sys.stderr)
        return 1
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    planned = {}
    conflicts = []
    for name in NAMES:
        source = SOURCE / f"{name}.template"
        target = DEST / name
        data = source.read_bytes()
        source_hash = digest(data)
        if target.is_symlink():
            conflicts.append(name)
        elif target.exists():
            actual_hash = digest(target.read_bytes())
            if actual_hash != source_hash and actual_hash != previous.get(name):
                conflicts.append(name)
        planned[name] = (target, data, source_hash)
    if conflicts:
        print("Runtime files changed since deployment: " + ", ".join(conflicts), file=sys.stderr)
        print("Review and reconcile them with config/coordinator before retrying.", file=sys.stderr)
        return 1
    for name, (target, data, source_hash) in planned.items():
        if not target.exists() or digest(target.read_bytes()) != source_hash:
            atomic_write(target, data)
        previous[name] = source_hash
    atomic_write(MANIFEST, (json.dumps(previous, indent=2, sort_keys=True) + "\n").encode())
    print(f"Deployed coordinator instructions to {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
