from pathlib import Path
import tempfile
import unittest

from src.catalog import file_sha256, mark_duplicates, parse_filename


class CatalogTests(unittest.TestCase):
    def test_parses_year_author_and_title(self) -> None:
        row = parse_filename("2024_Wang_single cell atlas.pdf")
        self.assertEqual(row["year"], "2024")
        self.assertEqual(row["first_author"], "Wang")
        self.assertEqual(row["title"], "single cell atlas")

    def test_preserves_title_case(self) -> None:
        row = parse_filename("2023_Li_scRNA in TNBC.pdf")
        self.assertEqual(row["title"], "scRNA in TNBC")

    def test_missing_year_is_review(self) -> None:
        self.assertEqual(parse_filename("Chen_unknown cohort.pdf")["status"], "REVIEW")

    def test_unparsed_name_is_review(self) -> None:
        self.assertEqual(parse_filename("misc.pdf")["status"], "REVIEW")

    def test_sha256_uses_file_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "paper.pdf"
            path.write_bytes(b"fixture")
            self.assertEqual(len(file_sha256(path)), 64)

    def test_second_matching_hash_is_duplicate(self) -> None:
        rows = [
            {"sha256": "same", "status": "READY"},
            {"sha256": "same", "status": "READY"},
        ]
        mark_duplicates(rows)
        self.assertEqual([row["status"] for row in rows], ["READY", "DUPLICATE"])


if __name__ == "__main__":
    unittest.main()
