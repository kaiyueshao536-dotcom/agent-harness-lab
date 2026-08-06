import json
from pathlib import Path

from super_ai.project_config import load_project_config

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_local_project_configs_are_ignored_and_templates_are_sanitized() -> None:
    ignore_patterns = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "config/project.json" in ignore_patterns
    assert "config/user.project.json" in ignore_patterns

    base_template = json.loads(
        (REPO_ROOT / "config/project.template.json").read_text(encoding="utf-8")
    )
    user_template = json.loads(
        (REPO_ROOT / "config/user.project.template.json").read_text(encoding="utf-8")
    )

    assert base_template["llm"]["apiKey"] == ""
    assert base_template["clsMcpServer"]["secretId"] == ""
    assert base_template["clsMcpServer"]["secretKey"] == ""
    assert base_template["prometheusAlerts"]["sources"][0]["password"] == ""
    assert base_template["aiopsDemo"]["password"] == ""
    assert base_template["minio"]["accessKey"] == ""
    assert base_template["minio"]["secretKey"] == ""
    assert user_template["llm"]["apiKey"] == ""
    assert user_template["clsMcpServer"]["secretId"] == ""
    assert user_template["clsMcpServer"]["secretKey"] == ""


def test_project_config_merges_an_untracked_user_override(tmp_path: Path) -> None:
    base_config = json.loads(
        (REPO_ROOT / "config/project.template.json").read_text(encoding="utf-8")
    )
    user_config = json.loads(
        (REPO_ROOT / "config/user.project.template.json").read_text(encoding="utf-8")
    )
    user_config["llm"]["apiKey"] = "test-api-key"
    base_path = tmp_path / "project.json"
    user_path = tmp_path / "user.project.json"
    base_path.write_text(json.dumps(base_config), encoding="utf-8")
    user_path.write_text(json.dumps(user_config), encoding="utf-8")

    merged_config = load_project_config(base_path)
    llm = merged_config["llm"]

    assert base_config["llm"]["apiKey"] == ""
    assert base_config["llm"]["chatModel"] == ""
    assert base_config["llm"]["embeddingModel"] == ""
    assert base_config["clsMcpServer"]["secretId"] == ""
    assert base_config["clsMcpServer"]["secretKey"] == ""
    assert base_config["clsLogUpload"]["region"] == ""
    assert base_config["clsLogUpload"]["logsetId"] == ""
    assert base_config["clsLogUpload"]["topicId"] == ""
    assert user_config["llm"]["apiKey"] == "test-api-key"
    assert llm["apiKey"] == "test-api-key"
    assert llm["baseUrl"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert llm["chatModel"] == "qwen3.7-max"
    assert llm["embeddingModel"] == "text-embedding-v4"
    assert llm["embeddingDimensions"] == 1024
    assert llm["rerankModel"] == "qwen3-vl-rerank"
    assert "modelCapabilities" not in base_config["llm"]
    capabilities = user_config["llm"]["modelCapabilities"]
    assert capabilities["qwen3.7-max"]["contextWindowTokens"] == 1_000_000
    assert llm["maxRetries"] == 2


def test_project_template_declares_supported_alert_source_types() -> None:
    config = json.loads(
        (REPO_ROOT / "config/project.template.json").read_text(encoding="utf-8")
    )
    sources = config["prometheusAlerts"]["sources"]

    assert sources[0]["type"] == "prometheus-v1"
    assert sources[0]["alertsApi"] == ""
    assert sources[1]["type"] == "alertmanager-v2"
    assert sources[1]["alertsApi"] == "http://127.0.0.1:9093/api/v2/alerts"
