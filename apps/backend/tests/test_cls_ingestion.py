from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pytest

from super_ai.cls_ingestion import (
    ClsIngestionError,
    ClsIngestionService,
    ClsIngestionSettings,
    load_cls_ingestion_settings,
    prepare_cls_batch,
)


class _Response:
    def get_request_id(self) -> str:
        return "request-123"


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def put_log_raw(self, topic_id: str, log_group_list: object) -> object:
        self.calls.append((topic_id, log_group_list))
        return _Response()


def _settings(*, max_count: int = 10) -> ClsIngestionSettings:
    return ClsIngestionSettings(
        endpoint="https://ap-guangzhou.cls.tencentcs.com",
        region="ap-guangzhou",
        logset_id="logset-id",
        topic_id="topic-id",
        secret_id="secret-id",
        secret_key="secret-key",
        environment="test",
        max_count=max_count,
    )


def test_load_settings_uses_merged_project_configuration(tmp_path: Path) -> None:
    config_path = tmp_path / "project.json"
    user_path = tmp_path / "user.project.json"
    config_path.write_text(
        json.dumps(
            {
                "app": {"env": "development"},
                "clsMcpServer": {"secretId": "", "secretKey": ""},
                "clsLogUpload": {
                    "endpoint": "https://ap-guangzhou.cls.tencentcs.com",
                    "region": "",
                    "logsetId": "",
                    "topicId": "",
                    "maxCount": 100,
                },
            }
        ),
        encoding="utf-8",
    )
    user_path.write_text(
        json.dumps(
            {
                "clsMcpServer": {
                    "secretId": "configured-id",
                    "secretKey": "configured-key",
                },
                "clsLogUpload": {
                    "region": "ap-guangzhou",
                    "logsetId": "configured-logset",
                    "topicId": "configured-topic",
                },
            }
        ),
        encoding="utf-8",
    )

    settings = load_cls_ingestion_settings(config_path)

    assert settings.region == "ap-guangzhou"
    assert settings.topic_id == "configured-topic"
    assert settings.secret_id == "configured-id"
    assert settings.max_count == 100


def test_prepare_batch_adds_queryable_provenance() -> None:
    prepared = prepare_cls_batch(
        _settings(),
        [{"service": "payment-service", "level": "ERROR", "latency_ms": 1200}],
        filename="business.jsonl",
        source="10.0.0.8",
        timestamp=datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc),
    )

    groups = cast(Any, prepared.log_group_list)
    group = groups.logGroupList[0]
    log = group.logs[0]
    fields = {
        str(content.key): str(content.value)
        for content in log.contents
    }

    assert prepared.count == 1
    assert group.filename == "business.jsonl"
    assert group.source == "10.0.0.8"
    assert fields["region"] == "ap-guangzhou"
    assert fields["environment"] == "test"
    assert fields["ingestion_method"] == "python-sdk"
    assert fields["host"] == "10.0.0.8"
    assert fields["latency_ms"] == "1200"


@pytest.mark.parametrize(
    "field_name",
    ["secretId", "secret_key", "password", "authorization", "access_token"],
)
def test_sensitive_field_is_rejected_before_upload(field_name: str) -> None:
    client = _FakeClient()
    service = ClsIngestionService(settings=_settings(), client=client)

    with pytest.raises(ClsIngestionError, match="Sensitive CLS log field"):
        service.upload(
            [{"message": "safe", field_name: "must-not-leave-process"}],
            filename="business.jsonl",
            source="127.0.0.1",
        )

    assert client.calls == []


def test_oversized_batch_is_rejected_before_upload() -> None:
    client = _FakeClient()
    service = ClsIngestionService(settings=_settings(max_count=1), client=client)

    with pytest.raises(ClsIngestionError, match="maximum is 1"):
        service.upload(
            [{"event": "one"}, {"event": "two"}],
            filename="business.jsonl",
            source="127.0.0.1",
        )

    assert client.calls == []


def test_upload_calls_injected_client_and_returns_safe_summary() -> None:
    client = _FakeClient()
    service = ClsIngestionService(settings=_settings(), client=client)

    result = service.upload(
        [{"event": "checkout_failed", "service": "order-service"}],
        filename="business.jsonl",
        source="127.0.0.1",
    )

    assert len(client.calls) == 1
    assert client.calls[0][0] == "topic-id"
    assert result.count == 1
    assert result.request_id == "request-123"
    assert result.region == "ap-guangzhou"
