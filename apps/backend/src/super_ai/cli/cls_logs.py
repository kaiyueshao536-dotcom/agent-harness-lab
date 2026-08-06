"""Generate safe e-commerce incident logs for Tencent Cloud CLS."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from super_ai.aiops.fixtures import (
    generate_java_ecommerce_incident_logs,
    generate_quant_incident_logs,
)
from super_ai.cls_ingestion import (
    ClsIngestionSettings,
    ClsUploadResult,
    create_cls_ingestion_service,
    load_cls_ingestion_settings,
    prepare_cls_batch,
)
from super_ai.project_config import project_config_section, required_int


@dataclass(frozen=True)
class ScriptArguments:
    profile: Literal["java-ecommerce", "quant"]
    count: int | None
    dry_run: bool
    config: Path | None


def parse_args(argv: Sequence[str] | None = None) -> ScriptArguments:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=("java-ecommerce", "quant"),
        default="java-ecommerce",
    )
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview the batch without creating a CLS client.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional base project JSON path; defaults to the repository config.",
    )
    parsed = parser.parse_args(argv)
    return ScriptArguments(
        profile=parsed.profile,
        count=parsed.count,
        dry_run=parsed.dry_run,
        config=parsed.config,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    settings = load_cls_ingestion_settings(args.config)
    generated_logs, filename = generate_logs(args, settings)
    source = "127.0.0.1"

    if args.dry_run:
        prepared = prepare_cls_batch(
            settings,
            generated_logs,
            filename=filename,
            source=source,
        )
        _print_summary(
            mode="dry-run",
            settings=settings,
            count=prepared.count,
            filename=prepared.filename,
            source=prepared.source,
            field_names=prepared.field_names,
        )
        return

    service = create_cls_ingestion_service(args.config)
    result = service.upload(
        generated_logs,
        filename=filename,
        source=source,
    )
    _print_upload_summary(result)


def generate_logs(
    args: ScriptArguments,
    settings: ClsIngestionSettings,
) -> tuple[list[dict[str, str]], str]:
    if args.profile == "java-ecommerce":
        if args.count is not None:
            raise SystemExit("--count is only supported with --profile quant")
        return (
            generate_java_ecommerce_incident_logs(now=datetime.now(timezone.utc)),
            "java-ecommerce-microservices.log",
        )

    target = project_config_section("clsLogUpload", config_path=args.config)
    count = args.count or required_int(target, "defaultCount")
    if not 1 <= count <= settings.max_count:
        raise SystemExit(f"--count must be between 1 and {settings.max_count}")
    return (
        generate_quant_incident_logs(
            count=count,
            now=datetime.now(timezone.utc),
        ),
        "ecommerce-quant-risk-service.log",
    )


def _print_upload_summary(result: ClsUploadResult) -> None:
    _print_summary(
        mode="uploaded",
        settings=None,
        count=result.count,
        filename=result.filename,
        source=result.source,
        region=result.region,
        topic_id=result.topic_id,
        request_id=result.request_id,
    )


def _print_summary(
    *,
    mode: str,
    settings: ClsIngestionSettings | None,
    count: int,
    filename: str,
    source: str,
    field_names: tuple[str, ...] = (),
    region: str | None = None,
    topic_id: str | None = None,
    request_id: str | None = None,
) -> None:
    resolved_region = region or (settings.region if settings is not None else "")
    resolved_topic = topic_id or (settings.topic_id if settings is not None else "")
    summary = {
        "mode": mode,
        "count": count,
        "region": resolved_region,
        "topic": _masked_topic_id(resolved_topic),
        "filename": filename,
        "source": source,
        "ingestionMethod": "python-sdk",
        "fieldNames": list(field_names),
        "requestId": request_id,
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


def _masked_topic_id(topic_id: str) -> str:
    if len(topic_id) <= 8:
        return topic_id
    return f"{topic_id[:4]}…{topic_id[-4:]}"


if __name__ == "__main__":
    main()
