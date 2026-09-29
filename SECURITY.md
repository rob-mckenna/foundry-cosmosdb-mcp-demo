# Security Policy

This repository is intended to remain safe to clone as a **public demo**. Only placeholder values and secretless configuration patterns belong in source control.

## Reporting a Vulnerability

- Do **not** open a public issue containing credentials, tokens, keys, or detailed exploit steps.
- Prefer GitHub private vulnerability reporting if it is enabled for this repository.
- If private reporting is unavailable, contact the maintainers through a private channel first and share only the minimum information needed to reproduce the issue safely.

## Public-Repository Rules

- Never commit `.env` files, local override files, access tokens, connection strings, account keys, SAS tokens, or client secrets.
- Checked-in configuration must be either:
  - placeholder-only documentation, or
  - secretless runtime configuration.
- MCP examples must reference environment variables or other external credential sources, never inline secrets.

## Required Azure Authentication Posture

For Azure resources used by this demo, the supported pattern is:

1. **`DefaultAzureCredential`** in application code and samples.
2. **Managed identity** for deployed workloads whenever Azure hosts the app.
3. **Azure RBAC** with least-privilege role assignments.

The following are intentionally **not** the recommended path for this repo:

- Cosmos DB account keys
- Static connection strings with embedded secrets
- Entra app client secrets committed to config
- Checked-in PATs, API keys, or shared secrets

For local development, authenticate through developer tooling supported by `DefaultAzureCredential` (for example, Azure CLI or IDE sign-in), not by adding secrets to tracked files.

## Repository-Specific Notes

- `.mcp.json` is an **example-only** MCP configuration. It must stay placeholder-only and must not be converted into a checked-in secret-bearing config.
- `.mcp.json` contains only the repository-local Squad state server configuration and no credentials.
- Local-only secret files and local MCP overrides are ignored by `.gitignore`.

## Change Review Expectations

Any new infrastructure or documentation added to this repository should continue to:

- use managed identity where available,
- rely on Azure RBAC for authorization,
- use `DefaultAzureCredential` rather than static secrets,
- avoid publishing tenant-specific or environment-specific sensitive values.
