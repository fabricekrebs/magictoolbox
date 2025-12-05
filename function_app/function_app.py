"""
Azure Function for PDF to DOCX conversion using HTTP trigger.
Flex Consumption plan with HTTP-triggered conversions for reliability.
"""

import logging
import tempfile
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from pdf2docx import Converter
import psycopg2

# Initialize Function App
app = func.FunctionApp()

# Configure logging - output to both file and stdout
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def get_blob_service_client() -> BlobServiceClient:
    """
    Get BlobServiceClient using Managed Identity or connection string.
    Supports both connection string format and service URI format.
    """
    # Check for service URI format (Managed Identity)
    blob_service_uri = os.environ.get("AzureWebJobsStorage__blobServiceUri")
    if blob_service_uri:
        logger.info(f"Using Managed Identity for storage: {blob_service_uri}")
        credential = DefaultAzureCredential()
        return BlobServiceClient(account_url=blob_service_uri, credential=credential)
    
    # Check for traditional connection string
    connection_string = os.environ.get("AzureWebJobsStorage")
    if connection_string:
        logger.info("Using connection string for storage")
        return BlobServiceClient.from_connection_string(connection_string)
    
    # Fallback: use account name from environment
    account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "sawemagictoolboxdev01")
    account_url = f"https://{account_name}.blob.core.windows.net"
    logger.info(f"Using Managed Identity for storage (fallback): {account_url}")
    credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=account_url, credential=credential)


def update_database_status(execution_id: str, status: str, output_file: str = None, 
                          output_filename: str = None, output_size: int = None, 
                          error: str = None) -> None:
    """
    Update the ToolExecution record in PostgreSQL database.
    
    Args:
        execution_id: UUID of the execution
        status: Status to set (processing, completed, failed)
        output_file: Path to output file in blob storage
        output_filename: Display name of output file
        output_size: Size of output file in bytes
        error: Error message if status is failed
    """
    try:
        logger.info(f"💾 Updating database for execution_id: {execution_id}")
        logger.info(f"   Status: {status}")
        
        # Get database connection parameters
        db_host = os.environ.get("DB_HOST")
        db_name = os.environ.get("DB_NAME")
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_port = os.environ.get("DB_PORT", "5432")
        
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port,
            sslmode="require",
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        
        # Build UPDATE query
        if status == "completed":
            query = """
                UPDATE tool_executions 
                SET status = %s, 
                    output_file = %s, 
                    output_filename = %s,
                    output_size = %s,
                    completed_at = %s,
                    updated_at = %s
                WHERE id = %s
            """
            params = (
                status,
                output_file,
                output_filename,
                output_size,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
                execution_id
            )
            logger.info(f"   Output file: {output_file}")
            logger.info(f"   Output filename: {output_filename}")
            logger.info(f"   Output size: {output_size:,} bytes")
            
        elif status == "failed":
            query = """
                UPDATE tool_executions 
                SET status = %s, 
                    error_message = %s,
                    completed_at = %s,
                    updated_at = %s
                WHERE id = %s
            """
            params = (
                status,
                error,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
                execution_id
            )
            logger.info(f"   Error: {error}")
            
        else:  # processing
            query = """
                UPDATE tool_executions 
                SET status = %s, 
                    updated_at = %s
                WHERE id = %s
            """
            params = (
                status,
                datetime.now(timezone.utc),
                execution_id
            )
        
        cursor.execute(query, params)
        rows_updated = cursor.rowcount
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Database updated successfully ({rows_updated} row(s) affected)")
        
    except Exception as e:
        logger.error(f"❌ Database update failed: {type(e).__name__}: {str(e)}")
        # Don't raise - we don't want database errors to fail the conversion


@app.function_name(name="ConnectivityCheck")
@app.route(route="health/connectivity", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def connectivity_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function to validate storage and database connectivity.
    Tests write, read, and delete operations for both services.
    """
    logger.info("=" * 80)
    logger.info("🔍 CONNECTIVITY CHECK STARTED")
    logger.info("=" * 80)
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": {
            "accessible": False,
            "write": {"success": False, "duration_ms": None, "error": None},
            "read": {"success": False, "duration_ms": None, "error": None},
            "delete": {"success": False, "duration_ms": None, "error": None},
            "details": {}
        },
        "database": {
            "accessible": False,
            "connect": {"success": False, "duration_ms": None, "error": None},
            "write": {"success": False, "duration_ms": None, "error": None},
            "read": {"success": False, "duration_ms": None, "error": None},
            "delete": {"success": False, "duration_ms": None, "error": None},
            "details": {}
        },
        "overall_status": "failed"
    }
    
    test_id = str(uuid4())[:8]
    
    # ========================================
    # STORAGE CONNECTIVITY TEST
    # ========================================
    logger.info("☁️ Testing Storage Account Connectivity...")
    try:
        blob_service = get_blob_service_client()
        results["storage"]["accessible"] = True
        results["storage"]["details"]["account_url"] = blob_service.account_name
        logger.info(f"✅ Storage client initialized: {blob_service.account_name}")
        
        # Test WRITE
        logger.info("📝 Testing WRITE operation...")
        try:
            start = datetime.now(timezone.utc)
            test_blob_name = f"connectivity-test/{test_id}.txt"
            test_content = f"Connectivity test at {results['timestamp']}"
            
            blob_client = blob_service.get_blob_client(
                container="uploads",
                blob=test_blob_name
            )
            blob_client.upload_blob(test_content.encode(), overwrite=True)
            
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            results["storage"]["write"]["success"] = True
            results["storage"]["write"]["duration_ms"] = round(duration, 2)
            results["storage"]["details"]["test_blob"] = test_blob_name
            logger.info(f"✅ WRITE successful ({duration:.2f}ms)")
            
        except Exception as e:
            results["storage"]["write"]["error"] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"❌ WRITE failed: {e}")
        
        # Test READ
        logger.info("📖 Testing READ operation...")
        try:
            start = datetime.now(timezone.utc)
            blob_client = blob_service.get_blob_client(
                container="uploads",
                blob=test_blob_name
            )
            blob_data = blob_client.download_blob().readall()
            
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            results["storage"]["read"]["success"] = True
            results["storage"]["read"]["duration_ms"] = round(duration, 2)
            results["storage"]["details"]["bytes_read"] = len(blob_data)
            logger.info(f"✅ READ successful ({duration:.2f}ms, {len(blob_data)} bytes)")
            
        except Exception as e:
            results["storage"]["read"]["error"] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"❌ READ failed: {e}")
        
        # Test DELETE
        logger.info("🗑️ Testing DELETE operation...")
        try:
            start = datetime.now(timezone.utc)
            blob_client = blob_service.get_blob_client(
                container="uploads",
                blob=test_blob_name
            )
            blob_client.delete_blob()
            
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            results["storage"]["delete"]["success"] = True
            results["storage"]["delete"]["duration_ms"] = round(duration, 2)
            logger.info(f"✅ DELETE successful ({duration:.2f}ms)")
            
        except Exception as e:
            results["storage"]["delete"]["error"] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"❌ DELETE failed: {e}")
        
    except Exception as e:
        results["storage"]["details"]["error"] = f"{type(e).__name__}: {str(e)}"
        logger.error(f"❌ Storage client initialization failed: {e}")
    
    # ========================================
    # DATABASE CONNECTIVITY TEST
    # ========================================
    logger.info("💾 Testing Database Connectivity...")
    try:
        # Get database connection parameters
        db_host = os.environ.get("DB_HOST")
        db_name = os.environ.get("DB_NAME")
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_port = os.environ.get("DB_PORT", "5432")
        
        results["database"]["details"]["host"] = db_host
        results["database"]["details"]["database"] = db_name
        results["database"]["details"]["user"] = db_user
        
        # Test CONNECTION
        logger.info("🔌 Testing DATABASE connection...")
        try:
            start = datetime.now(timezone.utc)
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port,
                sslmode="require",
                connect_timeout=10
            )
            
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            results["database"]["accessible"] = True
            results["database"]["connect"]["success"] = True
            results["database"]["connect"]["duration_ms"] = round(duration, 2)
            logger.info(f"✅ CONNECTION successful ({duration:.2f}ms)")
            
            cursor = conn.cursor()
            
            # Test WRITE (INSERT)
            logger.info("📝 Testing WRITE (INSERT) operation...")
            try:
                start = datetime.now(timezone.utc)
                
                # Create test table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS connectivity_tests (
                        id VARCHAR(50) PRIMARY KEY,
                        test_data TEXT,
                        created_at TIMESTAMP WITH TIME ZONE
                    )
                """)
                
                # Insert test record
                cursor.execute(
                    "INSERT INTO connectivity_tests (id, test_data, created_at) VALUES (%s, %s, %s)",
                    (test_id, f"Test at {results['timestamp']}", datetime.now(timezone.utc))
                )
                conn.commit()
                
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                results["database"]["write"]["success"] = True
                results["database"]["write"]["duration_ms"] = round(duration, 2)
                logger.info(f"✅ WRITE successful ({duration:.2f}ms)")
                
            except Exception as e:
                conn.rollback()
                results["database"]["write"]["error"] = f"{type(e).__name__}: {str(e)}"
                logger.error(f"❌ WRITE failed: {e}")
            
            # Test READ (SELECT)
            logger.info("📖 Testing READ (SELECT) operation...")
            try:
                start = datetime.now(timezone.utc)
                cursor.execute(
                    "SELECT id, test_data, created_at FROM connectivity_tests WHERE id = %s",
                    (test_id,)
                )
                row = cursor.fetchone()
                
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                results["database"]["read"]["success"] = True
                results["database"]["read"]["duration_ms"] = round(duration, 2)
                results["database"]["details"]["row_found"] = row is not None
                logger.info(f"✅ READ successful ({duration:.2f}ms, found: {row is not None})")
                
            except Exception as e:
                results["database"]["read"]["error"] = f"{type(e).__name__}: {str(e)}"
                logger.error(f"❌ READ failed: {e}")
            
            # Test DELETE
            logger.info("🗑️ Testing DELETE operation...")
            try:
                start = datetime.now(timezone.utc)
                cursor.execute(
                    "DELETE FROM connectivity_tests WHERE id = %s",
                    (test_id,)
                )
                rows_deleted = cursor.rowcount
                conn.commit()
                
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                results["database"]["delete"]["success"] = True
                results["database"]["delete"]["duration_ms"] = round(duration, 2)
                results["database"]["details"]["rows_deleted"] = rows_deleted
                logger.info(f"✅ DELETE successful ({duration:.2f}ms, {rows_deleted} row(s))")
                
            except Exception as e:
                conn.rollback()
                results["database"]["delete"]["error"] = f"{type(e).__name__}: {str(e)}"
                logger.error(f"❌ DELETE failed: {e}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            results["database"]["connect"]["error"] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"❌ DATABASE connection failed: {e}")
        
    except Exception as e:
        results["database"]["details"]["error"] = f"{type(e).__name__}: {str(e)}"
        logger.error(f"❌ Database test failed: {e}")
    
    # ========================================
    # OVERALL STATUS
    # ========================================
    storage_ok = (
        results["storage"]["accessible"] and
        results["storage"]["write"]["success"] and
        results["storage"]["read"]["success"] and
        results["storage"]["delete"]["success"]
    )
    
    database_ok = (
        results["database"]["accessible"] and
        results["database"]["connect"]["success"] and
        results["database"]["write"]["success"] and
        results["database"]["read"]["success"] and
        results["database"]["delete"]["success"]
    )
    
    if storage_ok and database_ok:
        results["overall_status"] = "healthy"
        status_code = 200
        logger.info("=" * 80)
        logger.info("✅ ALL CONNECTIVITY CHECKS PASSED")
        logger.info("=" * 80)
    elif storage_ok or database_ok:
        results["overall_status"] = "degraded"
        status_code = 207  # Multi-Status
        logger.warning("=" * 80)
        logger.warning("⚠️ SOME CONNECTIVITY CHECKS FAILED")
        logger.warning("=" * 80)
    else:
        results["overall_status"] = "unhealthy"
        status_code = 503  # Service Unavailable
        logger.error("=" * 80)
        logger.error("❌ ALL CONNECTIVITY CHECKS FAILED")
        logger.error("=" * 80)
    
    return func.HttpResponse(
        body=json.dumps(results, indent=2),
        status_code=status_code,
        mimetype="application/json"
    )


@app.route(route="convert/pdf-to-docx", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def pdf_to_docx_http(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered PDF to DOCX conversion (workaround for Flex Consumption blob trigger limitations).
    
    Request body should contain JSON:
    {
        "execution_id": "uuid-string",
        "blob_name": "uploads/pdf/uuid.pdf"
    }
    """
    logger.info("=" * 80)
    logger.info("🎉 HTTP TRIGGER - PDF TO DOCX CONVERSION")
    
    try:
        # Parse request body
        req_body = req.get_json()
        execution_id = req_body.get("execution_id")
        blob_name = req_body.get("blob_name")
        
        if not execution_id or not blob_name:
            return func.HttpResponse(
                json.dumps({"error": "Missing execution_id or blob_name"}),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"🆔 Execution ID: {execution_id}")
        logger.info(f"📄 Blob name: {blob_name}")
        
        # Get blob service client
        blob_service = get_blob_service_client()
        
        # Extract container and blob path
        parts = blob_name.split("/", 1)
        if len(parts) != 2:
            return func.HttpResponse(
                json.dumps({"error": "Invalid blob_name format. Expected: container/path"}),
                status_code=400,
                mimetype="application/json"
            )
        
        container_name, blob_path = parts
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_path)
        
        # Step 1: Update database status to 'processing'
        logger.info("⏳ Step 1: Updating database status to 'processing'...")
        update_database_status(execution_id, "processing")
        
        # Step 2: Download PDF from blob storage
        logger.info("📖 Step 2: Downloading PDF from blob storage...")
        pdf_content = blob_client.download_blob().readall()
        logger.info(f"✅ Downloaded {len(pdf_content):,} bytes")
        
        # Step 3: Convert PDF to DOCX
        logger.info("🔄 Step 3: Converting PDF to DOCX...")
        start_time = datetime.now(timezone.utc)
        
        # Save PDF to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf_path = temp_pdf.name
        
        temp_docx_path = temp_pdf_path.replace(".pdf", ".docx")
        
        try:
            # Convert using pdf2docx
            cv = Converter(temp_pdf_path)
            cv.convert(temp_docx_path, start=0, end=None)
            cv.close()
            
            conversion_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"✅ Conversion completed in {conversion_time:.2f}s")
            
            # Step 4: Upload DOCX to processed container
            logger.info("📤 Step 4: Uploading DOCX to blob storage...")
            with open(temp_docx_path, "rb") as docx_file:
                docx_content = docx_file.read()
            
            output_blob_name = f"docx/{execution_id}.docx"
            output_blob_client = blob_service.get_blob_client(
                container="processed",
                blob=output_blob_name
            )
            
            # Get original filename from blob metadata if available
            try:
                source_blob_client = blob_service.get_blob_client(container=container_name, blob=blob_path)
                blob_props = source_blob_client.get_blob_properties()
                original_filename = blob_props.metadata.get("original_filename", "document.pdf") if blob_props.metadata else "document.pdf"
            except:
                original_filename = "document.pdf"
            
            output_blob_client.upload_blob(docx_content, overwrite=True)
            logger.info(f"✅ Uploaded to: processed/{output_blob_name}")
            
            # Step 5: Update database with success
            logger.info("💾 Step 5: Updating database with results...")
            output_filename = Path(original_filename).stem + ".docx"
            update_database_status(
                execution_id=execution_id,
                status="completed",
                output_file=output_blob_name,
                output_filename=output_filename,
                output_size=len(docx_content)
            )
            
            logger.info("🎉 PDF to DOCX conversion completed successfully!")
            logger.info("=" * 80)
            
            return func.HttpResponse(
                json.dumps({
                    "status": "completed",
                    "execution_id": execution_id,
                    "output_blob": output_blob_name,
                    "conversion_time_seconds": conversion_time
                }),
                status_code=200,
                mimetype="application/json"
            )
            
        finally:
            # Cleanup temp files
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            if os.path.exists(temp_docx_path):
                os.remove(temp_docx_path)
    
    except Exception as e:
        logger.error(f"❌ Conversion failed: {type(e).__name__}: {str(e)}")
        logger.error("=" * 80)
        
        # Try to update database
        try:
            if 'execution_id' in locals():
                update_database_status(
                    execution_id=execution_id,
                    status="failed",
                    error=f"{type(e).__name__}: {str(e)}"
                )
        except Exception as db_error:
            logger.error(f"❌ Failed to update database: {db_error}")
        
        return func.HttpResponse(
            json.dumps({
                "status": "failed",
                "error": f"{type(e).__name__}: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        )
