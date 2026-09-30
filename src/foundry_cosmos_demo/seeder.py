from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Mapping, Sequence
import argparse
import json
import os
import time

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI, RateLimitError

from .config import SeederSettings
from .synthetic_data import build_embedding_inputs, build_synthetic_guidance_documents

_DRY_RUN_CONFIG_ENV_KEYS = (
    "AZURE_COSMOSDB_ENDPOINT",
    "AZURE_COSMOSDB_DATABASE_NAME",
    "AZURE_COSMOSDB_CONTAINER_NAME",
    "AZURE_OPENAI_BASE_URL",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "EMBEDDING_DEPLOYMENT",
)


@dataclass(frozen=True)
class SeedResult:
    document_count: int
    cosmos_endpoint: str
    database_name: str
    container_name: str
    embedding_dimensions: int


def _chunked(values: Sequence[str], batch_size: int) -> Iterable[Sequence[str]]:
    for index in range(0, len(values), batch_size):
        yield values[index : index + batch_size]


def create_embedding_client(
    settings: SeederSettings, credential: DefaultAzureCredential
) -> OpenAI:
    token_provider = get_bearer_token_provider(credential, settings.azure_openai_scope)
    return OpenAI(
        base_url=settings.azure_openai_base_url,
        api_key=token_provider,
    )


def generate_embeddings(
    client: OpenAI,
    deployment_name: str,
    payloads: Sequence[str],
    expected_dimensions: int,
    batch_size: int,
    max_rate_limit_retries: int = 8,
) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for batch in _chunked(payloads, batch_size):
        for attempt in range(max_rate_limit_retries + 1):
            try:
                response = client.embeddings.create(
                    model=deployment_name, input=list(batch)
                )
                break
            except RateLimitError as error:
                if attempt == max_rate_limit_retries:
                    raise
                retry_after = error.response.headers.get("retry-after")
                delay = float(retry_after) if retry_after else min(60.0, 2.0**attempt)
                time.sleep(max(delay, 1.0))
        ordered_rows = sorted(response.data, key=lambda row: row.index)
        for row in ordered_rows:
            if len(row.embedding) != expected_dimensions:
                raise ValueError(
                    f"Expected {expected_dimensions} dimensions, received {len(row.embedding)}."
                )
            embeddings.append(list(row.embedding))
    return embeddings


def seed_documents(
    settings: SeederSettings,
    *,
    dry_run: bool = False,
    batch_size: int = 16,
) -> SeedResult:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    documents = build_synthetic_guidance_documents(settings.document_count)
    embedding_inputs = build_embedding_inputs(documents)

    if dry_run:
        return SeedResult(
            document_count=len(documents),
            cosmos_endpoint=settings.cosmos_endpoint,
            database_name=settings.cosmos_database_name,
            container_name=settings.cosmos_container_name,
            embedding_dimensions=settings.embedding_dimensions,
        )

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    embedding_client = create_embedding_client(settings, credential)
    embeddings = generate_embeddings(
        embedding_client,
        settings.azure_openai_embedding_deployment,
        embedding_inputs,
        settings.embedding_dimensions,
        batch_size,
    )

    with CosmosClient(settings.cosmos_endpoint, credential=credential) as cosmos_client:
        container = (
            cosmos_client.get_database_client(settings.cosmos_database_name)
            .get_container_client(settings.cosmos_container_name)
        )
        for document, embedding in zip(documents, embeddings, strict=True):
            item = dict(document)
            item["embedding"] = embedding
            container.upsert_item(item)

    return SeedResult(
        document_count=len(documents),
        cosmos_endpoint=settings.cosmos_endpoint,
        database_name=settings.cosmos_database_name,
        container_name=settings.cosmos_container_name,
        embedding_dimensions=settings.embedding_dimensions,
    )


def apply_cli_overrides(
    settings: SeederSettings, args: argparse.Namespace
) -> SeederSettings:
    updates = {}
    if args.count is not None:
        updates["document_count"] = args.count
    if args.openai_endpoint:
        updates["azure_openai_base_url"] = args.openai_endpoint.rstrip("/") + "/"
    if args.embedding_deployment:
        updates["azure_openai_embedding_deployment"] = args.embedding_deployment
    if args.embedding_dimensions is not None:
        if args.embedding_dimensions != 1536:
            raise ValueError(
                "This demo expects text-embedding-3-small to use 1536-dimensional embeddings."
            )
        updates["embedding_dimensions"] = args.embedding_dimensions

    return replace(settings, **updates) if updates else settings


def load_settings(args: argparse.Namespace) -> SeederSettings:
    env_values = dict(os.environ)
    if args.openai_endpoint:
        env_values["AZURE_OPENAI_BASE_URL"] = args.openai_endpoint
    if args.embedding_deployment:
        env_values["EMBEDDING_DEPLOYMENT"] = args.embedding_deployment
    if args.embedding_dimensions is not None:
        env_values["AZURE_OPENAI_EMBEDDING_DIMENSIONS"] = str(args.embedding_dimensions)
    if args.count is not None:
        env_values["SEED_DOCUMENT_COUNT"] = str(args.count)

    settings = SeederSettings.from_mapping(env_values)
    return apply_cli_overrides(settings, args)


def should_validate_dry_run(
    args: argparse.Namespace, env_values: Mapping[str, str] | None = None
) -> bool:
    values = env_values if env_values is not None else os.environ
    if args.openai_endpoint or args.embedding_deployment:
        return True
    return any(values.get(key) for key in _DRY_RUN_CONFIG_ENV_KEYS)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed synthetic healthcare care-guidance documents into Cosmos DB."
    )
    parser.add_argument(
        "--count",
        type=int,
        help="Override the number of synthetic documents to generate.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Embedding batch size.",
    )
    parser.add_argument(
        "--openai-endpoint",
        help="OpenAI-compatible Foundry/Azure OpenAI endpoint, matching the Azure MCP CLI naming.",
    )
    parser.add_argument(
        "--embedding-deployment",
        help="Embedding deployment name, matching the Azure MCP CLI naming.",
    )
    parser.add_argument(
        "--embedding-dimensions",
        type=int,
        help="Embedding dimensions override. This demo currently validates that the value remains 1536.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate an offline preview without requiring environment variables or calling Azure. If Azure config values are supplied, also validate that they parse correctly.",
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        if args.embedding_dimensions is not None and args.embedding_dimensions != 1536:
            raise ValueError(
                "This demo expects text-embedding-3-small to use 1536-dimensional embeddings."
            )
        validated_settings = load_settings(args) if should_validate_dry_run(args) else None
        count = (
            args.count
            if args.count is not None
            else validated_settings.document_count if validated_settings is not None else 4
        )
        preview_documents = build_synthetic_guidance_documents(count)
        print(json.dumps(preview_documents[: min(len(preview_documents), 3)], indent=2))
        print(
            f"\nPrepared {len(preview_documents)} synthetic documents for offline dry-run preview."
        )
        if validated_settings is None:
            print("No Azure configuration supplied; offline preview only (no Azure wiring validated).")
        else:
            print("Validated provided seeder configuration locally without calling Azure services.")
        return 0

    settings = load_settings(args)

    result = seed_documents(settings, dry_run=args.dry_run, batch_size=args.batch_size)
    print(
        f"Prepared {result.document_count} synthetic documents for "
        f"{result.database_name}/{result.container_name} at {result.cosmos_endpoint} "
        f"with {result.embedding_dimensions}-dimension embeddings."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
