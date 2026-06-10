"""Tests for the role-based agent permission profile templates.

Filesystem + JSON assertions; runs in the same unittest suite.
"""
import json
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MEMORY_TOOLS = [
    "mcp__plugin_openviking-memory_openviking-memory__memory_health",
    "mcp__plugin_openviking-memory_openviking-memory__memory_store",
    "mcp__plugin_openviking-memory_openviking-memory__memory_recall",
    "mcp__plugin_openviking-memory_openviking-memory__memory_forget",
]
READ_ONLY_DIAG = [
    "Bash(systemctl status:*)", "Bash(journalctl:*)", "Bash(df:*)",
    "Bash(free:*)", "Bash(ps:*)", "Bash(ls:*)", "Bash(cat:*)",
    "Bash(find:*)", "Bash(grep:*)",
]
GATED = [
    "Bash(git push:*)", "Bash(rm:*)", "Bash(reboot:*)", "Bash(shutdown:*)",
]


def load(agent):
    p = os.path.join(REPO, "templates", agent, "claude-settings.json")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


class PermissionTemplateTests(unittest.TestCase):
    def test_templates_exist_and_valid(self):
        for agent in ("jupiter", "uran"):
            d = load(agent)
            self.assertIn("permissions", d)
            for k in ("allow", "ask", "deny"):
                self.assertIsInstance(d["permissions"][k], list, f"{agent}.{k}")

    def test_memory_tools_allow_listed(self):
        for agent in ("jupiter", "uran"):
            allow = load(agent)["permissions"]["allow"]
            for t in MEMORY_TOOLS:
                self.assertIn(t, allow, f"{agent} missing {t}")

    def test_read_only_diagnostics_allowed(self):
        for agent in ("jupiter", "uran"):
            allow = load(agent)["permissions"]["allow"]
            for d in READ_ONLY_DIAG:
                self.assertIn(d, allow, f"{agent} missing diag {d}")

    def test_dangerous_ops_gated_not_allowed(self):
        for agent in ("jupiter", "uran"):
            perms = load(agent)["permissions"]
            for g in GATED:
                self.assertIn(g, perms["ask"], f"{agent} {g} should be in ask")
                self.assertNotIn(g, perms["allow"], f"{agent} {g} must NOT be allowed")

    def test_no_self_edit_deny_rules(self):
        for agent in ("jupiter", "uran"):
            deny = load(agent)["permissions"]["deny"]
            base = f"/home/wayan/.claude-lab/{agent}"
            for target in ("CLAUDE.md", "orchestration/rules/**",
                           "orchestration/memory/**", "orchestration/mapping/**",
                           "skills/**"):
                self.assertTrue(
                    any(target in r and r.startswith("Edit(") for r in deny),
                    f"{agent} missing Edit deny for {target}")
                self.assertTrue(
                    any(target in r and r.startswith("Write(") for r in deny),
                    f"{agent} missing Write deny for {target}")

    def test_uran_extra_safe_ops_and_no_broad_sudo(self):
        u = load("uran")["permissions"]
        self.assertIn("Bash(sudo systemctl restart wayan-jupiter.service)", u["allow"])
        self.assertIn("Bash(docker compose restart openviking:*)", u["allow"])
        # broad sudo must NOT be in ask (it would shadow the specific sudo allows)
        self.assertNotIn("Bash(sudo:*)", u["ask"])

    def test_jupiter_gates_broad_sudo(self):
        j = load("jupiter")["permissions"]
        self.assertIn("Bash(sudo:*)", j["ask"])  # Jupiter has no sudo allows to shadow

    def test_installer_and_apply_deploy_settings(self):
        with open(os.path.join(REPO, "install.sh"), encoding="utf-8") as fh:
            inst = fh.read()
        self.assertIn("deploy_agent_settings", inst)
        self.assertIn("claude-settings.json", inst)
        self.assertIn(".claude/settings.json", inst)
        with open(os.path.join(REPO, "scripts", "apply-templates.sh"),
                  encoding="utf-8") as fh:
            ap = fh.read()
        self.assertIn("apply_settings", ap)
        self.assertIn("claude-settings.json", ap)


if __name__ == "__main__":
    unittest.main()
