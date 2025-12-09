"""
Full Azure Function for PDF to DOCX conversion with database tracking.
"""

import logging
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import psycopg2
from pdf2docx import Converter

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
    return psycopg2.connect(**db_config)


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        body=json.dumps({"status": "healthy", "message": "Azure Function is running successfully"}),
        mimetype="application/json",
        status_code=200
    )


@app.route(route="pdf/convert", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def convert_pdf_to_docx(req: func.HttpRequest) -> func.HttpResponse:
    """
    Full PDF to DOCX conversion workflow with database tracking.
    
    Expected JSON payload:
    {
        "execution_id": "uuid",
        "blob_name": "uploads/pdf/{uuid}.pdf"
    }
    """
    execution_id = None
    temp_pdf_path = None
    temp_docx_path = None
    
    try:
        logger.info("=" * 100)
        logger.info("🚀 PDF TO DOCX CONVERSION STARTED")
        logger.info("=" * 100)
        
        # Parse request body
        try:
            req_body = req.get_json()
            execution_id = req_body.get('execution_id')
            blob_name = req_body.get('blob_name')
            
            logger.info(f"📋 Request Details:")
            logger.info(f"   Execution ID: {execution_id}")
            logger.info(f"   Blob Name: {blob_name}")
            
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
        
        # Update database: processing
        logger.info("-" * 100)
        logger.info("📝 UPDATING DATABASE STATUS: processing")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tool_executions SET status = %s, updated_at = NOW() WHERE id = %s",
                ('processing', execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = processing")
        except Exception as db_error:
            logger.warning(f"⚠️ Failed to update database (continuing anyway): {db_error}")
        
        # Initialize blob service client
        logger.info("-" * 100)
        logger.info("🔐 INITIALIZING BLOB STORAGE CLIENT")
        blob_service_client = get_blob_service_client()
        logger.info("✅ Blob service client initialized")
        
        # Download PDF from blob storage
        logger.info("-" * 100)
        logger.info(f"📥 DOWNLOADING PDF FROM BLOB STORAGE")
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
            
            # Download to temp file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
                blob_data = blob_client.download_blob()
                temp_pdf.write(blob_data.readall())
            
            pdf_size = Path(temp_pdf_path).stat().st_size
            logger.info(f"✅ PDF downloaded to {temp_pdf_path}")
            logger.info(f"   Size: {pdf_size:,} bytes ({pdf_size / 1024 / 1024:.2f} MB)")
            
        except Exception as blob_error:
            logger.error(f"❌ Failed to download blob: {blob_error}")
            raise
        
        # Convert PDF to DOCX
        logger.info("-" * 100)
        logger.info(f"🔄 CONVERTING PDF TO DOCX")
        logger.info(f"   Input: {temp_pdf_path}")
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_docx:
                temp_docx_path = temp_docx.name
            
            logger.info(f"   Output: {temp_docx_path}")
            logger.info(f"   Starting conversion...")
            
            # Perform conversion
            cv = Converter(temp_pdf_path)
            cv.convert(temp_docx_path, start=0, end=None)
            cv.close()
            
            docx_size = Path(temp_docx_path).stat().st_size
            logger.info(f"✅ Conversion completed")
            logger.info(f"   Output size: {docx_size:,} bytes ({docx_size / 1024 / 1024:.2f} MB)")
            
        except Exception as convert_error:
            logger.error(f"❌ Conversion failed: {convert_error}")
            raise
        
        # Upload DOCX to blob storage
        logger.info("-" * 100)
        logger.info(f"📤 UPLOADING DOCX TO BLOB STORAGE")
        
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
                        'converted_at': datetime.now(timezone.utc).isoformat(),
                        'original_format': 'pdf',
                        'output_format': 'docx'
                    }
                )
            
            output_blob_path = f"processed/{output_blob_name}"
            logger.info(f"✅ DOCX uploaded successfully")
            logger.info(f"   Full path: {output_blob_path}")
            
        except Exception as upload_error:
            logger.error(f"❌ Upload failed: {upload_error}")
            raise
        
        # Update database: completed
        logger.info("-" * 100)
        logger.info("📝 UPDATING DATABASE STATUS: completed")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE tool_executions 
                   SET status = %s, 
                       output_blob_path = %s,
                       output_size = %s,
                       updated_at = NOW(),
                       completed_at = NOW()
                   WHERE id = %s""",
                ('completed', output_blob_path, docx_size, execution_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database updated: status = completed")
            logger.info(f"   Output blob path: {output_blob_path}")
            logger.info(f"   Output size: {docx_size:,} bytes")
        except Exception as db_error:
            logger.error(f"❌ Failed to update database: {db_error}")
            # Don't raise - conversion succeeded even if DB update failed
        
        # Cleanup temp files
        logger.info("-" * 100)
        logger.info("🧹 CLEANING UP TEMPORARY FILES")
        try:
            if temp_pdf_path and Path(temp_pdf_path).exists():
                Path(temp_pdf_path).unlink()
                logger.info(f"   Deleted: {temp_pdf_path}")
            if temp_docx_path and Path(temp_docx_path).exists():
                Path(temp_docx_path).unlink()
                logger.info(f"   Deleted: {temp_docx_path}")
            logger.info("✅ Cleanup completed")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Cleanup warning: {cleanup_error}")
        
        # Success response
        logger.info("=" * 100)
        logger.info("✅ PDF TO DOCX CONVERSION COMPLETED SUCCESSFULLY")
        logger.info(f"   Execution ID: {execution_id}")
        logger.info(f"   Input: {blob_name}")
        logger.info(f"   Output: {output_blob_path}")
        logger.info("=" * 100)
        
        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "execution_id": execution_id,
                "input_blob": blob_name,
                "output_blob": output_blob_path,
                "output_size_bytes": docx_size,
                "output_size_mb": round(docx_size / 1024 / 1024, 2)
            }, indent=2),
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
        
        # Update database: failed
        if execution_id:
            try:
                logger.info("📝 Updating database status: failed")
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE tool_executions 
                       SET status = %s, 
                           error_message = %s,
                           updated_at = NOW()
                       WHERE id = %s""",
                    ('failed', str(e), execution_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                logger.info("✅ Database updated: status = failed")
            except Exception as db_error:
                logger.error(f"❌ Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            if temp_pdf_path and Path(temp_pdf_path).exists():
                Path(temp_pdf_path).unlink()
            if temp_docx_path and Path(temp_docx_path).exists():
                Path(temp_docx_path).unlink()
        except:
            pass
        
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
