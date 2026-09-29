from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential


class AgentSettingsError(ValueError):
    """Raised when the Foundry MCP agent configuration is incomplete."""


@dataclass(frozen=True)
class AgentSettings:
    project_endpoint: str
    model_deployment_name: str
    connection_name: str
    mcp_server_url: str
    agent_name: str = "synthetic-care-guidance-agent"
    mcp_server_label: str = "cosmosdb"
    query: str = (
        "Find the most relevant synthetic guidance for an adult with asthma "
        "who wants a safe exercise plan."
    )

    @classmethod
    def from_env(cls) -> "AgentSettings":
        return cls.from_mapping(os.environ)

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> "AgentSettings":
        required = {
            "FOUNDRY_PROJECT_ENDPOINT": values.get("FOUNDRY_PROJECT_ENDPOINT", ""),
            "MODEL_DEPLOYMENT_NAME": values.get("MODEL_DEPLOYMENT_NAME", ""),
            "CONNECTION_NAME": values.get("CONNECTION_NAME", ""),
            "MCP_SERVER_URL": values.get("MCP_SERVER_URL", ""),
        }
        missing = sorted(key for key, value in required.items() if not value)
        if missing:
            raise AgentSettingsError(
                "Missing required environment variables: " + ", ".join(missing)
            )

        project_endpoint = required["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
        if ".services.ai.azure.com/api/projects/" not in project_endpoint:
            raise AgentSettingsError(
                "FOUNDRY_PROJECT_ENDPOINT must use the Foundry project endpoint format "
                "https://<resource>.services.ai.azure.com/api/projects/<project>."
            )

        mcp_server_url = required["MCP_SERVER_URL"]
        if not mcp_server_url.startswith("https://"):
            raise AgentSettingsError("MCP_SERVER_URL must use HTTPS.")

        return cls(
            project_endpoint=project_endpoint,
            model_deployment_name=required["MODEL_DEPLOYMENT_NAME"],
            connection_name=required["CONNECTION_NAME"],
            mcp_server_url=mcp_server_url,
            agent_name=values.get("AGENT_NAME", "synthetic-care-guidance-agent"),
            mcp_server_label=values.get("MCP_SERVER_LABEL", "cosmosdb"),
            query=values.get(
                "DEMO_QUERY",
                (
                    "Find the most relevant synthetic guidance for an adult with asthma "
                    "who wants a safe exercise plan."
                ),
            ),
        )


def run_agent(settings: AgentSettings) -> str:
    """Create a Foundry agent version and run one MCP-backed query."""

    project = AIProjectClient(
        endpoint=settings.project_endpoint,
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=False),
    )
    mcp_tool = MCPTool(
        server_label=settings.mcp_server_label,
        server_url=settings.mcp_server_url,
        require_approval="never",
        project_connection_id=settings.connection_name,
    )
    agent = project.agents.create_version(
        agent_name=settings.agent_name,
        definition=PromptAgentDefinition(
            model=settings.model_deployment_name,
            instructions=(
                "Use the Cosmos DB MCP tools to search only the synthetic care-guidance "
                "corpus. Prefer vector_search for semantic questions. Explain that results "
                "are fictional educational examples and are not medical advice. Never infer "
                "or request real patient information."
            ),
            tools=[mcp_tool],
        ),
    )

    openai = project.get_openai_client()
    response = openai.responses.create(
        input=settings.query,
        extra_body={
            "agent_reference": {
                "name": agent.name,
                "type": "agent_reference",
            }
        },
    )
    return response.output_text


def main() -> int:
    settings = AgentSettings.from_env()
    output = run_agent(settings)
    if not output or not output.strip():
        raise RuntimeError("The Foundry agent returned no output text.")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
