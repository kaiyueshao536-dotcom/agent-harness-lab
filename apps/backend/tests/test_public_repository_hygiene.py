"""Checks that keep the public repository baseline free of local/private artifacts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_IGNORE_RULES = {
    ".venv/",
    ".python/",
    ".npm-cache/",
    ".uv-cache/",
    "apps/backend/var/",
    "node_modules/",
    "dist/",
    "*.log",
    "*.sqlite3",
    "config/project.json",
    "config/user.project.json",
    "简历/",
    "学习/",
}
FORBIDDEN_TRACKED_PREFIXES = (
    ".npm-cache/",
    ".python/",
    ".uv-cache/",
    "apps/backend/.venv/",
    "apps/backend/var/",
    "apps/frontend/dist/",
    "node_modules/",
    "简历/",
    "学习/",
)
FORBIDDEN_TRACKED_PATHS = {
    "config/project.json",
    "config/user.project.json",
}
ALLOWED_PUBLIC_CREDENTIAL_PLACEHOLDERS: set[str] = set()


def test_public_gitignore_covers_local_and_personal_artifacts() -> None:
    rules = {
        line.strip()
        for line in (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert REQUIRED_IGNORE_RULES <= rules


def test_git_index_excludes_private_paths_when_repository_is_initialized() -> None:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return

    tracked = {
        value.decode("utf-8").replace("\\", "/")
        for value in result.stdout.split(b"\0")
        if value
    }
    assert not (tracked & FORBIDDEN_TRACKED_PATHS)
    assert not any(
        path.startswith(prefix) for path in tracked for prefix in FORBIDDEN_TRACKED_PREFIXES
    )


def test_tracked_configuration_templates_do_not_contain_credentials() -> None:
    for filename in ("project.template.json", "user.project.template.json"):
        payload = cast(
            dict[str, object],
            json.loads((REPOSITORY_ROOT / "config" / filename).read_text(encoding="utf-8")),
        )
        sensitive_values = _sensitive_values(payload)
        assert not sensitive_values, f"{filename} contains credential values at {sensitive_values}"


def _sensitive_values(value: object, path: str = "") -> list[str]:
    if isinstance(value, dict):
        findings: list[str] = []
        for key, item in cast(dict[object, object], value).items():
            key_text = str(key)
            item_path = f"{path}.{key_text}" if path else key_text
            normalized = key_text.replace("-", "_").lower()
            if normalized in {
                "api_key",
                "apikey",
                "secret_id",
                "secretid",
                "secret_key",
                "secretkey",
                "access_token",
                "token",
                "password",
            }:
                if (
                    isinstance(item, str)
                    and item.strip()
                    and item.strip() not in ALLOWED_PUBLIC_CREDENTIAL_PLACEHOLDERS
                ):
                    findings.append(item_path)
                continue
            findings.extend(_sensitive_values(item, item_path))
        return findings
    if isinstance(value, list):
        findings = []
        for index, item in enumerate(cast(list[object], value)):
            findings.extend(_sensitive_values(item, f"{path}[{index}]"))
        return findings
    return []
