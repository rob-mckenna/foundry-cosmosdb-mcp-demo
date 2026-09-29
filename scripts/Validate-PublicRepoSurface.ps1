Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Get-RepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string] $RelativePath
    )

    $parts = $RelativePath -split '[\\/]'
    $path = $repoRoot
    foreach ($part in $parts) {
        $path = Join-Path $path $part
    }

    return $path
}

function Assert-PathExists {
    param(
        [Parameter(Mandatory = $true)]
        [string] $RelativePath
    )

    $fullPath = Get-RepoPath -RelativePath $RelativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw "Missing required file: $RelativePath"
    }
}

function Read-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string] $RelativePath
    )

    $fullPath = Get-RepoPath -RelativePath $RelativePath
    return (Get-Content -LiteralPath $fullPath -Raw | ConvertFrom-Json)
}

function Assert-Contains {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Content,
        [Parameter(Mandatory = $true)]
        [string] $Needle,
        [Parameter(Mandatory = $true)]
        [string] $Message
    )

    if (-not $Content.Contains($Needle)) {
        throw $Message
    }
}

function Assert-Matches {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Content,
        [Parameter(Mandatory = $true)]
        [string] $Pattern,
        [Parameter(Mandatory = $true)]
        [string] $Message
    )

    if ($Content -notmatch $Pattern) {
        throw $Message
    }
}

$requiredFiles = @(
    'azure.yaml',
    'infra\main.bicep',
    'infra\main.parameters.json',
    'pyproject.toml',
    'src\foundry_cosmos_demo\__init__.py',
    'src\foundry_cosmos_demo\config.py',
    'src\foundry_cosmos_demo\foundry_agent.py',
    'src\foundry_cosmos_demo\synthetic_data.py',
    'src\foundry_cosmos_demo\seeder.py',
    'scripts\run_foundry_mcp_agent.py',
    'scripts\seed_synthetic_data.py',
    'scripts\seeder.env.example',
    'tests\test_config.py',
    'tests\test_foundry_agent.py',
    'tests\test_infra_scaffold.py',
    'tests\test_seeder.py',
    'tests\test_synthetic_data.py',
    'docs\mcp-toolkit-remote-setup.md',
    'docs\azure-mcp-cli-vector-search-example.md',
    'templates\mcp\remote-foundry-cosmos-client.template.json',
    'templates\mcp\remote-foundry-cosmos-server.template.json',
    'templates\mcp\remote-foundry-cosmos.env.template',
    'scripts\Validate-PublicRepoSurface.ps1',
    '.github\workflows\ci.yml'
)

foreach ($file in $requiredFiles) {
    Assert-PathExists -RelativePath $file
}

$clientTemplate = Read-JsonFile -RelativePath 'templates\mcp\remote-foundry-cosmos-client.template.json'
$serverTemplate = Read-JsonFile -RelativePath 'templates\mcp\remote-foundry-cosmos-server.template.json'

Assert-Contains -Content $clientTemplate.'$comment' -Needle 'Placeholder-only' -Message 'Client template must be clearly labeled placeholder-only.'
Assert-Contains -Content $clientTemplate.'$comment' -Needle 'not runnable as-is' -Message 'Client template must be labeled non-runnable.'
Assert-Contains -Content $clientTemplate.mcpServers.'foundry-cosmos-remote'.transport.url -Needle '<remote-mcp-host>' -Message 'Client template must keep the remote host as a placeholder.'
Assert-Contains -Content $clientTemplate.mcpServers.'foundry-cosmos-remote'.transport.headers.Authorization -Needle '${REMOTE_MCP_BEARER_TOKEN}' -Message 'Client template must reference a token environment variable placeholder.'
Assert-Contains -Content $clientTemplate.mcpServers.'foundry-cosmos-remote'.metadata.foundryProjectEndpoint -Needle '.services.ai.azure.com/api/projects/' -Message 'Client template must use the current Foundry project endpoint.'
Assert-Contains -Content $clientTemplate.mcpServers.'foundry-cosmos-remote'.metadata.openAiEndpoint -Needle '<openai-resource>' -Message 'Client template must keep the OpenAI endpoint placeholder.'

Assert-Contains -Content $serverTemplate.'$comment' -Needle 'Placeholder-only' -Message 'Server template must be clearly labeled placeholder-only.'
Assert-Contains -Content $serverTemplate.remoteServer.baseUrl -Needle '<remote-mcp-host>' -Message 'Server template must keep the remote base URL as a placeholder.'
Assert-Contains -Content $serverTemplate.cosmos.accountEndpoint -Needle '<cosmos-account>' -Message 'Server template must keep the Cosmos endpoint as a placeholder.'
Assert-Contains -Content $serverTemplate.embeddings.foundryProjectEndpoint -Needle '.services.ai.azure.com/api/projects/' -Message 'Server template must use the current Foundry project endpoint.'
Assert-Contains -Content $serverTemplate.embeddings.openAiEndpoint -Needle '<openai-resource>' -Message 'Server template must keep the OpenAI endpoint as a placeholder.'

$readme = Get-Content -LiteralPath (Get-RepoPath -RelativePath 'README.md') -Raw
Assert-Contains -Content $readme -Needle 'infra/main.bicep' -Message 'README must reference infra/main.bicep.'
Assert-Contains -Content $readme -Needle 'src/foundry_cosmos_demo/' -Message 'README must reference the live Python package path.'
Assert-Contains -Content $readme -Needle 'AZURE_OPENAI_BASE_URL' -Message 'README must document the seeder environment contract.'
Assert-Contains -Content $readme -Needle 'diskANN' -Message 'README must document the Cosmos vector index.'

$bicep = Get-Content -LiteralPath (Get-RepoPath -RelativePath 'infra\main.bicep') -Raw
Assert-Contains -Content $bicep -Needle "Microsoft.CognitiveServices/accounts@2025-06-01" -Message 'Bicep must create a Microsoft Foundry resource.'
Assert-Contains -Content $bicep -Needle "Microsoft.CognitiveServices/accounts/projects@2025-06-01" -Message 'Bicep must create a Foundry project.'
Assert-Contains -Content $bicep -Needle "name: 'text-embedding-3-small'" -Message 'Bicep must deploy text-embedding-3-small.'
Assert-Contains -Content $bicep -Needle "name: 'EnableNoSQLVectorSearch'" -Message 'Bicep must enable Cosmos vector search.'
Assert-Contains -Content $bicep -Needle "/embedding" -Message 'Bicep must use /embedding as the vector property.'
Assert-Contains -Content $bicep -Needle "type: 'diskANN'" -Message 'Bicep must use a DiskANN vector index.'
Assert-Contains -Content $bicep -Needle "disableLocalAuth: true" -Message 'Bicep must disable local auth for secretless posture.'
Assert-Contains -Content $bicep -Needle ".services.ai.azure.com/api/projects/" -Message 'Bicep must output the current Foundry project endpoint.'

$parameters = Read-JsonFile -RelativePath 'infra\main.parameters.json'
Assert-Contains -Content $parameters.parameters.environmentName.value -Needle '${AZURE_ENV_NAME}' -Message 'Parameter file must bind environmentName to AZURE_ENV_NAME.'
Assert-Contains -Content $parameters.parameters.location.value -Needle '${AZURE_LOCATION}' -Message 'Parameter file must bind location to AZURE_LOCATION.'
Assert-Contains -Content $parameters.parameters.localDeveloperPrincipalId.value -Needle '${DEPLOYER_PRINCIPAL_ID}' -Message 'Parameter file must bind localDeveloperPrincipalId to DEPLOYER_PRINCIPAL_ID.'
Assert-Contains -Content $parameters.parameters.embeddingModelVersion.value -Needle '${EMBEDDING_MODEL_VERSION=1}' -Message 'Parameter file must let azd override embeddingModelVersion via EMBEDDING_MODEL_VERSION.'

$azureYaml = Get-Content -LiteralPath (Get-RepoPath -RelativePath 'azure.yaml') -Raw
Assert-Contains -Content $azureYaml -Needle 'ignored .env.local' -Message 'azure.yaml must direct users to an explicitly ignored local env file.'

$seedFile = Get-Content -LiteralPath (Get-RepoPath -RelativePath 'src\foundry_cosmos_demo\seeder.py') -Raw
Assert-Contains -Content $seedFile -Needle 'DefaultAzureCredential' -Message 'Seeder must use DefaultAzureCredential.'
Assert-Contains -Content $seedFile -Needle 'OpenAI' -Message 'Seeder must use the OpenAI-compatible client surface.'
Assert-Contains -Content $seedFile -Needle 'CosmosClient' -Message 'Seeder must use the Cosmos DB SDK client.'
Assert-Contains -Content $seedFile -Needle 'embedding' -Message 'Seeder must populate the embedding field.'
Assert-Contains -Content $seedFile -Needle 'offline preview only (no Azure wiring validated).' -Message 'Seeder dry-run messaging must be honest when no Azure config is supplied.'
Assert-Contains -Content $seedFile -Needle 'Validated provided seeder configuration locally without calling Azure services.' -Message 'Seeder dry-run must document config validation when values are supplied.'

$envExample = Get-Content -LiteralPath (Get-RepoPath -RelativePath 'scripts\seeder.env.example') -Raw
Assert-Contains -Content $envExample -Needle 'AZURE_COSMOSDB_ENDPOINT=' -Message 'Seeder env example must document the Cosmos endpoint variable.'
Assert-Contains -Content $envExample -Needle 'AZURE_OPENAI_BASE_URL=' -Message 'Seeder env example must document the OpenAI-compatible base URL.'
Assert-Contains -Content $envExample -Needle 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small' -Message 'Seeder env example must pin the embedding deployment name.'

$vectorDoc = (Get-Content -LiteralPath (Get-RepoPath -RelativePath 'docs\azure-mcp-cli-vector-search-example.md') -Raw).Replace("`r`n", "`n")
$expectedCommand = @'
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
'@.Replace("`r`n", "`n")
Assert-Contains -Content $vectorDoc -Needle $expectedCommand -Message 'Vector-search documentation must contain the exact current Learn CLI example.'

$remoteSetupDoc = Get-Content -LiteralPath (Get-RepoPath -RelativePath 'docs\mcp-toolkit-remote-setup.md') -Raw
Assert-Matches -Content $remoteSetupDoc -Pattern 'AzureCosmosDB/MCPToolKit' -Message 'Remote setup documentation must cite MCPToolKit.'
Assert-Matches -Content $remoteSetupDoc -Pattern 'Setup-AIFoundry-Connection.ps1' -Message 'Remote setup documentation must explain the upstream Foundry connection flow.'

$publicSurfaceFiles = @(
    'docs\mcp-toolkit-remote-setup.md',
    'docs\azure-mcp-cli-vector-search-example.md',
    'templates\mcp\remote-foundry-cosmos-client.template.json',
    'templates\mcp\remote-foundry-cosmos-server.template.json',
    'templates\mcp\remote-foundry-cosmos.env.template',
    'scripts\seeder.env.example'
)

$publicSurfaceRules = @(
    @{
        Files = $publicSurfaceFiles
        Pattern = 'https://(?!<)[A-Za-z0-9-]+\.documents\.azure\.com(?::443/|/)'
        Message = 'Found a non-placeholder Cosmos endpoint in a public template.'
    },
    @{
        Files = $publicSurfaceFiles
        Pattern = 'https://(?!<)[A-Za-z0-9-]+\.openai\.azure\.com/'
        Message = 'Found a non-placeholder Azure OpenAI endpoint in a public template.'
    },
    @{
        Files = @(
            'templates\mcp\remote-foundry-cosmos-client.template.json',
            'templates\mcp\remote-foundry-cosmos.env.template'
        )
        Pattern = 'Bearer\s+(?!\$\{REMOTE_MCP_BEARER_TOKEN\})[A-Za-z0-9\-\._~+/]+=*'
        Message = 'Found a non-placeholder bearer token in a public template.'
    }
)

foreach ($relativePath in $publicSurfaceFiles) {
    $content = Get-Content -LiteralPath (Get-RepoPath -RelativePath $relativePath) -Raw
    foreach ($rule in $publicSurfaceRules) {
        if ($relativePath -notin $rule.Files) {
            continue
        }
        if ($content -match $rule.Pattern) {
            throw "$($rule.Message) File: $relativePath"
        }
    }
}

Write-Host 'Public repo surface validation passed.'
