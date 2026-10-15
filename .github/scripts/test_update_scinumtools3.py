import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "updater", Path(__file__).with_name("update_scinumtools3.py")
)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.formula = (
            'class Scinumtools3 < Formula\n'
            '  url "https://github.com/scinumtools/snt3/archive/refs/tags/v0.9.5.tar.gz"\n'
            f'  sha256 "{"a" * 64}"\n'
            '  revision 2\n\n'
            '  bottle do\n    root_url "https://example.com"\n'
            '    rebuild 1\n  end\n\n'
            '  resource "briefpp" do\n'
            f'    url "https://github.com/vrtulka23/briefpp/archive/{"b" * 40}.tar.gz"\n'
            f'    sha256 "{"c" * 64}"\n  end\n\n'
            '  def install\n    system "cmake", "--build", "build"\n  end\nend\n'
        )
        self.tree = {"truncated": False, "tree": [
            {"mode": "160000", "path": "external/briefpp", "sha": "d" * 40},
        ]}
        self.modules = (
            '[submodule "external/briefpp"]\n'
            'path = external/briefpp\nurl = https://github.com/vrtulka23/briefpp.git\n'
        )

    def release(self, tag, **flags):
        return dict(tag_name=tag, draft=False, prerelease=False, **flags)

    def test_versions_are_compared_numerically(self):
        self.assertEqual(
            updater.release_to_update(self.formula, self.release("v0.9.10")), "v0.9.10"
        )

    def test_same_and_older_releases_are_ignored(self):
        for tag in ("v0.9.5", "0.9.5", "v0.9.4"):
            with self.subTest(tag=tag):
                self.assertIsNone(updater.release_to_update(self.formula, self.release(tag)))

    def test_drafts_and_prereleases_are_ignored(self):
        for flag in ("draft", "prerelease"):
            release = self.release("v1.0.0")
            release[flag] = True
            self.assertIsNone(updater.release_to_update(self.formula, release))

    def test_unexpected_tag_is_rejected(self):
        for tag in ("v1.0.0-rc1", 'v1.0.0\nchanged=true', '$(echo bad)'):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                updater.release_to_update(self.formula, self.release(tag))

    def test_updates_source_and_pins_and_removes_obsolete_packaging(self):
        downloads = []

        def checksum(url):
            downloads.append(url)
            return ("e" if len(downloads) == 1 else "f") * 64

        result = updater.updated_formula(
            self.formula, "v0.9.10", self.tree, self.modules, checksum
        )
        self.assertEqual(downloads, [
            "https://github.com/scinumtools/snt3/archive/refs/tags/v0.9.10.tar.gz",
            f'https://github.com/vrtulka23/briefpp/archive/{"d" * 40}.tar.gz',
        ])
        self.assertIn(f'  sha256 "{"e" * 64}"', result)
        self.assertIn(f'    sha256 "{"f" * 64}"', result)
        self.assertNotIn("bottle do", result)
        self.assertNotIn("revision 2", result)
        self.assertEqual(result.split("  def install")[1], self.formula.split("  def install")[1])

    def test_changed_dependency_layout_fails_before_downloads(self):
        cases = [
            ({"truncated": True, "tree": self.tree["tree"]}, self.modules),
            ({"tree": []}, self.modules),
            (self.tree, self.modules.replace("vrtulka23/briefpp", "other/briefpp")),
            ({"tree": self.tree["tree"] + [
                {"mode": "160000", "path": "external/new", "sha": "e" * 40}
            ]}, self.modules),
        ]
        for tree, modules in cases:
            with self.subTest(tree=tree, modules=modules), patch.object(updater, "archive_sha256") as download:
                with self.assertRaises(ValueError):
                    updater.updated_formula(self.formula, "v1.0.0", tree, modules, download)
                download.assert_not_called()

    def test_noop_does_not_fetch_or_write_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            formula = Path(directory) / "formula.rb"
            output = Path(directory) / "output"
            formula.write_text(self.formula)
            with patch.object(updater, "FORMULA", formula), patch.object(
                updater, "github_api", return_value=self.release("v0.9.5")
            ) as api, patch.dict(updater.os.environ, GITHUB_OUTPUT=str(output)):
                updater.main()
            api.assert_called_once_with("releases/latest")
            self.assertEqual(formula.read_text(), self.formula)
            self.assertEqual(output.read_text(), "changed=false\n")

    def test_failure_leaves_formula_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            formula = Path(directory) / "formula.rb"
            formula.write_text(self.formula)
            with patch.object(updater, "FORMULA", formula), patch.object(
                updater, "github_api", side_effect=[self.release("v1.0.0"), RuntimeError("API failed")]
            ), self.assertRaises(RuntimeError):
                updater.main()
            self.assertEqual(formula.read_text(), self.formula)


if __name__ == "__main__":
    unittest.main()
