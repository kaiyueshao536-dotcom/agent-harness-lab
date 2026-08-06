"""Explicit, secret-safe Tencent Cloud CLS structured log ingestion."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, cast

from tencentcloud.log.cls_pb2 import (  # pyright: ignore[reportMissingTypeStubs]
    LogGroupList,
)
from tencentcloud.log.logclient import (  # pyright: ignore[reportMissingTypeStubs]
    LogClient,
)

from super_ai.project_config import (
    project_config_section,
    required_int,
    required_str,
)

MAX_FIELD_COUNT = 128
MAX_FIELD_NAME_BYTES = 128
MAX_FIELD_VALUE_BYTES = 64 * 1024
INGESTION_METHOD = "python-sdk"
_SENSITIVE_KEYS = {
    "access_token",
    "accesstoken",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "credentials",
    "password",
    "secret",
    "secret_id",
    "secret_key",
    "secretid",
    "secretkey",
    "token",
}


class ClsIngestionError(RuntimeError):
    """Raised before an unsafe or invalid CLS batch can be uploaded."""


class ClsLogClient(Protocol):
    """Minimal boundary used by the ingestion service and its tests."""

    def put_log_raw(self, topic_id: str, log_group_list: object) -> object:
        """Upload one protobuf log group list."""


@dataclass(frozen=True)
class ClsIngestionSettings:
    """Merged project settings required for explicit CLS ingestion."""

    endpoint: str
    region: str
    logset_id: str
    topic_id: str
    secret_id: str
    secret_key: str
    environment: str
    max_count: int


@dataclass(frozen=True)
class PreparedClsBatch:
    """Validated protobuf payload plus non-secret provenance."""

    log_group_list: object
    count: int
    filename: str
    source: str
    field_names: tuple[str, ...]


@dataclass(frozen=True)
class ClsUploadResult:
    """Safe upload result that can be printed or audited."""

    topic_id: str
    region: str
    count: int
    filename: str
    source: str
    request_id: str | None


ClsClientFactory = Callable[[ClsIngestionSettings], ClsLogClient]


def load_cls_ingestion_settings(
    config_path: Path | str | None = None,
) -> ClsIngestionSettings:
    """Load CLS target and credentials from the merged project configuration."""
    target = project_config_section("clsLogUpload", config_path=config_path)
    credentials = project_config_section("clsMcpServer", config_path=config_path)
    app = project_config_section("app", config_path=config_path)
    max_count = required_int(target, "maxCount")
    if max_count < 1:
        raise ClsIngestionError("clsLogUpload.maxCount must be greater than zero.")
    return ClsIngestionSettings(
        endpoint=required_str(target, "endpoint"),
        region=required_str(target, "region"),
        logset_id=required_str(target, "logsetId"),
        topic_id=required_str(target, "topicId"),
        secret_id=required_str(credentials, "secretId"),
        secret_key=required_str(credentials, "secretKey"),
        environment=required_str(app, "env"),
        max_count=max_count,
    )


def create_cls_ingestion_service(
    config_path: Path | str | None = None,
    *,
    client_factory: ClsClientFactory | None = None,
) -> ClsIngestionService:
    """Create a service only when a caller explicitly requests one."""
    settings = load_cls_ingestion_settings(config_path)
    factory = client_factory or _default_client_factory
    return ClsIngestionService(settings=settings, client=factory(settings))


class ClsIngestionService:
    """Validate and upload bounded structured log batches."""

    def __init__(self, *, settings: ClsIngestionSettings, client: ClsLogClient) -> None:
        self._settings = settings
        self._client = client

    @property
    def settings(self) -> ClsIngestionSettings:
        return self._settings

    def prepare(
        self,
        records: Sequence[Mapping[str, object]],
        *,
        filename: str,
        source: str,
        timestamp: datetime | None = None,
    ) -> PreparedClsBatch:
        return prepare_cls_batch(
            self._settings,
            records,
            filename=filename,
            source=source,
            timestamp=timestamp,
        )

    def upload(
        self,
        records: Sequence[Mapping[str, object]],
        *,
        filename: str,
        source: str,
        timestamp: datetime | None = None,
    ) -> ClsUploadResult:
        prepared = self.prepare(
            records,
            filename=filename,
            source=source,
            timestamp=timestamp,
        )
        response = self._client.put_log_raw(
            self._settings.topic_id,
            prepared.log_group_list,
        )
        request_id = _request_id_from_response(response)
        return ClsUploadResult(
            topic_id=self._settings.topic_id,
            region=self._settings.region,
            count=prepared.count,
            filename=prepared.filename,
            source=prepared.source,
            request_id=request_id,
        )


def prepare_cls_batch(
    settings: ClsIngestionSettings,
    records: Sequence[Mapping[str, object]],
    *,
    filename: str,
    source: str,
    timestamp: datetime | None = None,
) -> PreparedClsBatch:
    """Build a protobuf batch after all local validation has succeeded."""
    clean_filename = _required_label(filename, "filename")
    clean_source = _required_label(source, "source")
    if not records:
        raise ClsIngestionError("CLS log batch must contain at least one record.")
    if len(records) > settings.max_count:
        raise ClsIngestionError(
            f"CLS log batch contains {len(records)} records; maximum is {settings.max_count}."
        )

    prepared_records = [
        _prepare_record(
            settings,
            record,
            default_host=clean_source,
        )
        for record in records
    ]
    event_time = timestamp or datetime.now(timezone.utc)
    if event_time.tzinfo is None:
        raise ClsIngestionError("CLS log timestamp must include timezone information.")

    groups = cast(Any, LogGroupList())
    group = groups.logGroupList.add()
    group.filename = clean_filename
    group.source = clean_source
    timestamp_micros = int(event_time.timestamp() * 1_000_000)
    all_field_names: set[str] = set()
    for fields in prepared_records:
        log = group.logs.add()
        log.time = timestamp_micros
        for key, value in fields.items():
            content = log.contents.add()
            content.key = key
            content.value = value
            all_field_names.add(key)

    return PreparedClsBatch(
        log_group_list=groups,
        count=len(prepared_records),
        filename=clean_filename,
        source=clean_source,
        field_names=tuple(sorted(all_field_names)),
    )


def _prepare_record(
    settings: ClsIngestionSettings,
    record: Mapping[str, object],
    *,
    default_host: str,
) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key, value in record.items():
        clean_key = _validate_field_name(key)
        fields[clean_key] = _field_value(clean_key, value)

    host = fields.get("host", "").strip() or default_host
    fields["host"] = host
    fields["region"] = settings.region
    fields["environment"] = settings.environment
    fields["ingestion_method"] = INGESTION_METHOD
    if len(fields) > MAX_FIELD_COUNT:
        raise ClsIngestionError(
            f"CLS log record contains {len(fields)} fields; maximum is {MAX_FIELD_COUNT}."
        )
    return fields


def _validate_field_name(key: object) -> str:
    if not isinstance(key, str) or not key.strip():
        raise ClsIngestionError("CLS log field names must be non-empty strings.")
    clean_key = key.strip()
    if len(clean_key.encode("utf-8")) > MAX_FIELD_NAME_BYTES:
        raise ClsIngestionError(
            f"CLS log field name exceeds {MAX_FIELD_NAME_BYTES} UTF-8 bytes."
        )
    if _is_sensitive_key(clean_key):
        raise ClsIngestionError(f"Sensitive CLS log field is not allowed: {clean_key}")
    return clean_key


def _field_value(key: str, value: object) -> str:
    if value is None:
        encoded = ""
    elif isinstance(value, bool):
        encoded = "true" if value else "false"
    elif isinstance(value, (str, int, float)):
        encoded = str(value)
    else:
        raise ClsIngestionError(
            f"CLS log field values must be scalar; field {key} is {type(value).__name__}."
        )
    if len(encoded.encode("utf-8")) > MAX_FIELD_VALUE_BYTES:
        raise ClsIngestionError(
            f"CLS log field {key} exceeds {MAX_FIELD_VALUE_BYTES} UTF-8 bytes."
        )
    return encoded


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").lower()
    return normalized in _SENSITIVE_KEYS or normalized.endswith(
        ("_key", "_password", "_secret", "_token")
    )


def _required_label(value: str, name: str) -> str:
    clean_value = value.strip()
    if not clean_value:
        raise ClsIngestionError(f"CLS log {name} must be a non-empty string.")
    return clean_value


def _default_client_factory(settings: ClsIngestionSettings) -> ClsLogClient:
    return cast(
        ClsLogClient,
        LogClient(settings.endpoint, settings.secret_id, settings.secret_key),
    )


def _request_id_from_response(response: object) -> str | None:
    getter = getattr(response, "get_request_id", None)
    if not callable(getter):
        return None
    request_id = cast(Any, getter)()
    return str(request_id) if request_id else None
