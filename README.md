# Foundry + Cosmos DB MCP Demo

Public, customer-agnostic Microsoft Foundry + Azure Cosmos DB MCP vector-search demo for **synthetic healthcare care-guidance discovery**. The repo provisions the Azure resource skeleton with Bicep/azd, seeds a synthetic corpus with `DefaultAzureCredential`, documents remote MCP-to-Foundry wiring, and keeps all checked-in configuration secret-free.

## What this repo includes

- `azure.yaml` plus `infra/main.bicep` and `infra/main.parameters.json` for:
  - a Microsoft Foundry resource and project
  - a `text-embedding-3-small` deployment
  - a Cosmos DB for NoSQL account, database, and container
  - `/embedding` vector policy with `diskANN`
  - managed identity and RBAC assignments for secretless auth
- a Python seeder under `src/foundry_cosmos_demo/` and `scripts/seed_synthetic_data.py`
- a Foundry MCP agent sample based on [AzureCosmosDB/MCPToolKit](https://github.com/AzureCosmosDB/MCPToolKit), without vendoring the toolkit
- the exact current Azure MCP Server Cosmos vector-search CLI example from Microsoft Learn in `docs/azure-mcp-cli-vector-search-example.md`
- credential-free CI and local validation

## What this repo intentionally does not include

- real PHI, PII, or customer data
- checked-in secrets, account keys, or connection strings
- a web UI
- a vendored copy of MCPToolKit
- automatic deployment into an arbitrary subscription; you choose the target environment

## Architecture

```text
Microsoft Foundry agent
(scripts/run_foundry_mcp_agent.py)
        |
        v
Remote MCP endpoint
(Azure Cosmos DB MCP Toolkit)
        |
        +------------------------------+
        |                              |
        v                              v
Azure Cosmos DB for NoSQL      Microsoft Foundry embedding deployment
synthetic care-guidance docs   text-embedding-3-small (1536 dims)
with /embedding vectors        query-time vector generation
```

### Core Azure shape

- **Foundry resource + project**: provisioned with `Microsoft.CognitiveServices/accounts` and `accounts/projects`, following the current Microsoft Foundry Bicep quickstart.
- **Foundry project endpoint**: `https://<resource>.services.ai.azure.com/api/projects/<project>`.
- **Embeddings**: `text-embedding-3-small`, sized for **1536 dimensions**.
- **Cosmos DB**: NoSQL account with `EnableNoSQLVectorSearch`, local auth disabled, and a `guidance` container that stores vectors on `/embedding`.
- **RBAC**:
  - Foundry project managed identity
  - optional deployer principal assignment for local seeding
- **Seeder auth**: `DefaultAzureCredential`; no static secrets or keys.

## Repo layout

| Path | Purpose |
| --- | --- |
| [`azure.yaml`](azure.yaml) | azd project definition |
| [`infra/main.bicep`](infra/main.bicep) | Foundry + Cosmos + RBAC infrastructure |
| [`infra/main.parameters.json`](infra/main.parameters.json) | azd parameter mapping |
| [`pyproject.toml`](pyproject.toml) | Python package/test configuration |
| [`src/foundry_cosmos_demo/`](src/foundry_cosmos_demo) | Python seeder package |
| [`scripts/seed_synthetic_data.py`](scripts/seed_synthetic_data.py) | Seeder entry point |
| [`scripts/run_foundry_mcp_agent.py`](scripts/run_foundry_mcp_agent.py) | Foundry agent using the upstream MCPToolKit connection pattern |
| [`scripts/seeder.env.example`](scripts/seeder.env.example) | Local placeholder environment contract for the seeder |
| [`tests/`](tests) | Offline unit tests |
| [`docs/mcp-toolkit-remote-setup.md`](docs/mcp-toolkit-remote-setup.md) | Remote MCP-to-Foundry setup guidance |
| [`docs/azure-mcp-cli-vector-search-example.md`](docs/azure-mcp-cli-vector-search-example.md) | Exact current Azure MCP CLI example |
| [`templates/mcp/`](templates/mcp) | Placeholder-only MCP config templates |
| [`scripts/Validate-PublicRepoSurface.ps1`](scripts/Validate-PublicRepoSurface.ps1) | Repo-surface validation |

## Prerequisites

- Python 3.11+
- PowerShell 7+ for the validation script
- Azure CLI with Bicep support if you want to build or deploy the infra locally
- Azure Developer CLI (`azd`) if you want to use the included `azure.yaml`
- an Azure subscription if you plan to provision resources
- a chat-capable model deployment for the optional Foundry agent sample

No Azure credentials are required for CI or the offline unit tests.

## Infrastructure details

The Bicep template provisions:

1. **Microsoft Foundry**
   - `Microsoft.CognitiveServices/accounts@2025-06-01`
   - `Microsoft.CognitiveServices/accounts/projects@2025-06-01`
   - `Microsoft.CognitiveServices/accounts/deployments@2025-06-01`
2. **Cosmos DB for NoSQL**
   - `Microsoft.DocumentDB/databaseAccounts@2024-11-15`
   - `EnableNoSQLVectorSearch`
   - local auth disabled
   - database: `care-guidance`
   - container: `guidance`
3. **Vector policy**
   - vector path: `/embedding`
   - datatype: `float32`
   - distance function: `cosine`
   - dimensions: `1536`
   - vector index: `diskANN`
4. **Secretless auth**
   - Foundry project managed identity
   - Cosmos DB built-in data contributor data-plane assignments
   - Foundry `Cognitive Services OpenAI User` assignments

### Important assumptions

- The template defaults `embeddingModelVersion` to `1`. Regions and model catalog availability can change; azd users can override it per environment through `EMBEDDING_MODEL_VERSION`, which this repo maps in `infra/main.parameters.json`.
- The seeder uses the OpenAI-compatible inference base URL for the deployed Foundry model (`https://<custom-subdomain>.openai.azure.com/openai/v1/`) rather than the project management endpoint.

## Using azd

Create an environment and set the non-secret values:

```powershell
azd env new foundry-cosmos-demo
azd env set AZURE_LOCATION eastus2
azd env set DEPLOYER_PRINCIPAL_ID <your-aad-object-id>
```

Then provision:

```powershell
azd provision
```

If your region requires a different embedding model version, set it on the azd environment first and then provision:

```powershell
azd env set EMBEDDING_MODEL_VERSION <supported-version>
azd provision
```

The repo does **not** deploy an application service. It provisions the Azure resource layer only.

## Seeding synthetic care-guidance data

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

Set the required environment variables from your deployed resources:

```powershell
$env:AZURE_COSMOSDB_ENDPOINT = "https://<cosmos-account>.documents.azure.com:443/"
$env:AZURE_COSMOSDB_DATABASE_NAME = "care-guidance"
$env:AZURE_COSMOSDB_CONTAINER_NAME = "guidance"
$env:AZURE_OPENAI_BASE_URL = "https://<custom-subdomain>.openai.azure.com/openai/v1/"
$env:AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "text-embedding-3-small"
```

`scripts/seeder.env.example` captures the same placeholder-only contract. Export values in your shell or copy them to `.env.local`, which is ignored; do **not** edit the tracked example in place.

Preview the deterministic synthetic payload without calling Azure. If you already exported seeder settings, the same command also validates that those values parse locally without making Azure calls:

```powershell
python .\scripts\seed_synthetic_data.py --dry-run
```

Seed Cosmos DB with live embeddings:

```powershell
python .\scripts\seed_synthetic_data.py
```

The seeded documents remain synthetic and customer-agnostic; they contain generic care-guidance topics, guidance steps, and red-flag lists only.

## Remote MCP-to-Foundry setup

Use the upstream Azure Cosmos DB MCP Toolkit as the deployable remote server:

- [MCPToolKit-to-Foundry setup and agent runbook](docs/mcp-toolkit-remote-setup.md)
- [Placeholder MCP templates](templates/mcp)
- [Azure MCP CLI vector-search example](docs/azure-mcp-cli-vector-search-example.md)

After the toolkit is deployed and its Foundry managed-identity connection exists, export the private runtime values and run:

```powershell
python .\scripts\run_foundry_mcp_agent.py
```

The default question asks for synthetic asthma exercise guidance. A successful run creates a Foundry agent version, invokes MCPToolKit's Cosmos DB tools, and prints a synthesis of the closest fictional records.

### Exact current Azure MCP CLI vector-search example

The verbatim current Microsoft Learn command is preserved in `docs/azure-mcp-cli-vector-search-example.md`:

```console
azmcp cosmos database container item vector-search \
  --vector-property <vector-property> \
  --search-text <search-text> \
  --openai-endpoint <openai-endpoint> \
  --embedding-deployment <embedding-deployment> \
  --container <container> \
  --database <database> \
  --account <account> \
  [--properties-to-select <properties-to-select>] \
  [--count <count>] \
  [--embedding-dimensions <embedding-dimensions>]
```

The complete healthcare-specific command, including selected properties, count, and 1536 dimensions, is in [the Azure MCP vector-search runbook](docs/azure-mcp-cli-vector-search-example.md). It uses the OpenAI resource root in `OPENAI_ENDPOINT`; the Python seeder separately uses `AZURE_OPENAI_BASE_URL` ending in `/openai/v1/`.

## Validation

### Credential-free local checks

```powershell
python -m pip install -e .[dev]
pytest
python -m json.tool .\infra\main.parameters.json
python -m json.tool .mcp.json
pwsh -File .\scripts\Validate-PublicRepoSurface.ps1
```

### Optional local infra build check

If Azure CLI and Bicep are installed:

```powershell
az bicep build --file .\infra\main.bicep
```

### CI

GitHub Actions runs:

- `git diff --check`
- `pytest`
- `pwsh -File ./scripts/Validate-PublicRepoSurface.ps1`

No Azure credentials are required for CI.

## Example prompts and expected results

| Path | Example | Expected behavior |
| --- | --- | --- |
| Foundry + MCPToolKit | `Find synthetic guidance for an adult with asthma who wants a safe exercise plan.` | The agent calls `vector_search`, returns nearby fictional guidance, and includes the educational-use disclaimer. |
| Azure MCP Server | Use the command in `docs/azure-mcp-cli-vector-search-example.md` | The tool generates the query embedding and ranks Cosmos documents with `VectorDistance`. |
| MCPToolKit discovery | `Infer the schema of the guidance container.` | The toolkit reports top-level fields such as `title`, `content`, `conditionGroup`, and `embedding`. |

Actual ranking varies with the deployed model and seeded count; the repository does not check in fabricated live output.

## Cost and security notes

- Cosmos DB autoscale defaults to 4000 RU/s maximum; reduce or remove resources when the demo is idle.
- Foundry model deployments consume quota and incur usage charges.
- Deploying MCPToolKit adds Container Apps and Container Registry resources described by the upstream project.
- Local authentication is disabled on Cosmos DB and the Foundry resource. Access uses Entra ID, managed identity, and RBAC.
- Public network access remains enabled for demo simplicity. Production deployments should add private networking and organizational policy controls.
- The sample gives the optional deployer principal data-plane access for seeding. Omit `DEPLOYER_PRINCIPAL_ID` when local seeding is not required.

## Limitations

- This is an educational demo, not a clinical system or a source of medical advice.
- All records are deterministic synthetic examples; no PHI or customer data belongs in the repository.
- Chat-model deployment availability differs by region, so the agent sample expects an existing chat deployment rather than provisioning one.
- MCPToolKit is deployed and versioned independently; follow its release notes and security guidance.
- Vector search quality is illustrative and is not evaluated for clinical accuracy.

## Troubleshooting

- **Bicep model deployment fails**: choose a region/model version available to the subscription and set `EMBEDDING_MODEL_VERSION`.
- **Seeder returns 403**: confirm the signed-in identity has Cosmos DB Built-in Data Contributor and Cognitive Services OpenAI User.
- **Foundry project 404**: use `https://<resource>.services.ai.azure.com/api/projects/<project>`, not a legacy endpoint.
- **MCPToolKit returns 401/403**: recreate or verify the `ProjectManagedIdentity` connection and toolkit app-role assignment.
- **Vector search returns no rows**: seed the data and verify the container vector path is `/embedding` with 1536 dimensions.

## Teardown

Delete the azd environment's resource group when finished:

```powershell
azd down --purge
```

If MCPToolKit was deployed into a separate resource group, remove that group separately after confirming it contains no shared resources. Delete any Entra app registration created by the toolkit according to its teardown guidance.

## Security and data-handling guardrails

- synthetic data only
- no web UI
- no checked-in secrets
- no static Cosmos DB keys or connection strings
- managed identity + RBAC + `DefaultAzureCredential` as the supported auth posture
- placeholder-only MCP configs and docs

See [SECURITY.md](SECURITY.md) for the full public-demo policy.

## License

This repository is released under the [MIT License](LICENSE).
