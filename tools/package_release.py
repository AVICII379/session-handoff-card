#!/usr/bin/env python3
"""为 session-handoff-card 创建确定性的插件发布 ZIP 和校验清单。"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "session-handoff-card"
MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def plugin_files() -> list[Path]:
    files = sorted(path for path in PLUGIN_ROOT.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError(f"插件目录为空：{PLUGIN_ROOT}")
    for path in files:
        if path.is_symlink():
            raise RuntimeError(f"发布包拒绝符号链接：{path}")
    return files


def write_deterministic_zip(destination: Path, files: list[Path]) -> None:
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in files:
            relative = path.relative_to(PLUGIN_ROOT).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="创建确定性的 Skill 插件发布包。")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "dist",
        help="发布文件输出目录，默认 ./dist。",
    )
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    name = manifest["name"]
    version = manifest["version"]
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_path = output_dir / f"{name}-plugin-{version}.zip"
    if archive_path.exists():
        archive_path.unlink()

    files = plugin_files()
    write_deterministic_zip(archive_path, files)
    digest = file_sha256(archive_path)

    release_manifest = {
        "plugin": name,
        "version": version,
        "protocol": "session-handoff-card/v1.2",
        "archive": archive_path.name,
        "sha256": digest,
        "file_count": len(files),
    }
    manifest_out = output_dir / "release-manifest.json"
    manifest_out.write_text(
        json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    sums_out = output_dir / "SHA256SUMS.txt"
    sums_out.write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8", newline="\n"
    )

    print(json.dumps(release_manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
