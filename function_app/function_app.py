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
    Convert PDF to DOCX format.
    
    Expected JSON payload:
    {
        "execution_id": "uuid-string",
        "blob_name": "uploads/pdf/{uuid}.pdf"
    }
    
    Process:
    1. Download PDF from blob storage
    2. Convert to DOCX using pdf2docx
    3. Upload DOCX to blob storage
    4. Update database record with result
    """
    logger.info("=" * 100)
    logger.info("🚀 PDF TO DOCX CONVERSION STARTED")
    logger.info("=" * 100)
    
    start_time = datetime.now(timezone.utc)
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
        
        # Update database: set status to processing
        logger.info("-" * 100)
        logger.info("💾 UPDATING DATABASE: Setting status to 'processing'")
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE tool_executions SET status = 'processing', started_at = %s WHERE id = %s",
                    (start_time, execution_id)
                )
                conn.commit()
                logger.info(f"✅ Database updated: status = 'processing'")
        except Exception as db_error:
            logger.error(f"❌ Database update failed: {db_error}")
            logger.error(f"   This is non-fatal, continuing with conversion...")
        finally:
            if 'conn' in locals():
                conn.close()
        
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
        
        # Download PDF from blob storage
        logger.info("-" * 100)
        logger.info(f"⬇️  DOWNLOADING PDF FROM BLOB STORAGE")
        logger.info(f"   Blob: {blob_name}")
        
        try:
            # Remove 'uploads/' prefix if present (blob_name should be just the blob within container)
            if blob_name.startswith('uploads/'):
                actual_blob_name = blob_name.replace('uploads/', '', 1)
            else:
                actual_blob_name = blob_name
            
            logger.info(f"   Container: uploads")
            logger.info(f"   Blob path: {actual_blob_name}")
            
            input_blob_client = blob_service_client.get_blob_client(
                container="uploads",
                blob=actual_blob_name
            )
            
            # Check if blob exists
            if not input_blob_client.exists():
                logger.error(f"❌ Blob not found: uploads/{actual_blob_name}")
                raise Exception(f"Blob not found: {blob_name}")
            
            # Download blob
            pdf_data = input_blob_client.download_blob().readall()
            pdf_size = len(pdf_data)
            logger.info(f"✅ PDF downloaded successfully")
            logger.info(f"   Size: {pdf_size:,} bytes ({pdf_size / 1024 / 1024:.2f} MB)")
            
            # Get metadata for conversion parameters
            blob_properties = input_blob_client.get_blob_properties()
            metadata = blob_properties.metadata
            logger.info(f"   Metadata: {metadata}")
            
            original_filename = metadata.get('original_filename', 'document.pdf')
            start_page = int(metadata.get('start_page', 0))
            end_page_str = metadata.get('end_page', '')
            end_page = int(end_page_str) if end_page_str else None
            
            logger.info(f"   Original filename: {original_filename}")
            logger.info(f"   Conversion range: pages {start_page} to {end_page if end_page else 'end'}")
            
        except Exception as download_error:
            logger.error(f"❌ Failed to download PDF: {download_error}")
            logger.error(f"   Error type: {type(download_error).__name__}")
            raise
        
        # Convert PDF to DOCX
        logger.info("-" * 100)
        logger.info("🔄 CONVERTING PDF TO DOCX")
        
        import tempfile
        from pathlib import Path
        
        try:
            # Check if pdf2docx is available
            try:
                from pdf2docx import Converter
                logger.info("✅ pdf2docx library loaded")
            except ImportError:
                logger.error("❌ pdf2docx library not installed")
                raise ImportError("pdf2docx library not available")
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_pdf.write(pdf_data)
                temp_pdf_path = tmp_pdf.name
                logger.info(f"   Temporary PDF: {temp_pdf_path}")
            
            # Generate output filename
            output_filename = f"{Path(original_filename).stem}.docx"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
                temp_docx_path = tmp_docx.name
                logger.info(f"   Temporary DOCX: {temp_docx_path}")
            
            logger.info(f"   Starting conversion...")
            logger.info(f"   Parameters: start={start_page}, end={end_page}")
            
            # Perform conversion
            cv = Converter(temp_pdf_path)
            cv.convert(temp_docx_path, start=start_page, end=end_page)
            cv.close()
            
            # Get output file size
            output_size = os.path.getsize(temp_docx_path)
            logger.info(f"✅ Conversion completed successfully")
            logger.info(f"   Output file: {output_filename}")
            logger.info(f"   Output size: {output_size:,} bytes ({output_size / 1024 / 1024:.2f} MB)")
            
        except Exception as conversion_error:
            logger.error(f"❌ PDF conversion failed: {conversion_error}")
            logger.error(f"   Error type: {type(conversion_error).__name__}")
            
            # Cleanup temp files
            if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            if 'temp_docx_path' in locals() and os.path.exists(temp_docx_path):
                os.unlink(temp_docx_path)
            
            raise
        
        # Upload DOCX to blob storage
        logger.info("-" * 100)
        logger.info("⬆️  UPLOADING DOCX TO BLOB STORAGE")
        
        try:
            output_blob_name = f"docx/{execution_id}.docx"
            logger.info(f"   Container: processed")
            logger.info(f"   Blob: {output_blob_name}")
            
            output_blob_client = blob_service_client.get_blob_client(
                container="processed",
                blob=output_blob_name
            )
            
            with open(temp_docx_path, 'rb') as docx_file:
                output_blob_client.upload_blob(
                    docx_file,
                    overwrite=True,
                    metadata={
                        'execution_id': execution_id,
                        'original_filename': original_filename,
                        'output_filename': output_filename,
                        'converted_at': datetime.now(timezone.utc).isoformat()
                    }
                )
            
            logger.info(f"✅ DOCX uploaded successfully")
            logger.info(f"   Blob path: processed/{output_blob_name}")
            
        except Exception as upload_error:
            logger.error(f"❌ Failed to upload DOCX: {upload_error}")
            logger.error(f"   Error type: {type(upload_error).__name__}")
            
            # Cleanup temp files
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            if os.path.exists(temp_docx_path):
                os.unlink(temp_docx_path)
            
            raise
        
        # Cleanup temporary files
        logger.info("-" * 100)
        logger.info("🧹 CLEANING UP TEMPORARY FILES")
        try:
            os.unlink(temp_pdf_path)
            os.unlink(temp_docx_path)
            logger.info("✅ Temporary files cleaned up")
        except Exception as cleanup_error:
            logger.warning(f"⚠️  Cleanup warning: {cleanup_error}")
        
        # Update database: set status to completed
        logger.info("-" * 100)
        logger.info("💾 UPDATING DATABASE: Setting status to 'completed'")
        
        try:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE tool_executions 
                    SET status = 'completed',
                        completed_at = %s,
                        duration_seconds = %s,
                        output_filename = %s,
                        output_size = %s,
                        output_blob_path = %s
                    WHERE id = %s
                    """,
                    (end_time, duration, output_filename, output_size, f"processed/{output_blob_name}", execution_id)
                )
                conn.commit()
                
                logger.info(f"✅ Database updated successfully")
                logger.info(f"   Status: completed")
                logger.info(f"   Duration: {duration:.2f} seconds")
                logger.info(f"   Output filename: {output_filename}")
                logger.info(f"   Output size: {output_size:,} bytes")
                
        except Exception as db_error:
            logger.error(f"❌ Database update failed: {db_error}")
            logger.error(f"   Error type: {type(db_error).__name__}")
        finally:
            if 'conn' in locals():
                conn.close()
        
        # Success response
        logger.info("=" * 100)
        logger.info("✅ PDF TO DOCX CONVERSION COMPLETED SUCCESSFULLY")
        logger.info(f"   Execution ID: {execution_id}")
        logger.info(f"   Total duration: {duration:.2f} seconds")
        logger.info("=" * 100)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "output_filename": output_filename,
                "output_blob_path": f"processed/{output_blob_name}",
                "duration_seconds": duration,
                "input_size_bytes": pdf_size,
                "output_size_bytes": output_size
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        # Handle any errors
        logger.error("=" * 100)
        logger.error("❌ PDF TO DOCX CONVERSION FAILED")
        logger.error(f"   Execution ID: {execution_id}")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error("=" * 100)
        logger.error("Full traceback:", exc_info=True)
        
        # Update database: set status to failed
        if execution_id:
            try:
                logger.info("💾 Updating database: Setting status to 'failed'")
                conn = get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE tool_executions 
                        SET status = 'failed',
                            error_message = %s,
                            completed_at = %s
                        WHERE id = %s
                        """,
                        (str(e), datetime.now(timezone.utc), execution_id)
                    )
                    conn.commit()
                    logger.info("✅ Database updated with error status")
            except Exception as db_error:
                logger.error(f"❌ Failed to update database with error: {db_error}")
            finally:
                if 'conn' in locals():
                    conn.close()
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "error",
                "error": str(e),
                "execution_id": execution_id
            }),
            mimetype="application/json",
            status_code=500
        )
