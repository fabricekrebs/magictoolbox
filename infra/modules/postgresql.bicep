// Azure Database for PostgreSQL Flexible Server
param location string
param namingPrefix string
param tags object
param administratorLogin string
param environment string

@secure()
param administratorLoginPassword string

// Location abbreviation for naming
var locationAbbr = location == 'westeurope' ? 'westeurope' : location == 'northeurope' ? 'northeurope' : location == 'italynorth' ? 'italynorth' : location == 'eastus' ? 'eastus' : location == 'eastus2' ? 'eastus2' : location

var postgresServerName = 'psql-${locationAbbr}-${namingPrefix}-01'
var databaseName = 'magictoolbox'

// Use same SKU for both dev and prod (cost-effective, reliable)
var skuTier = 'Burstable'
var skuName = 'Standard_B1ms'

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01' = {
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
    version: '17' // PostgreSQL 17 (latest stable)
    storage: {
      storageSizeGB: 32
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled' // Disabled to avoid region compatibility issues
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// Create the database
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2025-08-01' = {
  parent: postgresServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Allow Azure services and resources to access this server (includes Function Apps)
resource firewallRuleAllowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2025-08-01' = {
  parent: postgresServer
  name: 'AllowAllAzureServicesAndResourcesWithinAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
  dependsOn: [
    database
  ]
}

// PostgreSQL extensions configuration
// Must wait for database to be fully created before configuring extensions
resource postgresConfiguration 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2025-08-01' = {
  parent: postgresServer
  name: 'azure.extensions'
  properties: {
    value: 'uuid-ossp,pg_trgm,btree_gin,btree_gist'
    source: 'user-override'
  }
  dependsOn: [
    database
  ]
}

// Outputs
output postgresServerId string = postgresServer.id
output postgresServerName string = postgresServer.name
output fqdn string = postgresServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
