"""
Simplified Azure Function for PDF to DOCX conversion.
Based on the working simple test, with conversion logic added.
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
    """Get BlobServiceClient using connection string."""
    connection_string = os.environ.get("AzureWebJobsStorage")
    return BlobServiceClient.from_connection_string(connection_string)


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


@app.function_name(name="PdfToDocxConverter")
@app.blob_trigger(
    arg_name="blob",
    path="uploads/pdf/{name}",
    connection="AzureWebJobsStorage",
)
def pdf_to_docx_converter(blob: func.InputStream) -> None:
    """
    Convert PDF to DOCX when a new PDF is uploaded.
    """
    logger.info("=" * 80)
    logger.info("🎉 BLOB TRIGGER FIRED - PDF TO DOCX CONVERSION!")
    logger.info(f"📄 Blob name: {blob.name}")
    logger.info(f"📦 Blob size: {blob.length} bytes")
    logger.info(f"🔖 Blob URI: {blob.uri}")
    
    # Log metadata
    if blob.metadata:
        logger.info("📋 Blob metadata:")
        for key, value in blob.metadata.items():
            logger.info(f"   {key}: {value}")
    
    try:
        # Extract execution_id from blob name
        execution_id = Path(blob.name).stem
        logger.info(f"🆔 Execution ID: {execution_id}")
        
        # Step 1: Update database status to 'processing'
        logger.info("⏳ Step 1: Updating database status to 'processing'...")
        update_database_status(execution_id, "processing")
        
        # Step 2: Read PDF content
        logger.info("📖 Step 2: Reading PDF content...")
        pdf_content = blob.read()
        logger.info(f"✅ Read {len(pdf_content):,} bytes")
        
        # Step 3: Convert PDF to DOCX
        logger.info("🔄 Step 3: Converting PDF to DOCX...")
        start_time = datetime.now(timezone.utc)
        
        # Save PDF to temp file for conversion
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf_path = temp_pdf.name
        
        # Create temp file for DOCX output
        temp_docx_path = temp_pdf_path.replace(".pdf", ".docx")
        
        try:
            # Convert using pdf2docx
            cv = Converter(temp_pdf_path)
            cv.convert(temp_docx_path, start=0, end=None)
            cv.close()
            
            # Read converted DOCX
            with open(temp_docx_path, "rb") as f:
                docx_content = f.read()
            
            conversion_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"✅ Conversion completed in {conversion_time:.2f}s")
            logger.info(f"📦 DOCX size: {len(docx_content):,} bytes")
            
        finally:
            # Clean up temp files
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            if os.path.exists(temp_docx_path):
                os.unlink(temp_docx_path)
        
        # Step 4: Upload DOCX to blob storage
        logger.info("☁️ Step 4: Uploading DOCX to blob storage...")
        blob_service = get_blob_service_client()
        
        output_blob_name = f"docx/{execution_id}.docx"
        output_blob_client = blob_service.get_blob_client(
            container="processed",
            blob=output_blob_name
        )
        
        # Prepare metadata
        original_filename = blob.metadata.get("original_filename", "document.pdf") if blob.metadata else "document.pdf"
        output_metadata = {
            "execution_id": execution_id,
            "original_filename": original_filename,
            "source_blob": blob.name,
            "converted_at": datetime.now(timezone.utc).isoformat(),
        }
        
        output_blob_client.upload_blob(docx_content, overwrite=True, metadata=output_metadata)
        logger.info(f"✅ Uploaded to: processed/{output_blob_name}")
        logger.info(f"📊 Metadata: {output_metadata}")
        
        # Step 5: Update database status to 'completed'
        logger.info("✅ Step 5: Updating database status to 'completed'...")
        output_filename = Path(original_filename).stem + ".docx"
        update_database_status(
            execution_id=execution_id,
            status="completed",
            output_file=f"processed/{output_blob_name}",
            output_filename=output_filename,
            output_size=len(docx_content)
        )
        
        logger.info("=" * 80)
        logger.info("🎉 CONVERSION COMPLETED SUCCESSFULLY!")
        logger.info(f"⏱️ Total time: {(datetime.now(timezone.utc) - start_time).total_seconds():.2f}s")
        logger.info(f"📥 Input: {len(pdf_content):,} bytes")
        logger.info(f"📤 Output: {len(docx_content):,} bytes")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ CONVERSION FAILED!")
        logger.error(f"Error: {type(e).__name__}: {str(e)}")
        logger.error("=" * 80)
        import traceback
        logger.error(traceback.format_exc())
        
        # Update database status to 'failed'
        try:
            execution_id = Path(blob.name).stem
            logger.info("💾 Updating database status to 'failed'...")
            update_database_status(
                execution_id=execution_id,
                status="failed",
                error=f"{type(e).__name__}: {str(e)}"
            )
        except Exception as db_error:
            logger.error(f"❌ Failed to update database: {db_error}")
        
        raise
