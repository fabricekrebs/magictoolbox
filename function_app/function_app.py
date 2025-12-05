"""
Minimal Azure Function for testing Flex Consumption deployment.
"""

import logging
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import psycopg2
from psycopg2 import sql

# Initialize Function App
app = func.FunctionApp()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def get_blob_service_client() -> BlobServiceClient:
    """Get BlobServiceClient using Managed Identity."""
    storage_account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if not storage_account_name:
        raise ValueError("AZURE_STORAGE_ACCOUNT_NAME not configured")
    
    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    logger.info(f"Connecting to storage: {account_url}")
    
    credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=account_url, credential=credential)


def get_db_connection():
    """Get PostgreSQL database connection."""
    db_config = {
        'host': os.environ.get('DB_HOST'),
        'database': os.environ.get('DB_NAME'),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'port': os.environ.get('DB_PORT', '5432'),
        'sslmode': 'require'
    }
    
    logger.info(f"Connecting to database: {db_config['host']}/{db_config['database']}")
    return psycopg2.connect(**db_config)


@app.route(route="storage/test", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def test_storage(req: func.HttpRequest) -> func.HttpResponse:
    """
    Test blob storage read and write operations.
    """
    logger.info("Storage test endpoint called")
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "write": {"success": False, "error": None},
        "read": {"success": False, "error": None},
        "delete": {"success": False, "error": None}
    }
    
    try:
        # Get blob service client
        blob_service_client = get_blob_service_client()
        container_name = "uploads"
        test_blob_name = f"test-{uuid4()}.txt"
        test_content = f"Test blob created at {datetime.now(timezone.utc).isoformat()}"
        
        # Test 1: Write
        try:
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=test_blob_name)
            blob_client.upload_blob(test_content, overwrite=True)
            results["write"]["success"] = True
            results["write"]["blob_name"] = test_blob_name
            logger.info(f"Successfully wrote blob: {test_blob_name}")
        except Exception as e:
            results["write"]["error"] = str(e)
            logger.error(f"Write failed: {e}")
        
        # Test 2: Read (only if write succeeded)
        if results["write"]["success"]:
            try:
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=test_blob_name)
                downloaded_content = blob_client.download_blob().readall().decode('utf-8')
                results["read"]["success"] = (downloaded_content == test_content)
                results["read"]["content_match"] = results["read"]["success"]
                logger.info(f"Successfully read blob: {test_blob_name}")
            except Exception as e:
                results["read"]["error"] = str(e)
                logger.error(f"Read failed: {e}")
        
        # Test 3: Delete (cleanup)
        if results["write"]["success"]:
            try:
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=test_blob_name)
                blob_client.delete_blob()
                results["delete"]["success"] = True
                logger.info(f"Successfully deleted blob: {test_blob_name}")
            except Exception as e:
                results["delete"]["error"] = str(e)
                logger.error(f"Delete failed: {e}")
        
        results["overall_status"] = "success" if all([
            results["write"]["success"],
            results["read"]["success"],
            results["delete"]["success"]
        ]) else "partial"
        
    except Exception as e:
        results["overall_status"] = "failed"
        results["error"] = str(e)
        logger.error(f"Storage test failed: {e}")
    
    status_code = 200 if results.get("overall_status") in ["success", "partial"] else 500
    
    return func.HttpResponse(
        body=json.dumps(results, indent=2),
        mimetype="application/json",
        status_code=status_code
    )


@app.route(route="database/test", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def test_database(req: func.HttpRequest) -> func.HttpResponse:
    """
    Test database connection and operations.
    """
    logger.info("Database test endpoint called")
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "connect": {"success": False, "error": None},
        "query": {"success": False, "error": None, "row_count": 0}
    }
    
    conn = None
    try:
        # Test 1: Connect
        try:
            conn = get_db_connection()
            results["connect"]["success"] = True
            logger.info("Successfully connected to database")
        except Exception as e:
            results["connect"]["error"] = str(e)
            logger.error(f"Connection failed: {e}")
            
        # Test 2: Query (only if connection succeeded)
        if results["connect"]["success"] and conn:
            try:
                with conn.cursor() as cursor:
                    # Simple query to check if we can read from the database
                    cursor.execute("SELECT COUNT(*) FROM django_migrations;")
                    count = cursor.fetchone()[0]
                    results["query"]["success"] = True
                    results["query"]["row_count"] = count
                    logger.info(f"Successfully queried database: {count} migrations found")
            except Exception as e:
                results["query"]["error"] = str(e)
                logger.error(f"Query failed: {e}")
        
        results["overall_status"] = "success" if all([
            results["connect"]["success"],
            results["query"]["success"]
        ]) else "partial"
        
    except Exception as e:
        results["overall_status"] = "failed"
        results["error"] = str(e)
        logger.error(f"Database test failed: {e}")
    finally:
        if conn:
            conn.close()
    
    status_code = 200 if results.get("overall_status") in ["success", "partial"] else 500
    
    return func.HttpResponse(
        body=json.dumps(results, indent=2),
        mimetype="application/json",
        status_code=status_code
    )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple health check endpoint to verify Function App is working.
    """
    logger.info("Health check endpoint called")
    
    response_data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Azure Function is running successfully",
        "python_version": "3.11",
        "plan": "Flex Consumption"
    }
    
    return func.HttpResponse(
        body=json.dumps(response_data, indent=2),
        mimetype="application/json",
        status_code=200
    )


@app.route(route="echo", methods=["POST", "GET"], auth_level=func.AuthLevel.ANONYMOUS)
def echo(req: func.HttpRequest) -> func.HttpResponse:
    """
    Echo endpoint to test request handling.
    """
    logger.info(f"Echo endpoint called with method: {req.method}")
    
    # Get request data
    try:
        if req.method == "POST":
            req_body = req.get_json()
        else:
            req_body = {"message": "Use POST to echo JSON data"}
    except ValueError:
        req_body = {"error": "Invalid JSON in request body"}
    
    response_data = {
        "method": req.method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "received": req_body,
        "headers": dict(req.headers)
    }
    
    return func.HttpResponse(
        body=json.dumps(response_data, indent=2),
        mimetype="application/json",
        status_code=200
    )
# Minimal Function App for testing
