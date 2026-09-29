import pytest

from foundry_cosmos_demo.foundry_agent import AgentSettings, AgentSettingsError


def test_agent_settings_load_secretless_connection_contract() -> None:
    settings = AgentSettings.from_mapping(
        {
            "FOUNDRY_PROJECT_ENDPOINT": (
                "https://demo.services.ai.azure.com/api/projects/care-guidance"
            ),
            "MODEL_DEPLOYMENT_NAME": "gpt-4.1-mini",
            "CONNECTION_NAME": "cosmos-mcp-toolkit-connection",
            "MCP_SERVER_URL": "https://example.invalid/mcp",
        }
    )

    assert settings.project_endpoint.endswith("/projects/care-guidance")
    assert settings.mcp_server_label == "cosmosdb"
    assert "asthma" in settings.query


def test_agent_settings_reject_legacy_project_endpoint() -> None:
    with pytest.raises(AgentSettingsError):
        AgentSettings.from_mapping(
            {
                "FOUNDRY_PROJECT_ENDPOINT": (
                    "https://legacy-project.eastus.api.azureml.ms/"
                ),
                "MODEL_DEPLOYMENT_NAME": "gpt-4.1-mini",
                "CONNECTION_NAME": "cosmos-mcp-toolkit-connection",
                "MCP_SERVER_URL": "https://example.invalid/mcp",
            }
        )
