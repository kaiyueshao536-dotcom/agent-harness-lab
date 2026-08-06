from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from super_ai.cli import cls_logs as script
from super_ai.cls_ingestion import (
    ClsIngestionService,
    ClsIngestionSettings,
    ClsUploadResult,
)


def _settings() -> ClsIngestionSettings:
    return ClsIngestionSettings(
        endpoint="https://ap-guangzhou.cls.tencentcs.com",
        region="ap-guangzhou",
        logset_id="logset-id",
        topic_id="topic-12345678",
        secret_id="must-not-print-id",
        secret_key="must-not-print-key",
        environment="test",
        max_count=100,
    )


def test_parse_args_supports_explicit_dry_run() -> None:
    args = script.parse_args(["--profile", "quant", "--count", "3", "--dry-run"])

    assert args.profile == "quant"
    assert args.count == 3
    assert args.dry_run is True


def test_java_profile_rejects_count() -> None:
    with pytest.raises(SystemExit, match="only supported"):
        script.generate_logs(
            script.ScriptArguments(
                profile="java-ecommerce",
                count=3,
                dry_run=True,
                config=None,
            ),
            _settings(),
        )


def test_dry_run_does_not_create_client(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def load_settings(_path: Path | str | None) -> ClsIngestionSettings:
        return _settings()

    monkeypatch.setattr(script, "load_cls_ingestion_settings", load_settings)

    def fail_if_client_is_created(_path: Path | str | None) -> ClsIngestionService:
        raise AssertionError("dry-run must not create a CLS client")

    monkeypatch.setattr(script, "create_cls_ingestion_service", fail_if_client_is_created)

    script.main(["--profile", "java-ecommerce", "--dry-run"])

    summary = cast(dict[str, object], json.loads(capsys.readouterr().out))
    assert summary["mode"] == "dry-run"
    assert summary["count"] == 10
    assert summary["ingestionMethod"] == "python-sdk"
    output = json.dumps(summary).lower()
    assert "must-not-print-id" not in output
    assert "must-not-print-key" not in output


def test_upload_prints_safe_result(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def load_settings(_path: Path | str | None) -> ClsIngestionSettings:
        return _settings()

    monkeypatch.setattr(script, "load_cls_ingestion_settings", load_settings)

    class _Service:
        def upload(
            self,
            records: object,
            *,
            filename: str,
            source: str,
        ) -> ClsUploadResult:
            assert len(cast(list[object], records)) == 10
            return ClsUploadResult(
                topic_id="topic-12345678",
                region="ap-guangzhou",
                count=10,
                filename=filename,
                source=source,
                request_id="request-123",
            )

    def create_service(_path: Path | str | None) -> ClsIngestionService:
        return cast(ClsIngestionService, _Service())

    monkeypatch.setattr(script, "create_cls_ingestion_service", create_service)

    script.main(["--profile", "java-ecommerce"])

    summary = cast(dict[str, object], json.loads(capsys.readouterr().out))
    assert summary["mode"] == "uploaded"
    assert summary["count"] == 10
    assert summary["topic"] == "topi…5678"
    assert summary["requestId"] == "request-123"
