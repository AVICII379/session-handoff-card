#!/usr/bin/env python3
"""校验多个 CI 发布包的清单，并要求所有 ZIP 逐字节同哈希。"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def verify_package(manifest_path: Path) -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"无法读取 {manifest_path}: {exc}"]

    archive_name = manifest.get("archive")
    expected_hash = manifest.get("sha256")
    if not isinstance(archive_name, str) or not archive_name.endswith(".zip"):
        return manifest, [f"{manifest_path}: archive 字段无效"]
    archive_path = manifest_path.parent / archive_name
    if not archive_path.is_file():
        errors.append(f"{manifest_path}: ZIP 不存在：{archive_name}")
        return manifest, errors

    actual_hash = file_sha256(archive_path)
    if expected_hash != actual_hash:
        errors.append(
            f"{manifest_path}: 清单 SHA-256 与 ZIP 不一致：{expected_hash} != {actual_hash}"
        )

    sums_path = manifest_path.parent / "SHA256SUMS.txt"
    if not sums_path.is_file():
        errors.append(f"{manifest_path}: 缺少 SHA256SUMS.txt")
    else:
        parts = sums_path.read_text(encoding="utf-8").split()
        if len(parts) != 2 or parts[0] != actual_hash or parts[1] != archive_name:
            errors.append(f"{manifest_path}: SHA256SUMS.txt 与 ZIP 不一致")

    return {
        "directory": manifest_path.parent.as_posix(),
        "plugin": manifest.get("plugin"),
        "version": manifest.get("version"),
        "protocol": manifest.get("protocol"),
        "archive": archive_name,
        "sha256": actual_hash,
        "file_count": manifest.get("file_count"),
    }, errors


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="包含一个或多个发布工件目录的根目录。")
    parser.add_argument("--expected-count", type=int, help="期望发现的发布清单数量。")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    manifests = sorted(root.rglob("release-manifest.json"))
    errors: list[str] = []
    if not manifests:
        errors.append(f"没有发现 release-manifest.json：{root}")
    if args.expected_count is not None and len(manifests) != args.expected_count:
        errors.append(
            f"发布包数量不符：期望 {args.expected_count}，实际 {len(manifests)}"
        )

    packages: list[dict[str, object]] = []
    for manifest_path in manifests:
        package, package_errors = verify_package(manifest_path)
        if package:
            packages.append(package)
        errors.extend(package_errors)

    comparable_fields = (
        "plugin",
        "version",
        "protocol",
        "archive",
        "sha256",
        "file_count",
    )
    if packages:
        expected = {field: packages[0].get(field) for field in comparable_fields}
        for package in packages[1:]:
            actual = {field: package.get(field) for field in comparable_fields}
            if actual != expected:
                errors.append(
                    "发布包不一致："
                    + json.dumps(
                        {"expected": expected, "actual": actual},
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )

    result = {
        "ok": not errors,
        "expected_count": args.expected_count,
        "package_count": len(packages),
        "sha256": packages[0]["sha256"] if packages and not errors else None,
        "packages": packages,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
