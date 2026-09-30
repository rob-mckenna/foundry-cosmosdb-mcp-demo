from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bicep_declares_required_vector_and_embedding_shapes() -> None:
    contents = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")

    assert "name: 'EnableNoSQLVectorSearch'" in contents
    assert "path: '/embedding'" in contents
    assert "type: 'diskANN'" in contents
    assert "dimensions: 1536" in contents
    assert "name: 'text-embedding-3-small'" in contents
    assert "param embeddingDeploymentCapacity int = 200" in contents
    assert "name: 'gpt-4.1-mini'" in contents
    assert "param chatDeploymentCapacity int = 10" in contents
    assert "disableLocalAuth: true" in contents
    assert ".services.ai.azure.com/api/projects/" in contents
    assert "dependsOn:" in contents
    assert "publicNetworkAccess: 'Disabled'" in contents
    assert "privatelink.documents.azure.com" in contents
    assert "Microsoft.Network/privateEndpoints" in contents
    assert "Microsoft.Network/natGateways" in contents
    assert "serviceName: 'Microsoft.App/environments'" in contents
    assert "53ca6127-db72-4b80-b1b0-d745d6d5456d" in contents


def test_azd_parameters_file_uses_standard_environment_variables() -> None:
    contents = (ROOT / "infra" / "main.parameters.json").read_text(encoding="utf-8")

    assert "${AZURE_ENV_NAME}" in contents
    assert "${AZURE_LOCATION}" in contents
    assert "${EMBEDDING_MODEL_VERSION=1}" in contents


def test_seeder_env_example_documents_required_variables() -> None:
    contents = (ROOT / "scripts" / "seeder.env.example").read_text(encoding="utf-8")

    assert "AZURE_COSMOSDB_ENDPOINT=" in contents
    assert "AZURE_OPENAI_BASE_URL=" in contents
    assert "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small" in contents
