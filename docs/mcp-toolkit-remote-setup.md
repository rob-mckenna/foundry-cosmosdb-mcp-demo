# Connect MCPToolKit to Microsoft Foundry

This demo uses the upstream [Azure Cosmos DB MCP Toolkit](https://github.com/AzureCosmosDB/MCPToolKit) as the remote MCP server. The toolkit supplies the deployable server, Entra authentication, Cosmos DB operations, schema discovery, and vector search. This repository supplies the Foundry/Cosmos infrastructure, synthetic dataset, a small Foundry client adapted from the toolkit sample, and secret-free configuration contracts.

No MCPToolKit source is vendored here. Clone and deploy the upstream project separately so fixes and security updates remain owned by its maintainers.

## End-to-end path

1. Provision this repository with `azd provision`.
2. Seed the synthetic `care-guidance/guidance` container.
3. Clone `https://github.com/AzureCosmosDB/MCPToolKit` outside this repository.
4. Follow its [Quick Start](https://github.com/AzureCosmosDB/MCPToolKit/blob/main/docs/QUICK-START.md) to deploy the remote server, using this deployment's:
   - Cosmos endpoint
   - Foundry/OpenAI embedding endpoint
   - `text-embedding-3-small` deployment
   - 1536 embedding dimensions
5. Keep the toolkit-generated `deployment-info.json` private. It contains environment-specific identifiers and must not be copied into this repository.
6. From the MCPToolKit clone, create the Foundry managed-identity connection:

   ```powershell
   .\scripts\Setup-AIFoundry-Connection.ps1 `
     -AIFoundryProjectResourceId "<aiFoundryProjectResourceId-output>" `
     -ConnectionName "cosmos-mcp-toolkit-connection"
   ```

   The upstream script reads the MCP target URL and Entra audience from its private `deployment-info.json`, creates a `ProjectManagedIdentity` remote-tool connection, and grants the Foundry project identity the toolkit app role.
7. Add a chat model deployment to the Foundry resource and set `MODEL_DEPLOYMENT_NAME` to that deployment. The infrastructure in this repo intentionally deploys only the embedding model because chat-model availability varies by region and subscription.
8. Copy `templates/mcp/remote-foundry-cosmos.env.template` to a private, ignored file or export the values in your shell.
9. Run the Foundry agent sample:

   ```powershell
   python .\scripts\run_foundry_mcp_agent.py
   ```

The client follows the upstream [`client/agents_cosmosdb_mcp.py`](https://github.com/AzureCosmosDB/MCPToolKit/blob/main/client/agents_cosmosdb_mcp.py) pattern, updated to use `DefaultAzureCredential` and the current Foundry project endpoint:

```text
https://<foundry-resource>.services.ai.azure.com/api/projects/<foundry-project>
```

## Required private runtime values

| Variable | Purpose |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Current Foundry project endpoint from the Bicep output |
| `MODEL_DEPLOYMENT_NAME` | A chat-capable model deployment used by the agent |
| `CONNECTION_NAME` | Foundry connection created by the upstream setup script |
| `MCP_SERVER_URL` | Toolkit HTTPS endpoint ending in `/mcp` |
| `MCP_SERVER_LABEL` | Stable label exposed to the agent; default `cosmosdb` |
| `AGENT_NAME` | Foundry agent name |
| `DEMO_QUERY` | Synthetic healthcare question to send |

Authentication remains secretless:

- local runs use the developer's Azure CLI session through `DefaultAzureCredential`
- Foundry calls the toolkit with the project's managed identity
- the toolkit uses managed identity/RBAC for Azure services
- no Cosmos keys or OpenAI keys are required by this repository

## Expected agent behavior

For the default query, the agent should call MCPToolKit's `vector_search` tool against the synthetic container and summarize the closest fictional care-guidance records. Results are educational sample data, not medical advice.

Other useful prompts:

- `List the databases and containers available to this demo.`
- `Infer the schema of the guidance container.`
- `Find synthetic guidance similar to hydration planning for an older adult.`

## Templates

- `templates/mcp/remote-foundry-cosmos-client.template.json` shows a generic remote client contract.
- `templates/mcp/remote-foundry-cosmos-server.template.json` documents server-side values without making the file runnable.
- `templates/mcp/remote-foundry-cosmos.env.template` lists the complete private runtime contract.

## Troubleshooting

- **401/403 from the MCP server**: rerun the upstream Foundry connection setup and confirm the project managed identity received the toolkit app role.
- **Foundry client 404**: use the current `services.ai.azure.com/api/projects/...` endpoint, not a legacy `api.azureml.ms` endpoint.
- **No vector results**: seed the container first and verify the toolkit uses `embedding`, `text-embedding-3-small`, and 1536 dimensions.
- **Model deployment not found**: set `MODEL_DEPLOYMENT_NAME` to a chat-capable deployment available in the same Foundry resource.

## Sources

- [Azure Cosmos DB MCP Toolkit](https://github.com/AzureCosmosDB/MCPToolKit)
- [MCPToolKit Foundry client sample](https://github.com/AzureCosmosDB/MCPToolKit/blob/main/client/agents_cosmosdb_mcp.py)
- [MCPToolKit Foundry connection script](https://github.com/AzureCosmosDB/MCPToolKit/blob/main/scripts/Setup-AIFoundry-Connection.ps1)
- [Azure MCP Server Cosmos DB vector-search tool](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-cosmos-db?tabs=mcp-server#search-container-items-by-vector-similarity)
- [Current Microsoft Foundry project endpoint](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/sdk-overview)
