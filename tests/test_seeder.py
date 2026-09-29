from types import SimpleNamespace

import pytest

from foundry_cosmos_demo.config import SeederSettings, SettingsError
from foundry_cosmos_demo.seeder import (
    apply_cli_overrides,
    generate_embeddings,
    load_settings,
    main,
)


class FakeEmbeddingsApi:
    def __init__(self, dimensions: int) -> None:
        self._dimensions = dimensions

    def create(self, *, model: str, input: list[str]) -> SimpleNamespace:  # noqa: A002
        rows = [
            SimpleNamespace(index=index, embedding=[float(index)] * self._dimensions)
            for index, _ in enumerate(input)
        ]
        return SimpleNamespace(data=rows)


class FakeOpenAIClient:
    def __init__(self, dimensions: int) -> None:
        self.embeddings = FakeEmbeddingsApi(dimensions)


def test_generate_embeddings_preserves_expected_dimensions() -> None:
    client = FakeOpenAIClient(1536)

    embeddings = generate_embeddings(
        client,
        "text-embedding-3-small",
        ["alpha", "beta", "gamma"],
        1536,
        2,
    )

    assert len(embeddings) == 3
    assert all(len(embedding) == 1536 for embedding in embeddings)
    assert embeddings[1][0] == 1.0


def test_apply_cli_overrides_matches_mcp_style_option_names() -> None:
    settings = SeederSettings.from_mapping(
        {
            "AZURE_COSMOSDB_ENDPOINT": "https://example.documents.azure.com:443/",
            "AZURE_COSMOSDB_DATABASE_NAME": "care-guidance",
            "AZURE_COSMOSDB_CONTAINER_NAME": "guidance",
            "AZURE_OPENAI_BASE_URL": "https://demo.openai.azure.com/openai/v1/",
        }
    )
    args = SimpleNamespace(
        count=4,
        openai_endpoint="https://override.openai.azure.com/openai/v1",
        embedding_deployment="text-embedding-3-small",
        embedding_dimensions=1536,
    )

    updated = apply_cli_overrides(settings, args)

    assert updated.document_count == 4
    assert updated.azure_openai_base_url == "https://override.openai.azure.com/openai/v1/"
    assert updated.azure_openai_embedding_deployment == "text-embedding-3-small"


def test_apply_cli_overrides_rejects_non_1536_dimensions() -> None:
    settings = SeederSettings.from_mapping(
        {
            "AZURE_COSMOSDB_ENDPOINT": "https://example.documents.azure.com:443/",
            "AZURE_COSMOSDB_DATABASE_NAME": "care-guidance",
            "AZURE_COSMOSDB_CONTAINER_NAME": "guidance",
            "AZURE_OPENAI_BASE_URL": "https://demo.openai.azure.com/openai/v1/",
        }
    )
    args = SimpleNamespace(
        count=None,
        openai_endpoint=None,
        embedding_deployment=None,
        embedding_dimensions=3072,
    )

    with pytest.raises(ValueError):
        apply_cli_overrides(settings, args)


def test_load_settings_accepts_cli_only_openai_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_COSMOSDB_ENDPOINT", "https://example.documents.azure.com:443/")
    monkeypatch.setenv("AZURE_COSMOSDB_DATABASE_NAME", "care-guidance")
    monkeypatch.setenv("AZURE_COSMOSDB_CONTAINER_NAME", "guidance")
    monkeypatch.delenv("AZURE_OPENAI_BASE_URL", raising=False)

    args = SimpleNamespace(
        count=2,
        openai_endpoint="https://override.openai.azure.com/openai/v1",
        embedding_deployment="text-embedding-3-small",
        embedding_dimensions=1536,
    )

    settings = load_settings(args)

    assert settings.document_count == 2
    assert settings.azure_openai_base_url == "https://override.openai.azure.com/openai/v1/"


def test_dry_run_without_azure_environment_is_preview_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for key in (
        "AZURE_COSMOSDB_ENDPOINT",
        "AZURE_COSMOSDB_DATABASE_NAME",
        "AZURE_COSMOSDB_CONTAINER_NAME",
        "AZURE_OPENAI_BASE_URL",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "EMBEDDING_DEPLOYMENT",
    ):
        monkeypatch.delenv(key, raising=False)

    exit_code = main(["--dry-run", "--count", "2"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Prepared 2 synthetic documents for offline dry-run preview." in captured.out
    assert "offline preview only (no Azure wiring validated)." in captured.out


def test_dry_run_validates_provided_configuration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AZURE_COSMOSDB_ENDPOINT", "https://example.documents.azure.com:443/")
    monkeypatch.setenv("AZURE_COSMOSDB_DATABASE_NAME", "care-guidance")
    monkeypatch.setenv("AZURE_COSMOSDB_CONTAINER_NAME", "guidance")
    monkeypatch.setenv("AZURE_OPENAI_BASE_URL", "https://demo.openai.azure.com/openai/v1/")

    exit_code = main(["--dry-run", "--count", "2"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Prepared 2 synthetic documents for offline dry-run preview." in captured.out
    assert "Validated provided seeder configuration locally without calling Azure services." in captured.out


def test_dry_run_rejects_partial_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_COSMOSDB_ENDPOINT", "https://example.documents.azure.com:443/")
    monkeypatch.delenv("AZURE_COSMOSDB_DATABASE_NAME", raising=False)
    monkeypatch.delenv("AZURE_COSMOSDB_CONTAINER_NAME", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_BASE_URL", raising=False)

    with pytest.raises(SettingsError):
        main(["--dry-run"])
