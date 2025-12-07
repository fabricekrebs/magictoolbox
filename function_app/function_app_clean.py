"""
Simplified Azure Function for PDF to DOCX conversion.
Based on the working simple test, with conversion logic added.
"""

import logging
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from pdf2docx import Converter

# Initialize Function App
app = func.FunctionApp()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_blob_service_client() -> BlobServiceClient:
    """Get BlobServiceClient using connection string."""
    connection_string = os.environ.get("AzureWebJobsStorage")
    return BlobServiceClient.from_connection_string(connection_string)


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
        
        # Step 1: Read PDF content
        logger.info("📖 Reading PDF content...")
        pdf_content = blob.read()
        logger.info(f"✅ Read {len(pdf_content):,} bytes")
        
        # Step 2: Convert PDF to DOCX
        logger.info("🔄 Converting PDF to DOCX...")
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
        
        # Step 3: Upload DOCX to blob storage
        logger.info("☁️ Uploading DOCX to blob storage...")
        blob_service = get_blob_service_client()
        
        output_blob_name = f"docx/{execution_id}.docx"
        output_blob_client = blob_service.get_blob_client(
            container="processed",
            blob=output_blob_name
        )
        
        # Prepare metadata
        output_metadata = {
            "execution_id": execution_id,
            "original_filename": blob.metadata.get("original_filename", "document.pdf") if blob.metadata else "document.pdf",
            "source_blob": blob.name,
            "converted_at": datetime.now(timezone.utc).isoformat(),
        }
        
        output_blob_client.upload_blob(docx_content, overwrite=True, metadata=output_metadata)
        logger.info(f"✅ Uploaded to: processed/{output_blob_name}")
        logger.info(f"📊 Metadata: {output_metadata}")
        
        logger.info("=" * 80)
        logger.info("🎉 CONVERSION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ CONVERSION FAILED!")
        logger.error(f"Error: {type(e).__name__}: {str(e)}")
        logger.error("=" * 80)
        import traceback
        logger.error(traceback.format_exc())
        raise
