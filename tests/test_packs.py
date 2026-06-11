"""Tests for the WAYAN_PACK profession installer (v1).

Layout assertions plus safe functional checks of install.sh's pack preflight.
The preflight runs *before* the root check, so the functional tests never get
past validation; tests that would continue past it as root are skipped when
the suite runs as root (e.g. on the VPS).

    python -m unittest tests.test_packs
"""
import os
import re
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(REPO, "install.sh")

REQUIRED_PACKS = ["onchain", "creator", "devops", "student", "founder"]

REQUIRED_PACK_FILES = [
    "pack.md",
    os.path.join("jupiter", "PACK.md"),
    os.path.join("uran", "PACK.md"),
    os.path.join("memory", "cold.md"),
    os.path.join("rules", "{pack}-routing.md"),
    os.path.join("mapping", "{pack}-services.md"),
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                      # API keys
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),                     # GitHub PAT
    re.compile(r"xox[baprs]-"),                              # Slack
    re.compile(r"AKIA[0-9A-Z]{16}"),                         # AWS
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY"),            # key material
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}"),            # Telegram bot token
    re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\s*=\s*['\"]?[A-Za-z0-9_\-]{8,}"),
]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def run_installer(extra_env=None):
    env = dict(os.environ)
    env.pop("WAYAN_PACK", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", INSTALL], cwd=REPO, env=env,
        capture_output=True, text=True, timeout=60,
    )


def function_body(src, name):
    """Extract a bash function body (functions close with '}' at column 0)."""
    match = re.search(
        r"^%s\(\)\s*\{\n(.*?)^\}" % re.escape(name), src, re.S | re.M)
    if not match:
        raise AssertionError(f"function {name}() not found in install.sh")
    return match.group(1)


class PackLayoutTests(unittest.TestCase):
    def test_packs_readme(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO, "packs", "README.md")))

    def test_docs_packs_guide(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO, "docs", "PACKS.md")))

    def test_every_pack_has_required_files(self):
        for pack in REQUIRED_PACKS:
            for rel in REQUIRED_PACK_FILES:
                path = os.path.join(REPO, "packs", pack, rel.format(pack=pack))
                self.assertTrue(os.path.isfile(path), f"missing pack file: {path}")

    def test_no_secrets_in_packs(self):
        for root, _dirs, files in os.walk(os.path.join(REPO, "packs")):
            for name in files:
                path = os.path.join(root, name)
                body = read(path)
                for pat in SECRET_PATTERNS:
                    self.assertIsNone(
                        pat.search(body),
                        f"secret-shaped content in {path}: pattern {pat.pattern}")

    def test_templates_have_pack_hook(self):
        for agent in ("jupiter", "uran"):
            body = read(os.path.join(REPO, "templates", agent, "CLAUDE.md"))
            self.assertIn("PACK.md", body, agent)
            self.assertIn("profession pack", body.lower(), agent)


class InstallerStaticTests(unittest.TestCase):
    def setUp(self):
        self.src = read(INSTALL)

    def test_install_sh_syntax(self):
        proc = subprocess.run(["bash", "-n", INSTALL],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_pack_name_validation_exists(self):
        self.assertIn("WAYAN_PACK", self.src)
        self.assertIn("^[a-z][a-z0-9_-]{0,31}$", self.src)

    def test_pack_flow_skipped_when_unset(self):
        # Both pack entry points bail out immediately on an empty WAYAN_PACK.
        for fn in ("preflight_pack", "deploy_pack"):
            body = function_body(self.src, fn)
            self.assertIn('[[ -z "${WAYAN_PACK}" ]] && return 0', body, fn)

    def test_pack_deployed_before_defaults(self):
        main = function_body(self.src, "main")
        self.assertLess(main.index("deploy_pack"), main.index("copy_templates"))
        self.assertLess(main.index("deploy_pack"), main.index("deploy_skills"))
        self.assertLess(main.index("deploy_pack"), main.index("deploy_orchestration"))

    def test_deploy_pack_is_no_clobber_only(self):
        # Every file copy in deploy_pack goes through copy_template (which
        # keeps existing files); no raw cp/overwriting install of files.
        body = function_body(self.src, "deploy_pack")
        self.assertIn("copy_template", body)
        self.assertNotIn("cp ", body)
        self.assertNotIn("cp -r", body)
        for line in body.splitlines():
            if "install " in line:
                self.assertIn("install -d", line,
                              f"non-directory install in deploy_pack: {line}")

    def test_copy_template_no_clobber_preserved(self):
        body = function_body(self.src, "copy_template")
        self.assertIn('if [[ -f "${dst}" ]]', body)
        self.assertIn("return", body)

    def test_pack_files_owned_by_wayan(self):
        # copy_template installs as wayan:wayan; deploy_pack creates dirs the same way.
        self.assertIn('-o "${WAYAN_USER}" -g "${WAYAN_USER}" "${src}" "${dst}"',
                      self.src)
        body = function_body(self.src, "deploy_pack")
        self.assertIn('-o "${WAYAN_USER}" -g "${WAYAN_USER}"', body)

    def test_banner_shows_pack_or_default(self):
        body = function_body(self.src, "final_banner")
        self.assertIn("PROFESSION PACK", body)
        self.assertIn("WAYAN_PACK", body)
        self.assertIn("default", body)


class InstallerFunctionalTests(unittest.TestCase):
    """Run install.sh's preflight only — it exits before any system change."""

    def test_missing_pack_fails_with_available_list(self):
        proc = run_installer({"WAYAN_PACK": "no-such-pack-xyz"})
        self.assertNotEqual(proc.returncode, 0)
        err = proc.stderr
        self.assertIn("Available packs", err)
        for pack in REQUIRED_PACKS:
            self.assertIn(pack, err)
        # Must fail before the root gate / any install step.
        self.assertNotIn("must run as root", err)

    def test_invalid_pack_name_rejected(self):
        for bad in ("../etc", "Onchain", "a b", "x" * 40, "-lead"):
            proc = run_installer({"WAYAN_PACK": bad})
            self.assertNotEqual(proc.returncode, 0, bad)
            self.assertIn("Invalid WAYAN_PACK", proc.stderr, bad)

    @unittest.skipIf(os.geteuid() == 0, "would proceed past preflight as root")
    def test_default_no_pack_flow_unchanged(self):
        # Without WAYAN_PACK the script must reach the root gate silently —
        # no pack output at all (same first failure as before packs existed).
        for env in (None, {"WAYAN_PACK": ""}):
            proc = run_installer(env)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("must run as root", proc.stderr)
            self.assertNotIn("pack", proc.stdout.lower())
            self.assertNotIn("pack", proc.stderr.lower())

    @unittest.skipIf(os.geteuid() == 0, "would proceed past preflight as root")
    def test_valid_pack_passes_preflight(self):
        proc = run_installer({"WAYAN_PACK": "onchain"})
        self.assertNotEqual(proc.returncode, 0)  # still stops at the root gate
        self.assertIn("Profession pack selected: onchain", proc.stdout)
        self.assertIn("must run as root", proc.stderr)

    def test_existing_files_never_overwritten(self):
        # Functional no-clobber check: run the real copy_template body in a
        # sandbox (install(1) shimmed to plain cp so no chown is needed).
        src = read(INSTALL)
        body = function_body(src, "copy_template")
        script = "\n".join([
            "set -euo pipefail",
            "WAYAN_USER=$(id -un)",
            "ok() { :; }",
            "install() { local prev= last= a; "
            'for a in "$@"; do prev="$last"; last="$a"; done; '
            'cp "$prev" "$last"; }',
            "copy_template() {", body, "}",
            'T="$(mktemp -d)"; trap \'rm -rf "$T"\' EXIT',
            'echo KEEP > "$T/dst"; echo NEW > "$T/src"',
            'copy_template "$T/src" "$T/dst"',
            'grep -q KEEP "$T/dst"',          # existing file untouched
            'copy_template "$T/src" "$T/fresh"',
            'grep -q NEW "$T/fresh"',         # missing file is created
        ])
        proc = subprocess.run(["bash", "-c", script],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
