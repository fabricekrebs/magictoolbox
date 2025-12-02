"""
Azure Function App for MagicToolbox - PDF to DOCX Conversion

This function is triggered when a PDF file is uploaded to the Azure Blob Storage
container 'uploads' with the path 'pdf/{name}'.

Architecture:
1. User uploads PDF via Django frontend
2. Django uploads to blob storage: uploads/pdf/{execution_id}.pdf
3. Blob trigger activates this Azure Function
4. Function converts PDF to DOCX
5. Function uploads result to: processed/docx/{execution_id}.docx
6. Function updates ToolExecution record in PostgreSQL
7. User polls Django API for status and downloads result
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import azure.functions as func
import psycopg2
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from pdf2docx import Converter

# Initialize Function App (Azure Functions v2 programming model)
app = func.FunctionApp()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_blob_service_client() -> BlobServiceClient:
    """
    Get BlobServiceClient using connection string for local dev or Managed Identity for Azure.

    Returns:
        BlobServiceClient configured appropriately for the environment
    """
    # Try connection string first (local development with Azurite)
    connection_string = os.environ.get("AzureWebJobsStorage")
    if connection_string and "127.0.0.1" in connection_string:
        logger.info("Using connection string for local development")
        return BlobServiceClient.from_connection_string(connection_string)

    # Use Managed Identity for Azure deployment
    storage_account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if not storage_account_name:
        raise ValueError("AZURE_STORAGE_ACCOUNT_NAME environment variable not set")

    logger.info(f"Using Managed Identity for Azure storage account: {storage_account_name}")
    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential()

    return BlobServiceClient(account_url=account_url, credential=credential)


def update_execution_status(
    execution_id: str,
    status: str,
    output_file: Optional[str] = None,
    output_filename: Optional[str] = None,
    output_size: Optional[int] = None,
    error_message: Optional[str] = None,
    error_traceback: Optional[str] = None,
) -> None:
    """
    Update ToolExecution record in database.

    Supports both SQLite (local development) and PostgreSQL (production).
    Environment detection based on DJANGO_DB_PATH or DB_HOST.

    Args:
        execution_id: UUID of the ToolExecution record
        status: Status to set (processing, completed, failed)
        output_file: URL/path to output file (for completed status)
        output_filename: Name of output file
        output_size: Size of output file in bytes
        error_message: Error message (for failed status)
        error_traceback: Full error traceback (for failed status)
    """
    # Detect database type from environment
    sqlite_path = os.environ.get("DJANGO_DB_PATH")
    db_host = os.environ.get("DB_HOST")

    # Determine which database to use
    use_sqlite = sqlite_path is not None
    use_postgres = db_host is not None

    if not use_sqlite and not use_postgres:
        logger.error("No database configuration found (DJANGO_DB_PATH or DB_HOST)")
        return

    try:
        # Normalize execution_id (remove hyphens for database query)
        # Django stores UUIDs without hyphens in SQLite
        execution_id_normalized = execution_id.replace("-", "")

        if use_sqlite:
            # SQLite connection for local development
            import sqlite3

            logger.info(f"Connecting to SQLite database: {sqlite_path}")
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()

            # SQLite queries (use ? placeholders and ISO format for timestamps)
            # Table name is tool_executions (not tools_toolexecution)
            if status == "processing":
                query = """
                    UPDATE tool_executions
                    SET status = ?, started_at = ?
                    WHERE id = ?
                """
                cursor.execute(
                    query, (status, datetime.now(timezone.utc).isoformat(), execution_id_normalized)
                )

            elif status == "completed":
                query = """
                    UPDATE tool_executions
                    SET status = ?,
                        completed_at = ?,
                        output_file = ?,
                        output_filename = ?,
                        output_size = ?,
                        duration_seconds = (
                            julianday(?) - julianday(started_at)
                        ) * 86400
                    WHERE id = ?
                """
                now = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    query,
                    (
                        status,
                        now,
                        output_file,
                        output_filename,
                        output_size,
                        now,
                        execution_id_normalized,
                    ),
                )

            elif status == "failed":
                query = """
                    UPDATE tool_executions
                    SET status = ?,
                        completed_at = ?,
                        error_message = ?,
                        error_traceback = ?,
                        duration_seconds = (
                            julianday(?) - julianday(started_at)
                        ) * 86400
                    WHERE id = ?
                """
                now = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    query,
                    (status, now, error_message, error_traceback, now, execution_id_normalized),
                )

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Updated execution {execution_id} to status: {status} (SQLite)")

        else:
            # PostgreSQL connection for production
            import psycopg2
            from psycopg2.extras import Json

            db_name = os.environ.get("DB_NAME")
            db_user = os.environ.get("DB_USER")
            db_password = os.environ.get("DB_PASSWORD")
            db_port = os.environ.get("DB_PORT", "5432")

            # Log environment variables for debugging (mask password)
            logger.info(f"DB_HOST: {db_host}")
            logger.info(f"DB_NAME: {db_name}")
            logger.info(f"DB_USER: {db_user}")
            logger.info(f"DB_PORT: {db_port}")
            logger.info(f"DB_PASSWORD present: {bool(db_password)}")
            logger.info(f"DB_PASSWORD length: {len(db_password) if db_password else 0}")

            if not all([db_host, db_name, db_user, db_password]):
                logger.error("PostgreSQL environment variables not complete")
                logger.error(f"Missing: db_host={bool(db_host)}, db_name={bool(db_name)}, db_user={bool(db_user)}, db_password={bool(db_password)}")
                return

            logger.info(f"Attempting to connect to PostgreSQL: {db_host}:{db_port}/{db_name} as {db_user}")
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port,
                sslmode="require",
            )

            cursor = conn.cursor()

            # PostgreSQL queries (use %s placeholders and EXTRACT for duration)
            if status == "processing":
                query = """
                    UPDATE tool_executions
                    SET status = %s, started_at = %s
                    WHERE id = %s
                """
                cursor.execute(query, (status, datetime.now(timezone.utc), execution_id))

            elif status == "completed":
                query = """
                    UPDATE tool_executions
                    SET status = %s,
                        completed_at = %s,
                        output_file = %s,
                        output_filename = %s,
                        output_size = %s,
                        duration_seconds = EXTRACT(EPOCH FROM (%s - started_at))
                    WHERE id = %s
                """
                cursor.execute(
                    query,
                    (
                        status,
                        datetime.now(timezone.utc),
                        output_file,
                        output_filename,
                        output_size,
                        datetime.now(timezone.utc),
                        execution_id,
                    ),
                )

            elif status == "failed":
                query = """
                    UPDATE tool_executions
                    SET status = %s,
                        completed_at = %s,
                        error_message = %s,
                        error_traceback = %s,
                        duration_seconds = EXTRACT(EPOCH FROM (%s - started_at))
                    WHERE id = %s
                """
                cursor.execute(
                    query,
                    (
                        status,
                        datetime.now(timezone.utc),
                        error_message,
                        error_traceback,
                        datetime.now(timezone.utc),
                        execution_id,
                    ),
                )

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"✅ Successfully updated execution {execution_id} to status: {status} (PostgreSQL)")

    except Exception as e:
        logger.error(f"❌ Failed to update execution status: {type(e).__name__}: {e}", exc_info=True)
        # Log additional context for debugging
        logger.error(f"Execution ID: {execution_id}, Status: {status}, DB Host: {os.environ.get('DB_HOST')}")


def convert_pdf_to_docx(
    pdf_stream: func.InputStream,
    start_page: int = 0,
    end_page: Optional[int] = None,
) -> Tuple[bytes, int]:
    """
    Convert PDF to DOCX format using pdf2docx library.

    Args:
        pdf_stream: Azure Function InputStream containing PDF data
        start_page: First page to convert (0-indexed)
        end_page: Last page to convert (None = all pages)

    Returns:
        Tuple of (docx_bytes, docx_size)
    """
    try:
        from pdf2docx import Converter
    except ImportError:
        raise ImportError("pdf2docx library not installed")

    temp_pdf = None
    temp_docx = None

    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(pdf_stream.read())
            temp_pdf = tmp_pdf.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
            temp_docx = tmp_docx.name

        # Convert PDF to DOCX
        logger.info(f"Converting PDF (pages: {start_page}-{end_page or 'end'})")

        cv = Converter(temp_pdf)
        cv.convert(temp_docx, start=start_page, end=end_page)
        cv.close()

        # Read DOCX file
        with open(temp_docx, "rb") as f:
            docx_bytes = f.read()

        docx_size = len(docx_bytes)
        logger.info(f"Conversion successful, DOCX size: {docx_size / 1024:.1f} KB")

        return docx_bytes, docx_size

    finally:
        # Cleanup temporary files
        if temp_pdf and os.path.exists(temp_pdf):
            os.unlink(temp_pdf)
        if temp_docx and os.path.exists(temp_docx):
            os.unlink(temp_docx)


@app.function_name(name="PdfToDocxConverter")
@app.route(route="pdf-to-docx", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def pdf_to_docx_converter(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function HTTP trigger to convert PDF to DOCX.

    Expected JSON body:
    {
        "execution_id": "uuid-string",
        "blob_name": "pdf/execution_id.pdf",
        "original_filename": "document.pdf",
        "start_page": 0,
        "end_page": null
    }

    Returns:
    - 200: Processing started successfully
    - 400: Invalid request
    - 500: Processing failed
    """
    try:
        logger.info("=== PDF to DOCX Conversion Started (HTTP Trigger) ===")
        
        # Log environment variables for debugging
        logger.info(f"Environment check - DB_HOST: {os.environ.get('DB_HOST', 'NOT SET')}")
        logger.info(f"Environment check - DB_NAME: {os.environ.get('DB_NAME', 'NOT SET')}")
        logger.info(f"Environment check - DB_USER: {os.environ.get('DB_USER', 'NOT SET')}")
        logger.info(f"Environment check - DB_PASSWORD present: {bool(os.environ.get('DB_PASSWORD'))}")

        # Parse request body
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                '{"error": "Invalid JSON in request body"}',
                status_code=400,
                mimetype="application/json",
            )

        # Validate required fields
        execution_id = req_body.get("execution_id")
        blob_name = req_body.get("blob_name")
        original_filename = req_body.get("original_filename", "document.pdf")

        if not execution_id or not blob_name:
            return func.HttpResponse(
                '{"error": "Missing required fields: execution_id, blob_name"}',
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Execution ID: {execution_id}")
        logger.info(f"Blob name: {blob_name}")
        logger.info(f"Original filename: {original_filename}")

        # Get conversion parameters
        start_page = int(req_body.get("start_page", 0))
        end_page = req_body.get("end_page")
        if end_page is not None:
            end_page = int(end_page)

        logger.info(f"Page range: {start_page} to {end_page or 'end'}")

        # Update status to processing
        update_execution_status(execution_id, "processing")

        # Download PDF from blob storage
        blob_service = get_blob_service_client()
        blob_client = blob_service.get_blob_client(container="uploads", blob=blob_name)

        # Download blob data
        pdf_data = blob_client.download_blob().readall()
        logger.info(f"Downloaded PDF: {len(pdf_data)} bytes")

        # Create a temporary file-like object for conversion
        import io

        class PdfStream:
            def __init__(self, data):
                self._data = data
                self._stream = io.BytesIO(data)

            def read(self):
                return self._data

        pdf_stream = PdfStream(pdf_data)

        # Convert PDF to DOCX
        docx_bytes, docx_size = convert_pdf_to_docx(
            pdf_stream=pdf_stream,
            start_page=start_page,
            end_page=end_page,
        )

        # Generate output blob name
        output_blob_name = f"docx/{execution_id}.docx"
        output_filename = Path(original_filename).stem + ".docx"

        # Upload DOCX to processed container
        output_blob_client = blob_service.get_blob_client(
            container="processed", blob=output_blob_name
        )

        output_blob_client.upload_blob(
            docx_bytes,
            overwrite=True,
            metadata={
                "execution_id": execution_id,
                "original_filename": original_filename,
                "converted_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"Uploaded DOCX to: processed/{output_blob_name}")

        # Update execution status to completed
        update_execution_status(
            execution_id=execution_id,
            status="completed",
            output_file=output_blob_name,
            output_filename=output_filename,
            output_size=docx_size,
        )

        logger.info("=== PDF to DOCX Conversion Completed Successfully ===")

        return func.HttpResponse(
            '{"status": "completed", "execution_id": "' + execution_id + '"}',
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error("=== PDF to DOCX Conversion Failed ===")
        logger.error(f"Error: {str(e)}", exc_info=True)

        # Update execution status to failed
        import traceback

        error_traceback = traceback.format_exc()

        if "execution_id" in locals():
            update_execution_status(
                execution_id=execution_id,
                status="failed",
                error_message=str(e),
                error_traceback=error_traceback,
            )

        return func.HttpResponse(
            '{"error": "' + str(e).replace('"', '\\"') + '"}',
            status_code=500,
            mimetype="application/json",
        )


@app.function_name(name="DatabaseDiagnostic")
@app.route(route="db-diagnostic", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def db_diagnostic(req: func.HttpRequest) -> func.HttpResponse:
    """
    Database connection diagnostic endpoint.
    
    GET /api/db-diagnostic
    
    Returns:
        200 OK with database connection test results
    """
    logger.info("Database diagnostic endpoint called")
    
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "environment_variables": {},
        "connection_test": {}
    }
    
    # Check environment variables
    db_host = os.environ.get("DB_HOST")
    db_name = os.environ.get("DB_NAME")
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_port = os.environ.get("DB_PORT", "5432")
    
    result["environment_variables"] = {
        "DB_HOST": db_host or "NOT_SET",
        "DB_NAME": db_name or "NOT_SET",
        "DB_USER": db_user or "NOT_SET",
        "DB_PORT": db_port,
        "DB_PASSWORD_SET": bool(db_password),
        "DB_PASSWORD_LENGTH": len(db_password) if db_password else 0,
        "DB_PASSWORD_IS_KEYVAULT_REF": "@Microsoft.KeyVault" in (db_password or ""),
        "DB_PASSWORD_FIRST_CHAR": db_password[0] if db_password else None,
    }
    
    # Test database connection
    if not all([db_host, db_name, db_user, db_password]):
        result["connection_test"]["status"] = "skipped"
        result["connection_test"]["reason"] = "Missing required environment variables"
        return func.HttpResponse(
            body=json.dumps(result, indent=2),
            status_code=200,
            mimetype="application/json"
        )
    
    try:
        logger.info(f"Testing PostgreSQL connection to {db_host}:{db_port}/{db_name} as {db_user}")
        
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port,
            connect_timeout=10,
            sslmode='require'
        )
        
        # Test basic query
        cursor = conn.cursor()
        cursor.execute("SELECT version(), current_database(), current_user;")
        db_version, db_name_connected, db_user_connected = cursor.fetchone()
        cursor.close()
        conn.close()
        
        result["connection_test"]["status"] = "success"
        result["connection_test"]["connected_to"] = {
            "database": db_name_connected,
            "user": db_user_connected,
            "version": db_version
        }
        logger.info("✅ Database connection test successful")
        
    except psycopg2.OperationalError as e:
        result["connection_test"]["status"] = "failed"
        result["connection_test"]["error_type"] = "OperationalError"
        result["connection_test"]["error_message"] = str(e)
        result["connection_test"]["error_details"] = {
            "pgcode": getattr(e, 'pgcode', None),
            "pgerror": getattr(e, 'pgerror', None),
        }
        logger.error(f"❌ Database connection failed (OperationalError): {e}")
        
    except psycopg2.Error as e:
        result["connection_test"]["status"] = "failed"
        result["connection_test"]["error_type"] = type(e).__name__
        result["connection_test"]["error_message"] = str(e)
        result["connection_test"]["error_details"] = {
            "pgcode": getattr(e, 'pgcode', None),
            "pgerror": getattr(e, 'pgerror', None),
        }
        logger.error(f"❌ Database connection failed ({type(e).__name__}): {e}")
        
    except Exception as e:
        result["connection_test"]["status"] = "failed"
        result["connection_test"]["error_type"] = type(e).__name__
        result["connection_test"]["error_message"] = str(e)
        logger.error(f"❌ Database connection failed (unexpected error): {e}", exc_info=True)
    
    return func.HttpResponse(
        body=json.dumps(result, indent=2),
        status_code=200,
        mimetype="application/json"
    )


@app.function_name(name="HttpTriggerTest")
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger_test(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple HTTP health check endpoint for testing.

    GET /api/health
    GET /api/health?debug=true (returns environment info)

    Returns:
        200 OK with function app status
    """
    logger.info("Health check endpoint called")
    
    # If debug parameter is provided, return environment info
    debug = req.params.get('debug', '').lower() == 'true'
    
    if debug:
        env_info = {
            "status": "healthy",
            "function": "pdf-to-docx-converter",
            "environment": {
                "DB_HOST": os.environ.get("DB_HOST", "NOT_SET"),
                "DB_NAME": os.environ.get("DB_NAME", "NOT_SET"),
                "DB_USER": os.environ.get("DB_USER", "NOT_SET"),
                "DB_PORT": os.environ.get("DB_PORT", "NOT_SET"),
                "DB_PASSWORD_SET": bool(os.environ.get("DB_PASSWORD")),
                "DB_PASSWORD_LENGTH": len(os.environ.get("DB_PASSWORD", "")),
                "DB_PASSWORD_IS_KEYVAULT_REF": "@Microsoft.KeyVault" in os.environ.get("DB_PASSWORD", ""),
                "AZURE_STORAGE_ACCOUNT_NAME": os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "NOT_SET"),
                "WEBSITE_VNET_ROUTE_ALL": os.environ.get("WEBSITE_VNET_ROUTE_ALL", "NOT_SET")
            }
        }
        return func.HttpResponse(
            body=json.dumps(env_info, indent=2),
            status_code=200,
            mimetype="application/json",
        )

    return func.HttpResponse(
        body='{"status": "healthy", "function": "pdf-to-docx-converter"}',
        status_code=200,
        mimetype="application/json",
    )
