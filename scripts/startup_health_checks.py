#!/usr/bin/env python3
"""
Startup health checks for MagicToolbox Container App.
Tests connectivity to Azure Functions, Blob Storage, and Database.
"""
import os
import sys
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for Django imports
script_dir = Path(__file__).resolve().parent
app_dir = script_dir.parent
sys.path.insert(0, str(app_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magictoolbox.settings.production')

import django
django.setup()

import requests
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from django.db import connection
from django.conf import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class StartupHealthChecker:
    """Performs comprehensive health checks at container startup."""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checks': {},
            'overall_status': 'healthy'
        }
    
    def log_result(self, check_name: str, success: bool, message: str, details: dict = None):
        """Log and store check result."""
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} | {check_name}: {message}")
        
        self.results['checks'][check_name] = {
            'success': success,
            'message': message,
            'details': details or {}
        }
        
        if not success:
            self.results['overall_status'] = 'unhealthy'
    
    def check_azure_function_health(self) -> bool:
        """Test Azure Functions health endpoint."""
        logger.info("\n" + "=" * 80)
        logger.info("🔍 CHECKING AZURE FUNCTIONS CONNECTIVITY")
        logger.info("=" * 80)
        
        function_base_url = os.getenv('AZURE_FUNCTION_BASE_URL')
        
        if not function_base_url:
            self.log_result(
                'azure_functions',
                False,
                'AZURE_FUNCTION_BASE_URL not configured'
            )
            return False
        
        health_url = f"{function_base_url.rstrip('/api')}/api/health"
        logger.info(f"Testing: {health_url}")
        
        try:
            response = requests.get(health_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            self.log_result(
                'azure_functions',
                True,
                f'Health check successful (status: {data.get("status", "unknown")})',
                {
                    'url': health_url,
                    'status_code': response.status_code,
                    'response': data
                }
            )
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_result(
                'azure_functions',
                False,
                f'Failed to connect: {str(e)}',
                {'url': health_url, 'error': str(e)}
            )
            return False
    
    def check_blob_storage(self) -> bool:
        """Test blob storage read and write operations."""
        logger.info("\n" + "=" * 80)
        logger.info("🔍 CHECKING BLOB STORAGE CONNECTIVITY")
        logger.info("=" * 80)
        
        storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        
        if not storage_account_name and not connection_string:
            self.log_result(
                'blob_storage',
                False,
                'Storage account not configured'
            )
            return False
        
        try:
            # Get blob service client
            if connection_string and "127.0.0.1" in connection_string:
                logger.info("Using local Azurite")
                blob_service = BlobServiceClient.from_connection_string(connection_string)
            else:
                account_url = f"https://{storage_account_name}.blob.core.windows.net"
                logger.info(f"Using Azure Storage: {account_url}")
                
                client_id = os.getenv('AZURE_CLIENT_ID')
                if client_id:
                    logger.info(f"Using Managed Identity: {client_id}")
                else:
                    logger.info("Using default credential chain")
                
                credential = DefaultAzureCredential()
                blob_service = BlobServiceClient(account_url=account_url, credential=credential)
            
            # Test container: use 'deployments' container for health checks
            test_container = 'deployments'
            test_blob_name = f'health-check-{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt'
            test_content = f"Health check at {datetime.now(timezone.utc).isoformat()}"
            
            logger.info(f"Testing container: {test_container}")
            
            # Ensure container exists
            container_client = blob_service.get_container_client(test_container)
            if not container_client.exists():
                logger.info(f"Creating container: {test_container}")
                container_client.create_container()
            
            # Test write
            logger.info(f"Writing test blob: {test_blob_name}")
            blob_client = blob_service.get_blob_client(container=test_container, blob=test_blob_name)
            blob_client.upload_blob(test_content.encode('utf-8'), overwrite=True)
            logger.info("✅ Write successful")
            
            # Test read
            logger.info(f"Reading test blob: {test_blob_name}")
            downloaded_data = blob_client.download_blob().readall()
            downloaded_content = downloaded_data.decode('utf-8')
            
            if downloaded_content == test_content:
                logger.info("✅ Read successful - content matches")
            else:
                raise ValueError("Downloaded content doesn't match uploaded content")
            
            # Cleanup
            logger.info("Cleaning up test blob")
            blob_client.delete_blob()
            
            self.log_result(
                'blob_storage',
                True,
                'Read and write operations successful',
                {
                    'account': storage_account_name or 'local',
                    'container': test_container,
                    'test_blob': test_blob_name
                }
            )
            return True
            
        except Exception as e:
            self.log_result(
                'blob_storage',
                False,
                f'Failed: {str(e)}',
                {'error': str(e)}
            )
            return False
    
    def check_database(self) -> bool:
        """Test database read and write operations."""
        logger.info("\n" + "=" * 80)
        logger.info("🔍 CHECKING DATABASE CONNECTIVITY")
        logger.info("=" * 80)
        
        try:
            # Test connection
            with connection.cursor() as cursor:
                # Test write - create temporary table
                table_name = f'health_check_{datetime.now().strftime("%Y%m%d%H%M%S")}'
                logger.info(f"Creating temporary table: {table_name}")
                
                cursor.execute(f'''
                    CREATE TEMPORARY TABLE {table_name} (
                        id SERIAL PRIMARY KEY,
                        check_time TIMESTAMP,
                        status TEXT
                    )
                ''')
                logger.info("✅ Table created")
                
                # Test write
                test_time = datetime.now(timezone.utc)
                test_status = 'startup_health_check'
                
                logger.info("Inserting test record")
                cursor.execute(
                    f"INSERT INTO {table_name} (check_time, status) VALUES (%s, %s) RETURNING id",
                    [test_time, test_status]
                )
                inserted_id = cursor.fetchone()[0]
                logger.info(f"✅ Write successful (ID: {inserted_id})")
                
                # Test read
                logger.info("Reading test record")
                cursor.execute(f"SELECT id, check_time, status FROM {table_name} WHERE id = %s", [inserted_id])
                row = cursor.fetchone()
                
                if row and row[2] == test_status:
                    logger.info("✅ Read successful - data matches")
                else:
                    raise ValueError("Retrieved data doesn't match inserted data")
                
                # Cleanup
                logger.info("Dropping temporary table")
                cursor.execute(f"DROP TABLE {table_name}")
            
            db_config = settings.DATABASES.get('default', {})
            
            self.log_result(
                'database',
                True,
                'Read and write operations successful',
                {
                    'host': db_config.get('HOST'),
                    'name': db_config.get('NAME'),
                    'user': db_config.get('USER')
                }
            )
            return True
            
        except Exception as e:
            self.log_result(
                'database',
                False,
                f'Failed: {str(e)}',
                {'error': str(e)}
            )
            return False
    
    def run_all_checks(self) -> bool:
        """Run all health checks and return overall status."""
        logger.info("\n" + "=" * 80)
        logger.info("🏥 STARTING STARTUP HEALTH CHECKS")
        logger.info("=" * 80)
        logger.info(f"Timestamp: {self.results['timestamp']}")
        logger.info("=" * 80)
        
        # Run all checks
        self.check_database()
        self.check_blob_storage()
        self.check_azure_function_health()
        
        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 HEALTH CHECK SUMMARY")
        logger.info("=" * 80)
        
        for check_name, result in self.results['checks'].items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            logger.info(f"{status} | {check_name.upper()}: {result['message']}")
        
        logger.info("=" * 80)
        logger.info(f"OVERALL STATUS: {self.results['overall_status'].upper()}")
        logger.info("=" * 80 + "\n")
        
        return self.results['overall_status'] == 'healthy'


def main():
    """Main entry point."""
    checker = StartupHealthChecker()
    
    try:
        success = checker.run_all_checks()
        
        if not success:
            logger.error("⚠️  Some health checks failed, but continuing startup...")
            logger.error("The application may experience issues with failed services.")
            # Don't exit with error - allow container to start even with warnings
            # This prevents deployment failures due to temporary connectivity issues
            return 0
        
        logger.info("✅ All health checks passed!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Unexpected error during health checks: {e}")
        logger.error("Continuing startup despite error...")
        return 0


if __name__ == '__main__':
    sys.exit(main())
