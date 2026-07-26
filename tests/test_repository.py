from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "session-handoff-card"
SKILL = PLUGIN / "skills" / "session-handoff-card"
VALIDATOR = SKILL / "scripts" / "validate_handoff.py"


def run_json(arguments: list[str], cwd: Path = ROOT) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, *arguments], cwd=cwd, check=True, capture_output=True,
        text=True, encoding="utf-8",
    )
    return json.loads(completed.stdout)


class RepositoryContractTests(unittest.TestCase):
    def test_marketplace_points_to_plugin(self) -> None:
        marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(marketplace["name"], "session-handoff-card")
        self.assertEqual(marketplace["interface"]["displayName"], "AI 续聊交接卡")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["source"]["path"], "./plugins/session-handoff-card")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")

    def test_plugin_manifest_is_publishable_shape(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        repository_url = "https://github.com/AVICII379/session-handoff-card"
        self.assertEqual(manifest["name"], "session-handoff-card")
        self.assertEqual(manifest["version"], "0.4.0")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["author"], {"name": "AVICII379", "url": "https://github.com/AVICII379"})
        self.assertEqual(manifest["repository"], repository_url)
        self.assertEqual(manifest["homepage"], repository_url)
        self.assertNotIn("license", manifest)
        interface = manifest["interface"]
        self.assertEqual(interface["displayName"], "AI 续聊交接卡")
        self.assertIn("跨模型", interface["shortDescription"])
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)
        self.assertTrue(all(len(prompt) < 128 for prompt in interface["defaultPrompt"]))

    def test_openai_metadata_mentions_skill(self) -> None:
        text = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('$session-handoff-card', text)
        description = re.search(r'short_description: "([^"]+)"', text)
        self.assertIsNotNone(description)
        self.assertGreaterEqual(len(description.group(1)), 25)
        self.assertLessEqual(len(description.group(1)), 64)

    def test_publication_coordinates_and_no_fake_license(self) -> None:
        for relative in ("README.md", "docs/publishing.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("AVICII379/session-handoff-card", text)
            self.assertNotIn("<owner>/<repo>", text)
        self.assertFalse((ROOT / "LICENSE").exists())

    def test_ci_uses_read_only_current_actions(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("actions/checkout@v7", workflow)
        self.assertIn("actions/setup-python@v7", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("actions/download-artifact@v8", workflow)

    def test_skill_is_chinese_first_and_has_natural_triggers(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: session-handoff-card", text)
        for phrase in ("帮我做续聊卡", "换新聊天继续", "让另一个 AI 接手", "上下文快满了"):
            self.assertIn(phrase, text)
        for concept in ("QUICK", "VERIFIED", "纯文本", "后续候选（非授权）", "隐私预览"):
            self.assertIn(concept, text)
        required = [
            "assets/handoff-card-template.md", "assets/quick-handoff-card-template.md",
            "assets/handoff-card-template.en.md", "assets/quick-handoff-card-template.en.md",
            "scripts/chunk_history.py", "scripts/new_handoff.py", "scripts/normalize_history.py",
            "scripts/redact_handoff.py", "scripts/validate_handoff.py", "scripts/verify_history.py",
        ]
        for relative in required:
            self.assertTrue((SKILL / relative).is_file(), relative)

    def test_all_python_files_parse(self) -> None:
        python_files = sorted(list(SKILL.rglob("*.py")) + list((ROOT / "examples").rglob("*.py")) + list((ROOT / "tools").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")))
        self.assertTrue(python_files)
        for path in python_files:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_readme_relative_links_exist(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)
        relative = [link for link in links if not link.startswith(("https://", "http://", "#"))]
        self.assertTrue(relative)
        for link in relative:
            self.assertTrue((ROOT / link).is_file(), link)

    def test_universal_prompts_are_self_contained(self) -> None:
        for name, heading in (("quick-write.zh-CN.txt", "## 1. 现在要做什么"), ("quick-write.en.txt", "## 1. What we are doing now"), ("verified-write.zh-CN.txt", "## 2. 已核验证据与现状"), ("verified-write.en.txt", "## 2. Verified evidence and state")):
            text = (ROOT / "prompts" / name).read_text(encoding="utf-8")
            self.assertIn('handoff_protocol: "session-handoff-card/v1.3"', text)
            self.assertIn("project_root:", text)
            self.assertIn(heading, text)
            self.assertNotIn("$session-handoff-card", text)

    def test_quick_text_cards_validate_without_paths_or_evidence(self) -> None:
        for name, language in (("quick-zh.md", "zh-CN"), ("quick-en.md", "en")):
            result = run_json([str(VALIDATOR), str(ROOT / "tests" / "fixtures" / name), "--strict", "--json"])
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["profile"], "QUICK")
            self.assertEqual(result["delivery_mode"], "text")
            self.assertEqual(result["evidence_rows"], 0)
            self.assertEqual(result["language"], language)

    def test_v12_legacy_card_remains_readable(self) -> None:
        result = run_json([str(VALIDATOR), str(ROOT / "tests" / "fixtures" / "legacy-v1.2.md"), "--strict", "--json"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["protocol"], "session-handoff-card/v1.2")
        self.assertEqual(result["profile"], "VERIFIED")

    def test_quick_rejects_external_evidence_and_more_than_three_candidates(self) -> None:
        source = (ROOT / "tests" / "fixtures" / "quick-zh.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="handoff-invalid-") as temp:
            external = Path(temp) / "external.md"
            external.write_text(source.replace('evidence_mode: "conversation"', 'evidence_mode: "external"'), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(VALIDATOR), str(external), "--strict", "--json"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("QUICK 卡片必须使用", completed.stdout)

            candidates = Path(temp) / "candidates.md"
            candidates.write_text(source.replace("- 后续候选（非授权）：无。", "- 后续候选（非授权）：事项一；事项二；事项三；事项四"), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(VALIDATOR), str(candidates), "--strict", "--json"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("后续候选最多 3 项", completed.stdout)

            unknown = Path(temp) / "unknown-field.md"
            unknown.write_text(source.replace("project_root: ''", "project_path: ''"), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(VALIDATOR), str(unknown), "--strict", "--json"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("不支持的 frontmatter 字段：project_path", completed.stdout)

    def test_generator_selects_all_templates_and_refuses_overwrite(self) -> None:
        script = SKILL / "scripts" / "new_handoff.py"
        with tempfile.TemporaryDirectory(prefix="handoff-generator-") as temp:
            temp_path = Path(temp)
            for profile in ("quick", "verified"):
                for language in ("zh-CN", "en"):
                    output = temp_path / f"{profile}-{language}.md"
                    subprocess.run([sys.executable, str(script), "--output", str(output), "--profile", profile, "--language", language], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8")
                    text = output.read_text(encoding="utf-8")
                    self.assertIn(f'profile: "{profile.upper()}"', text)
                    self.assertIn(f'language: "{language}"', text)
                    self.assertIn('delivery_mode: "text"', text)
                    self.assertIn("project_root: ''", text)
                    duplicate = subprocess.run([sys.executable, str(script), "--output", str(output)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
                    self.assertNotEqual(duplicate.returncode, 0)

    def test_history_normalizers_cover_supported_shapes(self) -> None:
        script = SKILL / "scripts" / "normalize_history.py"
        fixtures = ROOT / "tests" / "fixtures" / "exports"
        expected = {"chatgpt.json": ("chatgpt", 3), "claude.json": ("claude", 2), "codex.jsonl": ("codex", 2), "generic.json": ("generic", 2), "generic-list.json": ("generic", 2)}
        with tempfile.TemporaryDirectory(prefix="handoff-normalize-") as temp:
            for filename, (platform, count) in expected.items():
                output = Path(temp) / f"{filename}.md"
                result = run_json([str(script), "--input", str(fixtures / filename), "--output", str(output)])
                self.assertEqual(result["platform"], platform)
                self.assertEqual(result["messages"], count)
                normalized = output.read_text(encoding="utf-8")
                self.assertIn(f"message_count: {count}", normalized)
                self.assertIn("## 0001 USER", normalized)
                self.assertNotIn(str(fixtures), normalized)
                duplicate = subprocess.run([sys.executable, str(script), "--input", str(fixtures / filename), "--output", str(output)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
                self.assertNotEqual(duplicate.returncode, 0)

    def test_redaction_preview_and_output_do_not_echo_values(self) -> None:
        script = SKILL / "scripts" / "redact_handoff.py"
        spec = importlib.util.spec_from_file_location("redact_handoff", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        slash = chr(92)
        values = [
            "C:" + slash + "Users" + slash + "sample-person" + slash + "notes.txt",
            "person" + "@" + "sample.invalid",
            "sk-" + ("a" * 24),
            "ghp_" + ("b" * 24),
            ("-" * 5) + "BEGIN PRIVATE KEY" + ("-" * 5) + "\nvalue\n" + ("-" * 5) + "END PRIVATE KEY" + ("-" * 5),
            "source_session: 'thread-1234'",
            "phone=" + "138" + "00138000",
            "https://example.invalid/path?" + "token=" + ("z" * 12),
        ]
        redacted, counts = module.redact("\n".join(values))
        self.assertTrue({"windows_home_path", "email_address", "openai_api_key", "github_token", "private_key_block", "source_session", "cn_mobile_number", "url_credential"}.issubset(counts))
        for value in values:
            self.assertNotIn(value, redacted)
        clean, clean_counts = module.redact("source_session: ''\n")
        self.assertEqual(clean, "source_session: ''\n")
        self.assertEqual(clean_counts, {})
        with tempfile.TemporaryDirectory(prefix="handoff-redact-") as temp:
            source = Path(temp) / "source.md"
            output = Path(temp) / "public.md"
            source.write_text("\n".join(values), encoding="utf-8")
            result = run_json([str(script), str(source), "--output", str(output)])
            self.assertTrue(result["changed"])
            self.assertTrue(output.is_file())
            duplicate = subprocess.run([sys.executable, str(script), str(source), "--output", str(output)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(duplicate.returncode, 0)

    def test_benchmark_covers_five_domains(self) -> None:
        result = run_json([str(ROOT / "tools" / "run_benchmark_checks.py")])
        self.assertTrue(result["ok"], result)
        self.assertEqual(set(result["domains"]), {"coding", "research", "writing", "browser", "planning"})
        self.assertEqual(set(result["profiles"].values()), {"QUICK", "VERIFIED"})

    def test_end_to_end_demo(self) -> None:
        result = run_json([str(ROOT / "examples" / "run_demo.py")])
        self.assertTrue(result["ok"])
        self.assertEqual(result["protocol"], "session-handoff-card/v1.3")
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
            subprocess.run([sys.executable, str(ROOT / "examples" / "run_demo.py"), "--output-dir", str(output)], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8")
            card = output / "handoff-card.md"
            text = card.read_text(encoding="utf-8").replace("- 当前目标：", "- 当前目标：" + ("重复复述" * 900), 1)
            card.write_text(text, encoding="utf-8", newline="\n")
            result = run_json([str(VALIDATOR), str(card), "--strict", "--check-paths", "--source-history", str(ROOT / "examples" / "long-session" / "conversation.md"), "--json"])
            self.assertTrue(result["ok"])
            warnings = "\n".join(result["warnings"])
            self.assertIn("超过 5000 字符", warnings)
            self.assertIn("源历史的 85%", warnings)

    def test_release_zip_is_deterministic_and_complete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="handoff-release-") as temp:
            first, second = Path(temp) / "first", Path(temp) / "second"
            for target in (first, second):
                run_json([str(ROOT / "tools" / "package_release.py"), "--output-dir", str(target)])
            first_manifest = json.loads((first / "release-manifest.json").read_text(encoding="utf-8"))
            second_manifest = json.loads((second / "release-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(first_manifest["sha256"], second_manifest["sha256"])
            self.assertEqual(first_manifest["version"], "0.4.0")
            self.assertEqual(first_manifest["protocol"], "session-handoff-card/v1.3")
            with zipfile.ZipFile(first / first_manifest["archive"]) as package:
                infos = package.infolist()
                names = {info.filename for info in infos}
            self.assertEqual([info.filename for info in infos], sorted(info.filename for info in infos))
            for required in (".codex-plugin/plugin.json", "skills/session-handoff-card/SKILL.md", "skills/session-handoff-card/scripts/normalize_history.py", "skills/session-handoff-card/scripts/redact_handoff.py"):
                self.assertIn(required, names)
            self.assertFalse(any("__pycache__" in name or name.endswith((".pyc", ".pyo")) for name in names))
            self.assertEqual(first_manifest["file_count"], len(names))
            for info in infos:
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.date_time, (2020, 1, 1, 0, 0, 0))
                self.assertEqual(info.create_system, 3)
            verification = run_json([str(ROOT / "tools" / "verify_release_set.py"), temp, "--expected-count", "2"])
            self.assertTrue(verification["ok"])

    def test_publication_privacy_gate_scans_source_and_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="handoff-privacy-") as temp:
            run_json([str(ROOT / "tools" / "package_release.py"), "--output-dir", temp])
            result = run_json([str(ROOT / "tools" / "check_publication_privacy.py"), "--archive-dir", temp])
            self.assertTrue(result["ok"], result)
            self.assertGreater(result["repository_text_files"], 40)
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
        sample = "\n".join(["C:" + slash + "Users" + slash + "sample-person" + slash + "notes.txt", "person" + "@" + "sample.invalid", "sk-" + ("a" * 24), "ghp_" + ("b" * 24), ("-" * 5) + "BEGIN PRIVATE KEY" + ("-" * 5)])
        kinds = {finding["kind"] for finding in module.scan_text("synthetic.txt", sample, [])}
        self.assertTrue({"windows_user_path", "email_address", "openai_api_key", "github_token", "private_key_block"}.issubset(kinds))


if __name__ == "__main__":
    unittest.main()
