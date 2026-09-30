targetScope = 'resourceGroup'

// API version note:
// - The Foundry quickstart confirms the required resource types are
//   Microsoft.CognitiveServices/accounts and Microsoft.CognitiveServices/accounts/projects.
// - These concrete API versions come from the current ARM/Bicep reference surface and should
//   be revisited if Microsoft promotes newer stable versions with schema changes.

@description('Azure region for all deployed resources.')
param location string = resourceGroup().location

@description('Short azd environment name used to derive globally unique resource names.')
@minLength(2)
param environmentName string

@description('Optional Microsoft Entra object ID for a local developer or automation principal that should be granted secretless access for running the Python seeder after provisioning. Leave empty to skip local-developer RBAC and rely only on the Foundry project managed identity.')
param localDeveloperPrincipalId string = ''

@description('Deployment name for the embedding model. Keeping the deployment name aligned with the underlying model makes the 1536-dimension contract obvious to repo consumers.')
param embeddingDeploymentName string = 'text-embedding-3-small'

@description('Model version for text-embedding-3-small. Version 1 is the current GA deployment shape that emits 1536-dimensional embeddings.')
param embeddingModelVersion string = '1'

@description('Capacity units for the embedding deployment.')
@minValue(1)
param embeddingDeploymentCapacity int = 8

@description('Max autoscale throughput for the Cosmos DB vector-search container.')
@minValue(1000)
param cosmosContainerMaxThroughput int = 4000

@description('Optional extra tags to apply to all resources.')
param tags object = {}

var normalizedEnvironment = toLower(replace(replace(environmentName, '-', ''), '_', ''))
var uniqueSuffix = toLower(uniqueString(subscription().subscriptionId, resourceGroup().id, environmentName))
var aiFoundryName = take('fd${normalizedEnvironment}${uniqueSuffix}', 24)
var aiProjectName = take('${aiFoundryName}-proj', 64)
var cosmosAccountName = take('cosmos${normalizedEnvironment}${uniqueSuffix}', 44)
var cosmosDatabaseName = 'care-guidance'
var cosmosContainerName = 'guidance'
var virtualNetworkName = 'vnet-${normalizedEnvironment}-${uniqueSuffix}'
var workloadSubnetName = 'workload'
var privateEndpointSubnetName = 'private-endpoints'
var foundryProjectEndpoint = 'https://${aiFoundryName}.services.ai.azure.com/api/projects/${aiProjectName}'
var openAiEndpoint = 'https://${aiFoundryName}.openai.azure.com/'
var openAiCompatibleBaseUrl = '${openAiEndpoint}openai/v1/'
var baseTags = union(
  {
    workload: 'synthetic-care-guidance'
    sample: 'foundry-cosmosdb-mcp-demo'
    authentication: 'entra-id-only'
  },
  tags
)
var openAiUserRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
)
var cosmosDataContributorRoleDefinitionId = '00000000-0000-0000-0000-000000000002'
var shouldAssignLocalDeveloper = !empty(localDeveloperPrincipalId)

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: aiFoundryName
  location: location
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: aiFoundryName
    disableLocalAuth: true
    dynamicThrottlingEnabled: false
    publicNetworkAccess: 'Enabled'
    restrictOutboundNetworkAccess: false
  }
  tags: baseTags
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  name: aiProjectName
  parent: aiFoundry
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'Synthetic care guidance discovery'
    description: 'Customer-agnostic Microsoft Foundry project for synthetic healthcare guidance discovery with Cosmos DB vector search.'
  }
  tags: baseTags
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  name: embeddingDeploymentName
  parent: aiFoundry
  sku: {
    name: 'GlobalStandard'
    capacity: embeddingDeploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: embeddingModelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
  tags: baseTags
  dependsOn: [
    aiProject
  ]
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    capabilities: [
      {
        name: 'EnableNoSQLVectorSearch'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    databaseAccountOfferType: 'Standard'
    disableKeyBasedMetadataWriteAccess: true
    disableLocalAuth: true
    enableAutomaticFailover: false
    enableFreeTier: false
    enableMultipleWriteLocations: false
    ipRules: []
    isVirtualNetworkFilterEnabled: false
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    minimalTlsVersion: 'Tls12'
    publicNetworkAccess: 'Disabled'
  }
  tags: baseTags
}

resource guidanceDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
  name: cosmosDatabaseName
  parent: cosmosAccount
  properties: {
    resource: {
      id: cosmosDatabaseName
    }
  }
}

resource guidanceContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  name: cosmosContainerName
  parent: guidanceDatabase
  properties: {
    options: {
      autoscaleSettings: {
        maxThroughput: cosmosContainerMaxThroughput
      }
    }
    resource: {
      id: cosmosContainerName
      partitionKey: {
        kind: 'Hash'
        paths: [
          '/conditionGroup'
        ]
        version: 2
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/_etag/?'
          }
          {
            path: '/embedding/*'
          }
        ]
        vectorIndexes: [
          {
            path: '/embedding'
            type: 'diskANN'
          }
        ]
      }
      vectorEmbeddingPolicy: {
        vectorEmbeddings: [
          {
            path: '/embedding'
            dataType: 'float32'
            distanceFunction: 'cosine'
            dimensions: 1536
          }
        ]
      }
    }
  }
}

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: virtualNetworkName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.42.0.0/16'
      ]
    }
    subnets: [
      {
        name: workloadSubnetName
        properties: {
          addressPrefix: '10.42.0.0/24'
          natGateway: {
            id: seederNatGateway.id
          }
        }
      }
      {
        name: privateEndpointSubnetName
        properties: {
          addressPrefix: '10.42.1.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
  tags: baseTags
}

resource seederNatPublicIp 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: 'pip-seeder-nat-${uniqueSuffix}'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
  tags: baseTags
}

resource seederNatGateway 'Microsoft.Network/natGateways@2024-05-01' = {
  name: 'nat-seeder-${uniqueSuffix}'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    idleTimeoutInMinutes: 10
    publicIpAddresses: [
      {
        id: seederNatPublicIp.id
      }
    ]
  }
  tags: baseTags
}

resource cosmosPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.documents.azure.com'
  location: 'global'
}

resource cosmosPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  name: 'link-${virtualNetworkName}'
  parent: cosmosPrivateDnsZone
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource cosmosPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${cosmosAccountName}'
  location: location
  properties: {
    subnet: {
      id: resourceId('Microsoft.Network/virtualNetworks/subnets', virtualNetwork.name, privateEndpointSubnetName)
    }
    privateLinkServiceConnections: [
      {
        name: 'cosmos-sql'
        properties: {
          privateLinkServiceId: cosmosAccount.id
          groupIds: [
            'Sql'
          ]
        }
      }
    ]
  }
  tags: baseTags
  dependsOn: [
    guidanceContainer
  ]
}

resource cosmosPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  name: 'default'
  parent: cosmosPrivateEndpoint
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cosmos-sql-zone'
        properties: {
          privateDnsZoneId: cosmosPrivateDnsZone.id
        }
      }
    ]
  }
}

resource projectOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiFoundry.id, aiProject.name, 'project-openai-user')
  scope: aiFoundry
  properties: {
    roleDefinitionId: openAiUserRoleDefinitionId
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    embeddingDeployment
  ]
}

resource localDeveloperOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (shouldAssignLocalDeveloper) {
  name: guid(aiFoundry.id, localDeveloperPrincipalId, openAiUserRoleDefinitionId)
  scope: aiFoundry
  properties: {
    roleDefinitionId: openAiUserRoleDefinitionId
    principalId: localDeveloperPrincipalId
  }
  dependsOn: [
    embeddingDeployment
  ]
}

resource projectCosmosContributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = {
  name: guid(cosmosAccount.id, aiProject.name, 'project-cosmos-data-contributor')
  parent: cosmosAccount
  properties: {
    principalId: aiProject.identity.principalId
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDataContributorRoleDefinitionId}'
    scope: cosmosAccount.id
  }
}

resource localDeveloperCosmosContributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = if (shouldAssignLocalDeveloper) {
  name: guid(cosmosAccount.id, localDeveloperPrincipalId, cosmosDataContributorRoleDefinitionId)
  parent: cosmosAccount
  properties: {
    principalId: localDeveloperPrincipalId
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDataContributorRoleDefinitionId}'
    scope: cosmosAccount.id
  }
}

output aiFoundryAccountName string = aiFoundry.name
output aiFoundryProjectName string = aiProject.name
output aiFoundryProjectResourceId string = aiProject.id
output aiFoundryProjectPrincipalId string = aiProject.identity.principalId
output aiFoundryProjectEndpoint string = foundryProjectEndpoint
output aiFoundryEndpoint string = aiFoundry.properties.endpoint
output openAiEndpoint string = openAiEndpoint
output openAiCompatibleBaseUrl string = openAiCompatibleBaseUrl
output embeddingDeploymentOutputName string = embeddingDeployment.name
output embeddingDimensions int = 1536
output cosmosAccountOutputName string = cosmosAccount.name
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output cosmosDatabaseOutputName string = guidanceDatabase.name
output cosmosContainerOutputName string = guidanceContainer.name
output vectorEmbeddingPath string = '/embedding'
output virtualNetworkOutputName string = virtualNetwork.name
output workloadSubnetOutputName string = workloadSubnetName
output workloadSubnetResourceId string = resourceId(
  'Microsoft.Network/virtualNetworks/subnets',
  virtualNetwork.name,
  workloadSubnetName
)
output localDeveloperRbacConfigured bool = shouldAssignLocalDeveloper
output seederEnvironmentHints object = {
  AZURE_COSMOSDB_CONTAINER_NAME: guidanceContainer.name
  AZURE_COSMOSDB_DATABASE_NAME: guidanceDatabase.name
  AZURE_COSMOSDB_ENDPOINT: cosmosAccount.properties.documentEndpoint
  AZURE_OPENAI_BASE_URL: openAiCompatibleBaseUrl
  AZURE_OPENAI_EMBEDDING_DEPLOYMENT: embeddingDeployment.name
  FOUNDRY_PROJECT_ENDPOINT: foundryProjectEndpoint
  OPENAI_ENDPOINT: openAiEndpoint
}
