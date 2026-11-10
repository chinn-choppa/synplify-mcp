"""Ensure complete reciprocal navigation for the public documentation."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BILINGUAL = [
    "README.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md",
    "CHANGELOG.md", "CODE_OF_CONDUCT.md", "docs/ARCHITECTURE.md",
    "docs/ROADMAP.md", "docs/TOOL_CONTRACT.md", "docs/TESTING.md",
    "docs/COMPATIBILITY.md", "docs/THIRD_PARTY.md",
]


class BilingualDocumentationTests(unittest.TestCase):
    def test_full_reciprocal_pairs(self) -> None:
        for ru in BILINGUAL:
            english = ru[:-3] + ".en.md"
            ru_path, en_path = ROOT / ru, ROOT / english
            with self.subTest(ru=ru):
                self.assertTrue(ru_path.is_file())
                self.assertTrue(en_path.is_file())
                self.assertIn(en_path.name, ru_path.read_text(encoding="utf-8"))
                self.assertIn(ru_path.name, en_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
