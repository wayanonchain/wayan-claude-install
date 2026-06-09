"""Repository-layout tests for the Day 2 orchestration layer.

Filesystem assertions only; runs in the same unittest suite:

    python -m unittest discover -s tests
"""
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORCH = os.path.join(REPO, "orchestration")

REQUIRED_FILES = [
    "README.md",
    "rules/README.md",
    "rules/safety.md",
    "rules/skill-routing.md",
    "rules/services-map.md",
    "learnings/README.md",
    "learnings/inbox/.gitkeep",
    "learnings/reviewed/.gitkeep",
    "memory/README.md",
    "memory/hot.md",
    "memory/warm.md",
    "memory/cold.md",
    "mapping/README.md",
    "mapping/infrastructure.md",
    "mapping/services.md",
    "mapping/accounts.example.md",
    "skill-lab/README.md",
    "skill-lab/proposals/.gitkeep",
]


class OrchestrationLayoutTests(unittest.TestCase):
    def test_required_files_exist(self):
        for rel in REQUIRED_FILES:
            self.assertTrue(os.path.isfile(os.path.join(ORCH, rel)),
                            f"missing orchestration file: {rel}")

    def test_doc_exists(self):
        self.assertTrue(
            os.path.isfile(os.path.join(REPO, "docs", "DAY2_ORCHESTRATION.md")))

    def test_installer_copies_orchestration(self):
        with open(os.path.join(REPO, "install.sh"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("deploy_orchestration", src)
        self.assertIn("/orchestration", src)
        # no-clobber copy must be used (cp -rn)
        self.assertIn("cp -rn", src)

    def test_templates_contain_day2_section(self):
        for agent in ("jupiter", "uran"):
            path = os.path.join(REPO, "templates", agent, "CLAUDE.md")
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            self.assertIn("## Day 2 Orchestration", body, agent)
            self.assertIn("orchestration/learnings/inbox", body, agent)

    def test_accounts_real_file_is_gitignored(self):
        with open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as fh:
            ignore = fh.read()
        self.assertIn("accounts.md", ignore)
        # the example template must still be tracked (present in repo)
        self.assertTrue(os.path.isfile(
            os.path.join(ORCH, "mapping", "accounts.example.md")))


if __name__ == "__main__":
    unittest.main()
