"""
Simplified Azure Function for blob trigger testing.

This is a minimal test to validate that the blob trigger is working correctly.
It simply logs information when a new blob is uploaded.
"""

import logging
import azure.functions as func

# Initialize Function App
app = func.FunctionApp()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.function_name(name="BlobTriggerTest")
@app.blob_trigger(
    arg_name="blob",
    path="uploads/pdf/{name}",
    connection="AzureWebJobsStorage",
)
def blob_trigger_test(blob: func.InputStream) -> None:
    """
    Simple blob trigger test to validate the trigger is working.
    
    Triggered when ANY file is uploaded to: uploads/pdf/
    Logs basic information about the blob.
    """
    logger.info("=" * 80)
    logger.info("🎉 BLOB TRIGGER FIRED!")
    logger.info(f"📄 Blob name: {blob.name}")
    logger.info(f"📦 Blob size: {blob.length} bytes")
    logger.info(f"🔖 Blob URI: {blob.uri}")
    
    # Log metadata if available
    if blob.metadata:
        logger.info("📋 Blob metadata:")
        for key, value in blob.metadata.items():
            logger.info(f"   {key}: {value}")
    else:
        logger.info("📋 No metadata found")
    
    logger.info("=" * 80)
    logger.info("✅ Blob trigger test completed successfully")
