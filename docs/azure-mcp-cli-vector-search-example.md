# Azure MCP CLI vector-search example

> Source captured from Microsoft Learn on 2026-09-29. This page intentionally preserves the current command template with placeholders only.

Reference:

- Microsoft Learn: `https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-cosmos-db?tabs=mcp-server#search-container-items-by-vector-similarity`

## Exact current CLI example from Microsoft Learn

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

## How to map this to the templates in this repo

| Learn placeholder | Template location |
| --- | --- |
| `<vector-property>` | `COSMOS_VECTOR_PROPERTY` |
| `<search-text>` | operator-supplied query text at runtime |
| `<openai-endpoint>` | `OPENAI_ENDPOINT` |
| `<embedding-deployment>` | `EMBEDDING_DEPLOYMENT_NAME` |
| `<container>` | `COSMOS_CONTAINER_NAME` |
| `<database>` | `COSMOS_DATABASE_NAME` |
| `<account>` | `COSMOS_ACCOUNT_NAME` |
| `<embedding-dimensions>` | `EMBEDDING_DIMENSIONS` |

## Healthcare demo command

After deployment and seeding, set the non-secret account name and embedding endpoint in your local shell. This concrete example returns only human-readable fields and omits the 1536-value embedding array:

```powershell
azmcp cosmos database container item vector-search `
  --vector-property embedding `
  --search-text "guidance for an adult with asthma who wants a safe exercise plan" `
  --openai-endpoint $env:OPENAI_ENDPOINT `
  --embedding-deployment text-embedding-3-small `
  --container guidance `
  --database care-guidance `
  --account $env:COSMOS_ACCOUNT_NAME `
  --properties-to-select "id,title,summary,conditionGroup,careSetting,population,intent,riskLevel" `
  --count 5 `
  --embedding-dimensions 1536
```

Expected behavior: Azure MCP Server embeds the search text with the named Foundry deployment, runs Cosmos DB `VectorDistance` against `/embedding`, and returns up to five synthetic guidance records ranked by `_score`.

`OPENAI_ENDPOINT` must be the resource root (`https://<resource>.openai.azure.com/`). Do not pass the seeder's `AZURE_OPENAI_BASE_URL`, which ends in `/openai/v1/`.

## Demo-safe reminder

Keep the command structure unchanged, but replace placeholders only in your private environment or local scratch files. Do not commit populated values back to this repository.
