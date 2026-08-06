"""Contract tests for the files that make the repository reviewable on GitHub."""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_public_collaboration_files_are_present() -> None:
    required_paths = (
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".github/dependabot.yml",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
    )

    missing = [path for path in required_paths if not (REPOSITORY_ROOT / path).is_file()]
    assert not missing, f"Missing public collaboration files: {missing}"


def test_ci_runs_every_local_quality_gate_without_credentials() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    required_commands = (
        "npm ci",
        "npx openspec validate --all",
        "npm run contracts:typecheck",
        "npm run frontend:typecheck",
        "npm run frontend:test",
        "npm run frontend:build",
        "uv sync --frozen --dev",
        "uv run ruff check .",
        "uv run pyright",
        "uv run pytest",
    )

    assert all(command in workflow for command in required_commands)
    assert "secrets." not in workflow
    assert "ci-placeholder-not-a-secret" in workflow
    assert "mkdir -p apps/backend/var" in workflow
    assert "contents: read" in workflow


def test_public_metadata_does_not_request_credentials() -> None:
    public_metadata = (
        REPOSITORY_ROOT / "CONTRIBUTING.md",
        REPOSITORY_ROOT / "SECURITY.md",
        REPOSITORY_ROOT / ".github/pull_request_template.md",
        REPOSITORY_ROOT / ".github/ISSUE_TEMPLATE/bug_report.yml",
        REPOSITORY_ROOT / ".github/ISSUE_TEMPLATE/feature_request.yml",
    )
    forbidden_requests = ("粘贴密码", "粘贴密钥", "paste your password", "paste your api key")

    for path in public_metadata:
        content = path.read_text(encoding="utf-8").lower()
        assert not any(value in content for value in forbidden_requests), path


def test_readme_has_reviewable_project_story_and_valid_local_links() -> None:
    readme_path = REPOSITORY_ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    required_sections = (
        "## 为什么做这个项目",
        "## 已实现能力",
        "## 架构",
        "## 可演示链路",
        "## 快速开始",
        "## 验证",
        "## 安全边界",
        "## 当前限制与路线图",
    )

    assert all(section in readme for section in required_sections)
    assert "下一阶段计划（尚未实现）" in readme
    assert "docs/architecture.en.md" in readme
    _assert_local_markdown_links_exist(readme_path)
    _assert_local_markdown_links_exist(REPOSITORY_ROOT / "docs/architecture.en.md")


def _assert_local_markdown_links_exist(document: Path) -> None:
    content = document.read_text(encoding="utf-8")
    for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", content):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        relative_path = target.split("#", maxsplit=1)[0]
        assert (document.parent / relative_path).resolve().exists(), (
            f"Broken local link in {document.relative_to(REPOSITORY_ROOT)}: {target}"
        )
