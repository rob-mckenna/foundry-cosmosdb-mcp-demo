# Contributing

Thanks for helping improve this public, customer-agnostic demo repository.

This repo includes infrastructure-as-code, a Python synthetic-data seeder, placeholder-only MCP templates, and supporting docs. Contributions should keep it safe to publish, easy to understand, and honest about what is or is not implemented or locally validated.

## Ground rules

### 1. Synthetic data only

Do not add:

- real PHI
- real PII
- customer records
- production exports
- screenshots containing real tenant, subscription, or user data

If you need example content, generate obviously fake sample data.

### 2. No secrets in the repository

Do not commit:

- API keys
- bearer tokens
- connection strings
- passwords
- `.env` files with live values
- copied portal output that exposes secret or tenant-specific details

Use placeholders and environment variables in documentation and sample configuration.

### 3. Keep the repo honest

Do not document folders, commands, or deployed artifacts as if they exist when they do not.

If you are describing future or planned behavior:

- label it clearly
- avoid fake links to missing files
- update the docs again when the implementation actually lands

### 4. No web UI assumptions

This repo currently has **no web UI**. Do not imply there is one unless a reviewed change adds it and updates the README accordingly.

### 5. Do not vendor MCPToolKit casually

This repository may reference the Azure Cosmos DB MCPToolKit, but it does not currently vendor that toolkit.

If you want to import assets from upstream:

- preserve licensing and attribution
- explain why vendoring is necessary
- update the README to clarify what is local versus external

## What good contributions look like

Useful changes include:

- clearer public docs
- tighter security/privacy wording
- secret-free setup guidance
- improvements to the synthetic seeding flow
- infrastructure or tests that match the README and stay public-safe

For the current baseline, also review [SECURITY.md](SECURITY.md).

## Repo-specific expectations

If you add or change implementation files, also update:

- [README.md](README.md)
- any related docs under `docs/`
- usage notes, prerequisites, and validation steps

Documentation is part of the deliverable, not follow-up work.

## Suggested workflow

1. Create a branch.
2. Make the smallest complete change.
3. Verify all changed links and commands.
4. Re-read your contribution for secret leaks and accidental customer specificity.
5. Open a pull request with a concise description of what changed and why.

## Validation

For the current repo shape, these checks are a good baseline:

```powershell
python -m pip install -e .[dev]
pytest
python -m json.tool .\infra\main.parameters.json
python -m json.tool .mcp.json
pwsh -File .\scripts\Validate-PublicRepoSurface.ps1
```

If you're working on the seeder, also verify the placeholder contract in:

```powershell
Get-Content .\scripts\seeder.env.example
python .\scripts\seed_synthetic_data.py --dry-run --count 4
```

If Azure CLI and Bicep are installed locally, also run:

```powershell
az bicep build --file .\infra\main.bicep
```

## Style guidance

- Prefer direct language over marketing language.
- Keep examples customer-agnostic.
- Use relative links for files that exist in this repo.
- Align any new environment variables with `azure.yaml`, `infra/main.parameters.json`, and the README.
- Preserve the managed-identity / RBAC / `DefaultAzureCredential` posture.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
