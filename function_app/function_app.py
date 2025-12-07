"""
Minimal Azure Function for testing Flex Consumption deployment.
Provides diagnostic endpoints for storage, database, and health checks.
"""

import logging
import json
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import psycopg2

# Initialize Function App
app = func.FunctionApp()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    stream=sys.stdout,
    force=True
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
        'sslmode': os.environ.get('DB_SSLMODE', 'require')
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


@app.route(route="pdf/convert", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def convert_pdf_to_docx(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple PDF blob reader - Step 1.
    
    Expected JSON payload:
    {
        "execution_id": "uuid-string",
        "blob_name": "uploads/pdf/{uuid}.pdf"
    }
    
    Process:
    1. Read blob from storage
    2. Return metadata
    """
    logger.info("=" * 100)
    logger.info("🚀 PDF BLOB READER STARTED (SIMPLIFIED)")
    logger.info("=" * 100)
    
    execution_id = None
    blob_name = None
    
    try:
        # Parse request body
        logger.info("📥 Parsing request body...")
        try:
            req_body = req.get_json()
            execution_id = req_body.get('execution_id')
            blob_name = req_body.get('blob_name')
            
            logger.info(f"✅ Request parsed successfully")
            logger.info(f"   Execution ID: {execution_id}")
            logger.info(f"   Blob name: {blob_name}")
        except Exception as e:
            logger.error(f"❌ Failed to parse request body: {e}")
            return func.HttpResponse(
                body=json.dumps({"error": "Invalid JSON payload", "details": str(e)}),
                mimetype="application/json",
                status_code=400
            )
        
        if not execution_id or not blob_name:
            logger.error("❌ Missing required parameters")
            return func.HttpResponse(
                body=json.dumps({"error": "Missing execution_id or blob_name"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Initialize blob service client
        logger.info("-" * 100)
        logger.info("🔐 INITIALIZING BLOB STORAGE CLIENT")
        storage_account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
        if not storage_account_name:
            logger.error("❌ AZURE_STORAGE_ACCOUNT_NAME not configured")
            raise ValueError("AZURE_STORAGE_ACCOUNT_NAME not configured")
        
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        logger.info(f"   Storage URL: {account_url}")
        
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        logger.info("✅ Blob service client initialized")
        
        # Read blob metadata
        logger.info("-" * 100)
        logger.info(f"📖 READING BLOB METADATA")
        logger.info(f"   Blob: {blob_name}")
        
        try:
            # Remove 'uploads/' prefix if present
            if blob_name.startswith('uploads/'):
                actual_blob_name = blob_name.replace('uploads/', '', 1)
            else:
                actual_blob_name = blob_name
            
            logger.info(f"   Container: uploads")
            logger.info(f"   Blob path: {actual_blob_name}")
            
            blob_client = blob_service_client.get_blob_client(
                container="uploads",
                blob=actual_blob_name
            )
            
            # Check if blob exists
            if not blob_client.exists():
                logger.error(f"❌ Blob not found: uploads/{actual_blob_name}")
                raise Exception(f"Blob not found: {blob_name}")
            
            # Get blob properties
            blob_properties = blob_client.get_blob_properties()
            
            logger.info(f"✅ Blob found and accessible")
            logger.info(f"   Size: {blob_properties.size:,} bytes ({blob_properties.size / 1024 / 1024:.2f} MB)")
            logger.info(f"   Content Type: {blob_properties.content_settings.content_type}")
            logger.info(f"   Created: {blob_properties.creation_time}")
            logger.info(f"   Last Modified: {blob_properties.last_modified}")
            logger.info(f"   Metadata: {blob_properties.metadata}")
            
        except Exception as blob_error:
            logger.error(f"❌ Failed to read blob: {blob_error}")
            logger.error(f"   Error type: {type(blob_error).__name__}")
            raise
        
        # Success response
        logger.info("=" * 100)
        logger.info("✅ BLOB READ COMPLETED SUCCESSFULLY")
        logger.info(f"   Execution ID: {execution_id}")
        logger.info("=" * 100)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "blob_name": blob_name,
                "blob_info": {
                    "size_bytes": blob_properties.size,
                    "size_mb": round(blob_properties.size / 1024 / 1024, 2),
                    "content_type": blob_properties.content_settings.content_type,
                    "created": blob_properties.creation_time.isoformat(),
                    "last_modified": blob_properties.last_modified.isoformat(),
                    "metadata": dict(blob_properties.metadata)
                }
            }, indent=2),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        # Handle any errors
        logger.error("=" * 100)
        logger.error("❌ BLOB READ FAILED")
        logger.error(f"   Execution ID: {execution_id}")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error("=" * 100)
        logger.error("Full traceback:", exc_info=True)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "error",
                "error": str(e),
                "execution_id": execution_id,
                "error_type": type(e).__name__
            }),
            mimetype="application/json",
            status_code=500
        )
