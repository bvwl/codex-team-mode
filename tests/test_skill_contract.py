from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class TeamModeSkillContractTests(unittest.TestCase):
    def test_dispatch_contract_is_operational(self) -> None:
        skill = (ROOT / "skills" / "team-mode" / "SKILL.md").read_text(encoding="utf-8")
        for label in ("Outcome", "Benefit", "Sources", "Scope", "Checks", "Stop when", "Return"):
            with self.subTest(label=label):
                self.assertIn(f"`{label}`", skill)
        for label in ("Unresolved risk", "Evidence", "Checks already passed", "Do not repeat"):
            with self.subTest(label=label):
                self.assertIn(f"`{label}`", skill)
        self.assertIn("usable partial verdict", skill)
        self.assertIn("children never spawn descendants", skill)
        self.assertIn("request a partial verdict once, then interrupt it", skill)
        self.assertIn("`Executor`（Luna High）", skill)
        self.assertIn("`Complex Executor`（Terra High）", skill)
        self.assertIn("Main thread: keep the critical slice", skill)
        self.assertIn("`Reviewer`（Sol High）", skill)

    def test_agent_type_dispatch_gate_is_explicit(self) -> None:
        skill = (ROOT / "skills" / "team-mode" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Dispatch Gate", skill)
        self.assertIn("Every `spawn_agent` call must explicitly pass `agent_type`", skill)
        self.assertIn("Never omit `agent_type` and never pass `default`", skill)
        self.assertIn("`default` profile is a fail-closed dispatch guard", skill)
        self.assertIn("only time Team Mode deliberately omits `agent_type`", skill)
        self.assertIn("## One-Time Onboarding", skill)
        self.assertIn("Do not inspect Agent files", skill)
        self.assertIn("skip onboarding without mentioning it", skill)

    def test_custom_agent_reference_matches_current_runtime_contract(self) -> None:
        reference = (ROOT / "skills" / "team-mode" / "references" / "custom-agents.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Use capability detection, not a remembered minimum Codex version", reference)
        self.assertIn("real `spawn_agent` input schema", reference)
        self.assertIn("require the field to select all four working profile names", reference)
        self.assertIn("max_depth = 1", reference)
        self.assertIn("actual runtime trace", reference)
        self.assertIn("four working profiles plus one fail-closed `default` guard", reference)
        self.assertIn("gpt-5.6-terra", reference)
        self.assertIn("## Run Onboarding Once", reference)
        self.assertIn("DISPATCH BLOCKED", reference)
        self.assertIn("## Explain How To Disable The Guard", reference)
        self.assertIn("~/.codex/agents-disabled/default.toml", reference)
        self.assertIn("[profiles.json](profiles.json)", reference)
        self.assertIn("scripts/manage_profiles.py", reference)
        self.assertNotIn("features enable multi_agent_v2", reference)

    def test_usage_guidance_includes_runtime_routing_audit(self) -> None:
        skill = (ROOT / "skills" / "team-mode" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`--audit-routing`", skill)
        self.assertIn("[references/profiles.json](references/profiles.json)", skill)
        self.assertIn("each `session_summary` as one runtime session", skill)
        self.assertIn("python3 skills/team-mode/scripts/usage_by_model.py", skill)
        self.assertIn("resolve the bundled script relative to this `SKILL.md`", skill)
        self.assertIn("do not require a binary named exactly `python3.11`", skill)

    def test_readmes_document_python_and_safe_profile_preflight(self) -> None:
        for filename in ("README.md", "README.zh-CN.md"):
            with self.subTest(filename=filename):
                readme = (ROOT / filename).read_text(encoding="utf-8")
                self.assertIn("Python 3.11", readme)
                self.assertIn("scripts/manage_profiles.py --scope project", readme)
                self.assertIn("--audit-routing", readme)
                self.assertNotIn("python3.11 scripts/", readme)
                self.assertIn("bvwl/codex-team-mode", readme)
                self.assertIn("docs/PROJECT_INTEGRATION.zh-CN.md", readme)

    def test_project_integration_guide_covers_install_verify_and_usage(self) -> None:
        guide = (ROOT / "docs" / "PROJECT_INTEGRATION.zh-CN.md").read_text(encoding="utf-8")
        for heading in (
            "## 自然语言接入流程：从 GitHub 到开始提需求",
            "## 高级方式：从本地仓库一次性接入",
            "## 为目标项目生成 AGENTS.md",
            "## 重启后验证 Skill 和 Agent",
            "## 全栈开发提示词",
            "## 逆向分析提示词",
            "## 更新已接入的 Team Mode",
            "## 故障排查",
            "## 最终检查清单",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, guide)
        self.assertIn(".agents/skills/team-mode", guide)
        self.assertIn(".codex/agents", guide)
        self.assertIn("manage_profiles.py", guide)
        self.assertIn("--audit-routing", guide)
        self.assertIn("https://github.com/bvwl/codex-team-mode", guide)
        self.assertIn("## 兼容性与能力预检", guide)
        self.assertIn("EXPECTED_TEAM_MODE_COMMIT", guide)
        self.assertIn("UV_PROJECT_DIR", guide)
        self.assertIn("UV_BIN", guide)
        self.assertIn("多数项目可以由 uv 解析为 Python 3.14", guide)
        self.assertIn("uv python install 3.14", guide)
        self.assertIn("uv init myproject", guide)
        self.assertIn("uv python pin 3.14", guide)
        self.assertIn("uv venv", guide)
        self.assertIn("uv add --dev <package>", guide)
        self.assertIn("不手工编辑 `uv.lock`", guide)
        self.assertIn("不运行 uv sync、uv lock、uv python install", guide)
        self.assertIn("不要回退到无关的系统 Python", guide)
        self.assertIn("第 1 步：让 Codex 从 GitHub 准备并审阅来源", guide)
        self.assertIn("PROJECT_ROOT 的同级目录 codex-team-mode-source", guide)
        self.assertIn("不扫描、搜索或列出其他用户目录", guide)
        self.assertIn("不存在：我授权你只在这个精确路径执行一次 git clone", guide)
        self.assertIn("如果任何一项是“未指定”或“未检查”", guide)
        self.assertIn("真正需要用户作出的安全决定只有一项", guide)
        self.assertIn("第 2 步：确认 commit，只安装四个工作 Profile", guide)
        self.assertIn("第 4 步：安装 `default` 哨兵和 Team Mode Skill", guide)
        self.assertIn("第 6 步：让 Team Mode 先分析现有项目", guide)
        self.assertIn("第 7 步：用自然语言提出真正的开发需求", guide)
        self.assertIn("不安装 default.toml", guide)
        self.assertIn("不得把尖括号占位符原样发送", guide)
        self.assertIn("显式自定义 Profile 选择契约", guide)
        self.assertIn("执行统一写入门禁", guide)
        self.assertIn("最后一次性汇总全部阻塞项", guide)
        self.assertIn("git status --porcelain=v1 --untracked-files=all 必须为空", guide)
        self.assertIn("git ls-files --others --ignored --exclude-standard", guide)
        self.assertIn("当前任务暴露的工具 Schema", guide)
        self.assertIn("导入 sys、argparse、json、pathlib 和 tomllib", guide)
        self.assertIn("使用 lstat 语义", guide)
        self.assertIn("普通文件的 SHA-256", guide)
        self.assertIn("### 安装中途失败或只完成一部分", guide)
        self.assertIn("本提示词不自动创建 AGENTS.md", guide)
        self.assertIn("$CODEX_HOME/sessions", guide)
        self.assertIn("操作系统级只读容器/沙箱", guide)
        self.assertNotIn("/Users/", guide)
        self.assertNotIn("python3.11 scripts/", guide)


if __name__ == "__main__":
    unittest.main()
