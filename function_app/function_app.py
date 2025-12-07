"""
Minimal Azure Function for testing Flex Consumption deployment.
"""

import logging
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import psycopg2
from psycopg2 import sql
from pdf2docx import Converter

# Initialize Function App
app = func.FunctionApp()

# Configure logging - use both logger and print() for Azure Functions
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# Helper function to ensure logs are visible
def log(message, level="INFO"):
    """Log message using both print and logger for maximum visibility."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    formatted = f"[{timestamp}] {level}: {message}"
    print(formatted, flush=True)  # Force flush to ensure immediate output
    if level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)


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
        log(f"💾 Updating database for execution_id: {execution_id}")
        log(f"   Status: {status}")
        log("🔌 Getting database connection...")
        
        conn = get_db_connection()
        log(f"✅ Database connection established")
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
            log(f"   Output file: {output_file}")
            log(f"   Output filename: {output_filename}")
            log(f"   Output size: {output_size:,} bytes")
            
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
            log(f"   Error: {error}")
            
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
        
        log(f"🔄 Executing database update...")
        log(f"   Query: {query}")
        log(f"   Params: {params}")
        cursor.execute(query, params)
        log("✅ Query executed, committing...")
        conn.commit()
        log(f"✅ Database updated successfully. Rows affected: {cursor.rowcount}")
        
        if cursor.rowcount == 0:
            log(f"⚠️ WARNING: No rows were updated! Execution ID {execution_id} may not exist.", "WARNING")
        
        cursor.close()
        conn.close()
        log("   Database connection closed")
        
    except Exception as e:
        log(f"❌ Database update failed: {type(e).__name__}: {str(e)}", "ERROR")
        import traceback
        log(f"   Traceback: {traceback.format_exc()}", "ERROR")
        raise


# @app.route(route="convert/pdf-to-docx", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
# def pdf_to_docx_http(req: func.HttpRequest) -> func.HttpResponse:
#     """
#     HTTP-triggered PDF to DOCX conversion.
    
#     Request body should contain JSON:
#     {
#         "execution_id": "uuid-string",
#         "blob_name": "uploads/pdf/uuid.pdf"
#     }
#     """
#     request_id = str(uuid4())[:8]
#     log("=" * 80)
#     log("🎉 HTTP TRIGGER - PDF TO DOCX CONVERSION")
#     log(f"   Request ID: {request_id}")
#     log(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")
#     log(f"   Method: {req.method}")
#     log(f"   URL: {req.url}")
#     log("=" * 80)
    
#     try:
#         # Parse request body
#         log("📥 Step 1: Parsing request body...")
#         try:
#             req_body = req.get_json()
#             log(f"   Request body: {req_body}")
#         except Exception as parse_error:
#             log(f"❌ Failed to parse JSON: {parse_error}", "ERROR")
#             return func.HttpResponse(
#                 json.dumps({"error": f"Invalid JSON: {str(parse_error)}"}),
#                 status_code=400,
#                 mimetype="application/json"
#             )
        
#         execution_id = req_body.get("execution_id")
#         blob_name = req_body.get("blob_name")
        
#         log(f"   Execution ID: {execution_id}")
#         log(f"   Blob name: {blob_name}")
        
#         if not execution_id or not blob_name:
#             log("❌ Missing required parameters", "ERROR")
#             return func.HttpResponse(
#                 json.dumps({"error": "Missing execution_id or blob_name"}),
#                 status_code=400,
#                 mimetype="application/json"
#             )
        
#         log("✅ Request validation passed")
        
#         # Get blob service client
#         log("📦 Step 2: Initializing blob storage client...")
#         blob_service = get_blob_service_client()
#         log("✅ Blob service client initialized")
        
#         # Extract container and blob path
#         log(f"🔍 Step 3: Parsing blob name: {blob_name}")
#         parts = blob_name.split("/", 1)
#         if len(parts) != 2:
#             log(f"❌ Invalid blob_name format: {blob_name}", "ERROR")
#             return func.HttpResponse(
#                 json.dumps({"error": "Invalid blob_name format. Expected: container/path"}),
#                 status_code=400,
#                 mimetype="application/json"
#             )
        
#         container_name, blob_path = parts
#         log(f"   Container: {container_name}")
#         log(f"   Blob path: {blob_path}")
        
#         log("📦 Getting blob client...")
#         blob_client = blob_service.get_blob_client(container=container_name, blob=blob_path)
#         log("✅ Blob client obtained")
        
#         # Step 1: Update database status to 'processing'
#         log("=" * 80)
#         log("💾 Step 4: Updating database status to 'processing'...")
#         log(f"   Execution ID: {execution_id}")
#         try:
#             update_database_status(execution_id, "processing")
#             log("✅ Database status updated to 'processing'")
#         except Exception as db_error:
#             log(f"⚠️  Database update failed (continuing anyway): {db_error}", "WARNING")
#             import traceback
#             log(f"   Traceback: {traceback.format_exc()}", "WARNING")
        
#         # Step 2: Download PDF from blob storage
#         log("=" * 80)
#         log("📖 Step 5: Downloading PDF from blob storage...")
#         log(f"   Container: {container_name}")
#         log(f"   Blob: {blob_path}")
#         download_start = datetime.now(timezone.utc)
#         pdf_content = blob_client.download_blob().readall()
#         download_duration = (datetime.now(timezone.utc) - download_start).total_seconds()
#         log(f"✅ Downloaded {len(pdf_content):,} bytes in {download_duration:.2f}s")
#         log(f"   Download speed: {len(pdf_content) / download_duration / 1024:.2f} KB/s")
        
#         # Step 3: Convert PDF to DOCX
#         log("=" * 80)
#         log("🔄 Step 6: Converting PDF to DOCX...")
#         start_time = datetime.now(timezone.utc)
        
#         # Save PDF to temp file
#         log("💾 Creating temporary PDF file...")
#         with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
#             temp_pdf.write(pdf_content)
#             temp_pdf_path = temp_pdf.name
#         log(f"   Temp PDF path: {temp_pdf_path}")
#         log(f"   File size: {os.path.getsize(temp_pdf_path):,} bytes")
        
#         temp_docx_path = temp_pdf_path.replace(".pdf", ".docx")
#         log(f"   Target DOCX path: {temp_docx_path}")
        
#         try:
#             # Convert using pdf2docx
#             log("🔄 Initializing pdf2docx Converter...")
#             cv = Converter(temp_pdf_path)
#             log("   Converter initialized")
#             log("   Starting conversion (all pages)...")
#             cv.convert(temp_docx_path, start=0, end=None)
#             log("   Conversion completed")
#             cv.close()
#             log("   Converter closed")
            
#             conversion_time = (datetime.now(timezone.utc) - start_time).total_seconds()
#             docx_size = os.path.getsize(temp_docx_path)
#             log(f"✅ PDF to DOCX conversion completed successfully")
#             log(f"   Duration: {conversion_time:.2f}s")
#             log(f"   Input size: {len(pdf_content):,} bytes")
#             log(f"   Output size: {docx_size:,} bytes")
#             log(f"   Compression ratio: {(docx_size / len(pdf_content) * 100):.1f}%")
            
#             # Step 4: Upload DOCX to processed container
#             log("=" * 80)
#             log("📤 Step 7: Uploading DOCX to blob storage...")
#             log("   Reading DOCX file from disk...")
#             with open(temp_docx_path, "rb") as docx_file:
#                 docx_content = docx_file.read()
#             log(f"   Read {len(docx_content):,} bytes")
            
#             output_blob_name = f"docx/{execution_id}.docx"
#             log(f"   Target blob: processed/{output_blob_name}")
            
#             log("   Getting output blob client...")
#             output_blob_client = blob_service.get_blob_client(
#                 container="processed",
#                 blob=output_blob_name
#             )
#             log("   Output blob client obtained")
            
#             # Get original filename from blob metadata if available
#             log("   Retrieving original filename from source blob metadata...")
#             try:
#                 source_blob_client = blob_service.get_blob_client(container=container_name, blob=blob_path)
#                 blob_props = source_blob_client.get_blob_properties()
#                 original_filename = blob_props.metadata.get("original_filename", "document.pdf") if blob_props.metadata else "document.pdf"
#                 log(f"   Original filename: {original_filename}")
#             except Exception as meta_error:
#                 original_filename = "document.pdf"
#                 log(f"   Could not retrieve metadata: {meta_error}. Using default: {original_filename}", "WARNING")
            
#             log("   Uploading DOCX to processed container...")
#             upload_start = datetime.now(timezone.utc)
#             output_blob_client.upload_blob(docx_content, overwrite=True)
#             upload_duration = (datetime.now(timezone.utc) - upload_start).total_seconds()
#             log(f"✅ DOCX uploaded successfully")
#             log(f"   Blob: processed/{output_blob_name}")
#             log(f"   Size: {len(docx_content):,} bytes")
#             log(f"   Duration: {upload_duration:.2f}s")
#             log(f"   Upload speed: {len(docx_content) / upload_duration / 1024:.2f} KB/s")
            
#             # Step 5: Update database with success
#             log("=" * 80)
#             log("💾 Step 8: Updating database with completion status...")
#             output_filename = Path(original_filename).stem + ".docx"
#             log(f"   Output filename: {output_filename}")
#             log(f"   Output size: {len(docx_content):,} bytes")
#             try:
#                 update_database_status(
#                     execution_id=execution_id,
#                     status="completed",
#                     output_file=output_blob_name,
#                     output_filename=output_filename,
#                     output_size=len(docx_content)
#                 )
#                 log("✅ Database updated with completion status")
#             except Exception as db_error:
#                 log(f"❌ Database update failed: {db_error}", "ERROR")
#                 import traceback
#                 log(f"   Traceback: {traceback.format_exc()}", "ERROR")
            
#             log("=" * 80)
#             log("🎉 PDF TO DOCX CONVERSION COMPLETED SUCCESSFULLY!")
#             log(f"   Execution ID: {execution_id}")
#             log(f"   Total time: {(datetime.now(timezone.utc) - start_time).total_seconds():.2f}s")
#             log(f"   Input: {len(pdf_content):,} bytes (PDF)")
#             log(f"   Output: {len(docx_content):,} bytes (DOCX)")
#             log("=" * 80)
            
#             return func.HttpResponse(
#                 json.dumps({
#                     "status": "completed",
#                     "execution_id": execution_id,
#                     "output_blob": output_blob_name,
#                     "conversion_time_seconds": conversion_time
#                 }),
#                 status_code=200,
#                 mimetype="application/json"
#             )
            
#         finally:
#             # Cleanup temp files
#             if os.path.exists(temp_pdf_path):
#                 os.remove(temp_pdf_path)
#             if os.path.exists(temp_docx_path):
#                 os.remove(temp_docx_path)
    
#     except Exception as e:
#         logger.error(f"❌ Conversion failed: {type(e).__name__}: {str(e)}")
#         logger.error("=" * 80)
        
#         # Try to update database
#         try:
#             if 'execution_id' in locals():
#                 update_database_status(
#                     execution_id=execution_id,
#                     status="failed",
#                     error=f"{type(e).__name__}: {str(e)}"
#                 )
#         except Exception as db_error:
#             logger.error(f"❌ Failed to update database: {db_error}")
        
#         return func.HttpResponse(
#             json.dumps({
#                 "status": "failed",
#                 "error": f"{type(e).__name__}: {str(e)}"
#             }),
#             status_code=500,
#             mimetype="application/json"
#         )
# # Minimal Function App for testing
