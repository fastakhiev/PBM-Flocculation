#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
import sys
from collections import deque
from pathlib import Path


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_directories(paths) -> list[Path]:
    result = []
    seen = set()
    for path in paths:
        if not path:
            continue
        directory = Path(path).resolve()
        key = str(directory).casefold()
        if directory.is_dir() and key not in seen:
            result.append(directory)
            seen.add(key)
    return result


def _search_directories(ctypes_binary: Path) -> list[Path]:
    roots = _unique_directories((sys.base_prefix, sys.prefix, Path(sys.executable).parent))
    directories = [ctypes_binary.parent]
    for root in roots:
        directories.extend((root, root / "DLLs", root / "Library" / "bin"))
    directories.extend(os.environ.get("PATH", "").split(os.pathsep))
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    directories.extend((system_root, system_root / "System32"))
    return _unique_directories(directories)


def _resolve_library(name: str, directories: list[Path]) -> Path | None:
    lowered_name = name.casefold()
    for directory in directories:
        direct = directory / name
        if direct.is_file():
            return direct.resolve()
        try:
            for candidate in directory.iterdir():
                if candidate.is_file() and candidate.name.casefold() == lowered_name:
                    return candidate.resolve()
        except OSError:
            continue
    return None


def _is_windows_system_library(path: Path) -> bool:
    system_root = str(Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve()).casefold()
    candidate = str(path.resolve()).casefold()
    return candidate == system_root or candidate.startswith(system_root + os.sep)


def _imports(path: Path) -> list[str]:
    import pefile

    pe = pefile.PE(str(path), fast_load=True)
    try:
        directories = [
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
        ]
        pe.parse_data_directories(directories=directories)
        names = set()
        for attribute in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
            for entry in getattr(pe, attribute, ()):
                raw_name = entry.dll
                names.add(raw_name.decode("ascii") if isinstance(raw_name, bytes) else str(raw_name))
        return sorted(names, key=str.casefold)
    finally:
        pe.close()


def _copy_dependency(source: Path, target_directory: Path) -> Path:
    destination = target_directory / source.name
    if destination.exists() and _file_hash(destination) != _file_hash(source):
        raise RuntimeError(f"Conflicting runtime DLLs resolve to {destination.name}")
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination


def collect_runtime(target_directory: Path) -> dict:
    if sys.platform != "win32":
        raise RuntimeError("This runtime collector must be executed on Windows.")

    import _ctypes

    ctypes_binary = Path(_ctypes.__file__).resolve()
    search_directories = _search_directories(ctypes_binary)
    target_directory.mkdir(parents=True, exist_ok=True)

    queue = deque([ctypes_binary])
    visited = set()
    copied = {}
    dependency_records = []
    unresolved = []

    while queue:
        binary = queue.popleft().resolve()
        binary_key = str(binary).casefold()
        if binary_key in visited:
            continue
        visited.add(binary_key)

        for name in _imports(binary):
            resolved = _resolve_library(name, search_directories)
            record = {"required_by": str(binary), "name": name}
            if resolved is None:
                if name.casefold().startswith(("api-ms-win-", "ext-ms-")):
                    record["source"] = "windows-api-set"
                else:
                    record["source"] = None
                    unresolved.append(record)
                dependency_records.append(record)
                continue

            record["source"] = str(resolved)
            if _is_windows_system_library(resolved):
                record["bundled"] = False
            else:
                destination = _copy_dependency(resolved, target_directory)
                record["bundled"] = True
                record["destination"] = str(destination)
                copied[destination.name.casefold()] = {
                    "name": destination.name,
                    "source": str(resolved),
                    "sha256": _file_hash(destination),
                }
                queue.append(resolved)
            dependency_records.append(record)

    if unresolved:
        details = ", ".join(sorted({entry["name"] for entry in unresolved}, key=str.casefold))
        raise RuntimeError(f"Unresolved non-system DLL dependencies for _ctypes: {details}")
    if not any(name.startswith(("ffi-", "libffi-")) for name in copied):
        raise RuntimeError("The analyzed _ctypes dependency chain does not contain a bundled libffi DLL.")

    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "ctypes_binary": str(ctypes_binary),
        "target_directory": str(target_directory.resolve()),
        "search_directories": [str(path) for path in search_directories],
        "copied": sorted(copied.values(), key=lambda item: item["name"].casefold()),
        "dependencies": dependency_records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundle the complete Windows _ctypes DLL dependency chain.")
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    report = collect_runtime(args.target)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Bundled _ctypes runtime DLLs:")
    for item in report["copied"]:
        print(f"  {item['name']} <- {item['source']}")


if __name__ == "__main__":
    main()
