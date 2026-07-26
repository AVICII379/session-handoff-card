from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import re


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "session-handoff-card"
SKILL = PLUGIN / "skills" / "session-handoff-card"


class RepositoryContractTests(unittest.TestCase):
    def test_marketplace_points_to_plugin(self) -> None:
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(marketplace["name"], "session-handoff-card")
        entries = marketplace["plugins"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["name"], "session-handoff-card")
        self.assertEqual(
            entry["source"]["path"], "./plugins/session-handoff-card"
        )
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

    def test_plugin_manifest_is_publishable_shape(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "session-handoff-card")
        self.assertEqual(manifest["version"], "0.3.2")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["author"]["name"], "AVICII379")
        self.assertEqual(
            manifest["author"]["url"], "https://github.com/AVICII379"
        )
        repository_url = "https://github.com/AVICII379/session-handoff-card"
        self.assertEqual(manifest["repository"], repository_url)
        self.assertEqual(manifest["homepage"], repository_url)
        self.assertNotIn("email", manifest["author"])
        self.assertNotIn("license", manifest)
        interface = manifest["interface"]
        for field in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
            "capabilities",
            "defaultPrompt",
        ):
            self.assertIn(field, interface)
        self.assertIn("中", interface["shortDescription"])
        self.assertEqual(interface["developerName"], "AVICII379")
        self.assertEqual(interface["websiteURL"], repository_url)
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)
        self.assertNotIn("[TODO:", json.dumps(manifest, ensure_ascii=False))

    def test_publication_coordinates_have_no_placeholders(self) -> None:
        for relative in ("README.md", "docs/publishing.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("AVICII379/session-handoff-card", text)
            self.assertNotIn("<owner>/<repo>", text)

    def test_ci_uses_read_only_current_actions(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("actions/checkout@v7", workflow)
        self.assertIn("actions/setup-python@v7", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("actions/download-artifact@v8", workflow)
        self.assertEqual(workflow.count("check_publication_privacy.py"), 2)
        self.assertIn("verify_release_set.py artifacts --expected-count 4", workflow)

    def test_skill_is_chinese_first_and_complete(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: session-handoff-card", text)
        self.assertIn("description: 创建、更新、校验并接收中文优先", text)
        self.assertIn("不得用抽样冒充 `FULL`", text)
        self.assertIn("## 不可违背", text)
        required = [
            "assets/handoff-card-template.md",
            "references/handoff-protocol.md",
            "references/long-context-reconstruction.md",
            "references/model-compatibility.md",
            "scripts/chunk_history.py",
            "scripts/new_handoff.py",
            "scripts/validate_handoff.py",
            "scripts/verify_history.py",
        ]
        for relative in required:
            self.assertTrue((SKILL / relative).is_file(), relative)

    def test_all_python_files_parse(self) -> None:
        python_files = sorted(
            list(SKILL.rglob("*.py"))
            + list((ROOT / "examples").rglob("*.py"))
            + list((ROOT / "tools").rglob("*.py"))
            + list((ROOT / "tests").rglob("*.py"))
        )
        self.assertTrue(python_files)
        for path in python_files:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_readme_relative_links_exist(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)
        relative = [
            link
            for link in links
            if not link.startswith(("https://", "http://", "#"))
        ]
        self.assertTrue(relative)
        for link in relative:
            self.assertTrue((ROOT / link).is_file(), link)

    def test_end_to_end_demo(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "examples" / "run_demo.py")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        result = json.loads(completed.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "HANDOFF_READY")
        self.assertEqual(result["history_coverage"], "FULL")
        self.assertTrue(result["coverage_exact"])
        self.assertGreaterEqual(result["chunks"], 2)
        self.assertGreaterEqual(result["source_chars"], 3000)
        self.assertGreaterEqual(result["card_chars"], 1500)
        self.assertLessEqual(result["card_chars"], 3500)
        self.assertLess(result["compression_ratio"], 0.85)
        self.assertLessEqual(result["evidence_rows"], 6)
        self.assertEqual(result["validator_errors"], 0)
        self.assertEqual(result["validator_warnings"], 0)
        self.assertFalse(result["persisted"])

    def test_validator_warns_on_reverse_compression(self) -> None:
        with tempfile.TemporaryDirectory(prefix="handoff-bloat-") as temp:
            output = Path(temp) / "demo"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "examples" / "run_demo.py"),
                    "--output-dir",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            card = output / "handoff-card.md"
            text = card.read_text(encoding="utf-8")
            text = text.replace(
                "- 当前目标：",
                "- 当前目标：" + ("重复复述" * 900),
                1,
            )
            card.write_text(text, encoding="utf-8", newline="\n")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "validate_handoff.py"),
                    str(card),
                    "--strict",
                    "--check-paths",
                    "--source-history",
                    str(ROOT / "examples" / "long-session" / "conversation.md"),
                    "--json",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertGreater(result["compression_ratio"], 0.85)
            warnings = "\n".join(result["warnings"])
            self.assertIn("超过 5000 字符", warnings)
            self.assertIn("源历史的 85%", warnings)

    def test_release_zip_is_deterministic_and_complete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="handoff-release-set-") as temp:
            first = Path(temp) / "first"
            second = Path(temp) / "second"
            for target in (first, second):
                subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "tools" / "package_release.py"),
                        "--output-dir",
                        str(target),
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
            first_manifest = json.loads(
                (first / "release-manifest.json").read_text(encoding="utf-8")
            )
            second_manifest = json.loads(
                (second / "release-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(first_manifest["sha256"], second_manifest["sha256"])
            archive = first / first_manifest["archive"]
            with zipfile.ZipFile(archive) as package:
                infos = package.infolist()
                names = {info.filename for info in infos}
            self.assertIn(".codex-plugin/plugin.json", names)
            self.assertIn("skills/session-handoff-card/SKILL.md", names)
            self.assertEqual(first_manifest["file_count"], len(names))
            for info in infos:
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.date_time, (2020, 1, 1, 0, 0, 0))
                self.assertEqual(info.create_system, 3)

            verified = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "verify_release_set.py"),
                    temp,
                    "--expected-count",
                    "2",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            verification = json.loads(verified.stdout)
            self.assertTrue(verification["ok"])
            self.assertEqual(verification["package_count"], 2)

    def test_publication_privacy_gate_scans_source_and_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="handoff-privacy-") as temp:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "package_release.py"),
                    "--output-dir",
                    temp,
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "check_publication_privacy.py"),
                    "--archive-dir",
                    temp,
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertGreater(result["repository_text_files"], 20)
            self.assertEqual(len(result["archives"]), 1)
            self.assertEqual(result["findings"], [])

    def test_publication_privacy_gate_detects_representative_leaks(self) -> None:
        script = ROOT / "tools" / "check_publication_privacy.py"
        spec = importlib.util.spec_from_file_location("publication_privacy", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        slash = chr(92)
        sample = "\n".join(
            [
                "C:" + slash + "Users" + slash + "example-user" + slash + "notes.txt",
                "person" + "@" + "example.org",
                "sk-" + ("a" * 24),
                "ghp_" + ("b" * 24),
                ("-" * 5) + "BEGIN PRIVATE KEY" + ("-" * 5),
            ]
        )
        findings = module.scan_text("synthetic.txt", sample, [])
        kinds = {finding["kind"] for finding in findings}
        self.assertTrue(
            {
                "windows_user_path",
                "email_address",
                "openai_api_key",
                "github_token",
                "private_key_block",
            }.issubset(kinds)
        )


if __name__ == "__main__":
    unittest.main()
