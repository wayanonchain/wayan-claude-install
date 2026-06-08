"""Repository-layout tests for the skills system.

Language-agnostic (just filesystem assertions), runs in the same unittest suite:

    python -m unittest discover -s tests
"""
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_SKILLS = [
    "onchain-alpha",
    "content-engine",
    "file-analyst",
    "server-ops",
    "security-check",
    "agent-reviewer",
]


class SkillsLayoutTests(unittest.TestCase):
    def test_skills_readme(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO, "skills", "README.md")))

    def test_required_skill_files_exist(self):
        for name in REQUIRED_SKILLS:
            path = os.path.join(REPO, "skills", name, "SKILL.md")
            self.assertTrue(os.path.isfile(path), f"missing skill: {path}")

    def test_proposals_dir_exists(self):
        self.assertTrue(
            os.path.isfile(os.path.join(REPO, "skills", "_proposals", "README.md")))

    def test_logs_dirs_exist(self):
        for d in ("successful", "failed"):
            self.assertTrue(os.path.isdir(os.path.join(REPO, "logs", d)),
                            f"missing logs/{d}")

    def test_installer_deploys_skills_and_logs(self):
        with open(os.path.join(REPO, "install.sh"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("deploy_skills", src)
        self.assertIn("/skills", src)
        self.assertIn("logs/successful", src)
        self.assertIn("logs/failed", src)

    def test_templates_mention_skills_and_proposals(self):
        for agent in ("jupiter", "uran"):
            path = os.path.join(REPO, "templates", agent, "CLAUDE.md")
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            self.assertIn("skills/", body, agent)
            self.assertIn("_proposals", body, agent)


if __name__ == "__main__":
    unittest.main()
