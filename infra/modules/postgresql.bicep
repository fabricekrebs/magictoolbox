// Azure Database for PostgreSQL Flexible Server
param location string
param namingPrefix string
param uniqueSuffix string
param tags object
param administratorLogin string
param environment string

@secure()
param administratorLoginPassword string

// Location abbreviation for naming
var locationAbbr = location == 'westeurope' ? 'westeurope' : location == 'northeurope' ? 'northeurope' : location == 'eastus' ? 'eastus' : location == 'eastus2' ? 'eastus2' : location

var postgresServerName = 'psql-${locationAbbr}-${namingPrefix}-01'
var databaseName = 'magictoolbox'

// SKU tiers based on environment
var skuTier = environment == 'prod' ? 'GeneralPurpose' : 'Burstable'
var skuName = environment == 'prod' ? 'Standard_D2ds_v4' : 'Standard_B1ms'

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: postgresServerName
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword
    version: '15' // PostgreSQL 15
    storage: {
      storageSizeGB: environment == 'prod' ? 128 : 32
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: environment == 'prod' ? 14 : 7
      geoRedundantBackup: environment == 'prod' ? 'Enabled' : 'Disabled'
    }
    highAvailability: {
      mode: environment == 'prod' ? 'ZoneRedundant' : 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled' // Change to 'Disabled' with VNet integration for production
    }
  }
}

// Firewall rule to allow Azure services
resource firewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0' // Special rule to allow Azure services
  }
}

// Create the database
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// PostgreSQL extensions configuration
resource postgresConfiguration 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  parent: postgresServer
  name: 'azure.extensions'
  properties: {
    value: 'uuid-ossp,pg_trgm,btree_gin,btree_gist'
    source: 'user-override'
  }
}

// Outputs
output postgresServerId string = postgresServer.id
output postgresServerName string = postgresServer.name
output fqdn string = postgresServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
output connectionString string = 'postgresql://${administratorLogin}:${administratorLoginPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/${databaseName}?sslmode=require'
