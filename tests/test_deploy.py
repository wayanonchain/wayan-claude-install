"""Tests for the repo-first deploy workflow (scripts/deploy-gateway.sh).

The script is exercised against a throwaway git repo + fake /opt trees in a
temp dir, using the documented test overrides (WAYAN_*_OPT,
WAYAN_DEPLOY_REQUIRE_VPS=false, WAYAN_DEPLOY_CHOWN=false). Production paths,
env files, and systemd are never touched.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY = os.path.join(REPO, "scripts", "deploy-gateway.sh")
UPDATE = os.path.join(REPO, "scripts", "update.sh")

SECRET_ENV = "TELEGRAM_BOT_TOKEN=000000:FAKE-TEST-VALUE\nGROQ_API_KEY=fake\n"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


class SyntaxTests(unittest.TestCase):
    def test_deploy_script_syntax(self):
        res = run(["bash", "-n", DEPLOY])
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_update_script_syntax(self):
        res = run(["bash", "-n", UPDATE])
        self.assertEqual(res.returncode, 0, res.stderr)


class DeployScriptTests(unittest.TestCase):
    """End-to-end behaviour against a sandboxed repo + fake /opt trees."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wayan-deploy-")
        self.repo = os.path.join(self.tmp, "repo")
        self.jup = os.path.join(self.tmp, "opt-jupiter")
        self.uran = os.path.join(self.tmp, "opt-uran")

        # Sandbox repo: real gateway sources + the real script, own git history.
        shutil.copytree(os.path.join(REPO, "src", "gateway"),
                        os.path.join(self.repo, "src", "gateway"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(self.repo, "scripts"))
        shutil.copy(DEPLOY, os.path.join(self.repo, "scripts", "deploy-gateway.sh"))
        self.script = os.path.join(self.repo, "scripts", "deploy-gateway.sh")
        for cmd in (["git", "init", "-q", "-b", "main"],
                    ["git", "add", "-A"],
                    ["git", "-c", "user.name=t", "-c", "user.email=t@t",
                     "commit", "-qm", "init"]):
            res = run(cmd, cwd=self.repo)
            self.assertEqual(res.returncode, 0, res.stderr)

        # Fake production trees: identical deploys + a secret-bearing env file
        # next to them that must never change.
        for root in (self.jup, self.uran):
            shutil.copytree(os.path.join(self.repo, "src", "gateway"),
                            os.path.join(root, "gateway"))
            with open(os.path.join(root, "agent.env"), "w") as fh:
                fh.write(SECRET_ENV)

        self.env = dict(
            os.environ,
            WAYAN_JUPITER_OPT=self.jup,
            WAYAN_URAN_OPT=self.uran,
            WAYAN_DEPLOY_REQUIRE_VPS="false",
            WAYAN_DEPLOY_CHOWN="false",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers ---------------------------------------------------------
    def _run(self, *flags):
        return run(["bash", self.script, *flags], env=self.env, cwd=self.repo)

    def _drift_jupiter(self):
        """Introduce drift: production app.py differs from the repo."""
        path = os.path.join(self.jup, "gateway", "app.py")
        with open(path, "a") as fh:
            fh.write("\n# hotfix-made-directly-on-vps\n")
        return path

    def _backups(self, root):
        return [d for d in os.listdir(root) if d.startswith("gateway.bak.")]

    # -- check mode ------------------------------------------------------
    def test_check_pass_when_identical(self):
        res = self._run("--check")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Status: PASS, production matches repo", res.stdout)

    def test_check_detects_drift_names_only(self):
        self._drift_jupiter()
        res = self._run("--check")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("Status: FAIL", res.stdout)
        self.assertIn("app.py", res.stdout)
        # Names only — never file contents (the drifted line must not leak).
        self.assertNotIn("hotfix-made-directly-on-vps", res.stdout + res.stderr)

    # -- dry-run ---------------------------------------------------------
    def test_dry_run_changes_nothing(self):
        drifted = self._drift_jupiter()
        with open(drifted) as fh:
            before = fh.read()
        res = self._run("--dry-run")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("DRY-RUN", res.stdout)
        self.assertIn("gateway.bak.", res.stdout)        # shows backup path
        with open(drifted) as fh:
            self.assertEqual(fh.read(), before, "dry-run modified production")
        self.assertEqual(self._backups(self.jup), [], "dry-run created a backup")
        self.assertEqual(self._backups(self.uran), [])

    # -- deploy ----------------------------------------------------------
    def test_deploy_syncs_creates_backups_and_spares_env(self):
        drifted = self._drift_jupiter()
        res = self._run()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        # Drift gone: production app.py matches the repo again.
        with open(os.path.join(self.repo, "src", "gateway", "app.py")) as fh:
            repo_app = fh.read()
        with open(drifted) as fh:
            self.assertEqual(fh.read(), repo_app)
        # Timestamped backups exist and preserve the pre-deploy (drifted) code.
        jb = self._backups(self.jup)
        self.assertEqual(len(jb), 1, res.stdout)
        self.assertEqual(len(self._backups(self.uran)), 1)
        with open(os.path.join(self.jup, jb[0], "app.py")) as fh:
            self.assertIn("hotfix-made-directly-on-vps", fh.read())
        # Env files (secrets) are byte-identical — never touched.
        for root in (self.jup, self.uran):
            with open(os.path.join(root, "agent.env")) as fh:
                self.assertEqual(fh.read(), SECRET_ENV)
        # Post-deploy verification reports PASS.
        self.assertIn("Status: PASS, production matches repo", res.stdout)

    def test_deploy_refuses_dirty_tree_unless_allow_dirty(self):
        drifted = self._drift_jupiter()
        # Dirty the *repo* working tree (uncommitted change).
        with open(os.path.join(self.repo, "src", "gateway", "config.py"), "a") as fh:
            fh.write("\n# uncommitted\n")
        res = self._run()
        self.assertNotEqual(res.returncode, 0, res.stdout)
        self.assertIn("dirty", (res.stdout + res.stderr).lower())
        self.assertEqual(self._backups(self.jup), [], "refused deploy must not touch production")
        with open(drifted) as fh:
            self.assertIn("hotfix-made-directly-on-vps", fh.read())
        # With --allow-dirty the same deploy proceeds.
        res = self._run("--allow-dirty")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual(len(self._backups(self.jup)), 1)


if __name__ == "__main__":
    unittest.main()
