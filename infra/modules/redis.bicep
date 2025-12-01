// Azure Cache for Redis
param location string
param namingPrefix string
param tags object

// Location abbreviation for naming
var locationAbbr = location == 'westeurope' ? 'westeurope' : location == 'northeurope' ? 'northeurope' : location == 'eastus' ? 'eastus' : location == 'eastus2' ? 'eastus2' : location

var redisName = 'red-${locationAbbr}-${namingPrefix}-01'

resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'Basic' // Basic for dev/staging, Standard/Premium for production
      family: 'C'
      capacity: 0 // C0 = 250MB, C1 = 1GB, C2 = 2.5GB, etc.
    }
    enableNonSslPort: false // Always use SSL
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru' // Eviction policy for cache
    }
    redisVersion: '6' // Redis 6.x
  }
}

// Outputs
output redisId string = redis.id
output redisName string = redis.name
output hostName string = redis.properties.hostName
output sslPort int = redis.properties.sslPort
output accessKey string = listKeys(redis.id, redis.apiVersion).primaryKey
output connectionString string = '${redis.properties.hostName}:${redis.properties.sslPort},password=${listKeys(redis.id, redis.apiVersion).primaryKey},ssl=True,abortConnect=False'
