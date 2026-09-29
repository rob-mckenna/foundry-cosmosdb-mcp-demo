import pytest

from foundry_cosmos_demo.config import SeederSettings, SettingsError


def test_settings_load_and_normalize_base_url() -> None:
    settings = SeederSettings.from_mapping(
        {
            "AZURE_COSMOSDB_ENDPOINT": "https://example.documents.azure.com:443/",
            "AZURE_COSMOSDB_DATABASE_NAME": "care-guidance",
            "AZURE_COSMOSDB_CONTAINER_NAME": "guidance",
            "AZURE_OPENAI_BASE_URL": "https://demo.openai.azure.com/openai/v1",
        }
    )

    assert settings.azure_openai_base_url == "https://demo.openai.azure.com/openai/v1/"
    assert settings.azure_openai_embedding_deployment == "text-embedding-3-small"
    assert settings.azure_openai_scope == "https://ai.azure.com/.default"
    assert settings.embedding_dimensions == 1536


def test_settings_accept_explicit_openai_base_url() -> None:
    settings = SeederSettings.from_mapping(
        {
            "AZURE_COSMOSDB_ENDPOINT": "https://example.documents.azure.com:443/",
            "AZURE_COSMOSDB_DATABASE_NAME": "care-guidance",
            "AZURE_COSMOSDB_CONTAINER_NAME": "guidance",
            "AZURE_OPENAI_BASE_URL": "https://demo.openai.azure.com/openai/v1",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
            "AZURE_OPENAI_EMBEDDING_DIMENSIONS": "1536",
        }
    )

    assert settings.azure_openai_base_url == "https://demo.openai.azure.com/openai/v1/"
    assert settings.azure_openai_embedding_deployment == "text-embedding-3-small"
    assert settings.embedding_dimensions == 1536


def test_settings_require_expected_dimensions() -> None:
    with pytest.raises(SettingsError):
        SeederSettings.from_mapping(
            {
                "AZURE_COSMOSDB_ENDPOINT": "https://example.documents.azure.com:443/",
                "AZURE_COSMOSDB_DATABASE_NAME": "care-guidance",
                "AZURE_COSMOSDB_CONTAINER_NAME": "guidance",
                "AZURE_OPENAI_BASE_URL": "https://demo.openai.azure.com/openai/v1/",
                "EMBEDDING_DIMENSIONS": "3072",
            }
        )


def test_settings_fail_when_required_values_are_missing() -> None:
    with pytest.raises(SettingsError) as error:
        SeederSettings.from_mapping({})

    assert "AZURE_COSMOSDB_ENDPOINT" in str(error.value)
    assert "AZURE_OPENAI_BASE_URL" in str(error.value)
