from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import os


class SettingsError(ValueError):
    """Raised when required seeder configuration is missing or invalid."""


def _first_non_empty(values: Mapping[str, str], *keys: str) -> str | None:
    for key in keys:
        value = values.get(key)
        if value:
            return value
    return None


@dataclass(frozen=True)
class SeederSettings:
    """Runtime configuration for the synthetic data seeder."""

    cosmos_endpoint: str
    cosmos_database_name: str
    cosmos_container_name: str
    azure_openai_base_url: str
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_openai_scope: str = "https://ai.azure.com/.default"
    embedding_dimensions: int = 1536
    document_count: int = 1024

    @classmethod
    def from_env(cls) -> "SeederSettings":
        return cls.from_mapping(os.environ)

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> "SeederSettings":
        cosmos_endpoint = _first_non_empty(values, "AZURE_COSMOSDB_ENDPOINT")
        cosmos_database_name = _first_non_empty(values, "AZURE_COSMOSDB_DATABASE_NAME")
        cosmos_container_name = _first_non_empty(values, "AZURE_COSMOSDB_CONTAINER_NAME")
        openai_base_url = _first_non_empty(values, "AZURE_OPENAI_BASE_URL")

        missing = []
        if not cosmos_endpoint:
            missing.append("AZURE_COSMOSDB_ENDPOINT")
        if not cosmos_database_name:
            missing.append("AZURE_COSMOSDB_DATABASE_NAME")
        if not cosmos_container_name:
            missing.append("AZURE_COSMOSDB_CONTAINER_NAME")
        if not openai_base_url:
            missing.append("AZURE_OPENAI_BASE_URL")
        if missing:
            raise SettingsError(
                "Missing required environment variables: " + ", ".join(sorted(missing))
            )

        document_count = int(values.get("SEED_DOCUMENT_COUNT", "1024"))
        embedding_dimensions = int(
            _first_non_empty(
                values,
                "EMBEDDING_DIMENSIONS",
                "AZURE_OPENAI_EMBEDDING_DIMENSIONS",
            )
            or "1536"
        )
        if document_count <= 0:
            raise SettingsError("SEED_DOCUMENT_COUNT must be a positive integer.")
        if embedding_dimensions != 1536:
            raise SettingsError(
                "This demo expects text-embedding-3-small to return 1536-dimensional vectors."
            )

        # The seeder expects the OpenAI-compatible Foundry deployment base URL, typically
        # https://<custom-subdomain>.openai.azure.com/openai/v1/.
        base_url = openai_base_url.rstrip("/") + "/"

        return cls(
            cosmos_endpoint=cosmos_endpoint,
            cosmos_database_name=cosmos_database_name,
            cosmos_container_name=cosmos_container_name,
            azure_openai_base_url=base_url,
            azure_openai_embedding_deployment=(
                _first_non_empty(
                    values,
                    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
                    "EMBEDDING_DEPLOYMENT",
                )
                or "text-embedding-3-small"
            ),
            azure_openai_scope=values.get(
                "AZURE_OPENAI_SCOPE", "https://ai.azure.com/.default"
            ),
            embedding_dimensions=embedding_dimensions,
            document_count=document_count,
        )
