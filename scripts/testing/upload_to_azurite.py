#!/usr/bin/env python3
"""
Upload a file to local Azurite storage for testing Azure Functions blob triggers.
"""
import sys
from azure.storage.blob import BlobServiceClient
import uuid

# Local Azurite connection string (must match local.settings.json)
AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstorageaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstorageaccount1;"
)

def upload_file_to_azurite(source_file_path: str, target_filename: str = None):
    """Upload a file to Azurite for testing."""
    # Generate execution ID if not provided
    if target_filename is None:
        execution_id = str(uuid.uuid4())
        target_filename = f"uploads/pdf/{execution_id}.pdf"
    
    print(f"📤 Uploading to Azurite: {target_filename}")
    
    try:
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(AZURITE_CONNECTION_STRING)
        
        # Get container client
        container_name = "uploads"
        container_client = blob_service_client.get_container_client(container_name)
        
        # Ensure container exists
        try:
            container_client.create_container()
            print(f"✅ Created container: {container_name}")
        except Exception:
            print(f"ℹ️ Container {container_name} already exists")
        
        # Upload blob (extract blob name without container prefix)
        blob_name = target_filename.replace("uploads/", "") if target_filename.startswith("uploads/") else target_filename
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        
        with open(source_file_path, "rb") as data:
            file_content = data.read()
            print(f"📁 File size: {len(file_content):,} bytes")
            
            # Upload with metadata
            metadata = {
                "original_filename": "SF-F5-FR.pdf",
                "tool": "pdf_docx_converter",
                "upload_source": "test_script"
            }
            
            blob_client.upload_blob(file_content, overwrite=True, metadata=metadata)
            print(f"✅ Successfully uploaded to: {target_filename}")
            print(f"📊 Metadata: {metadata}")
            
            # Extract execution_id from filename
            if "/pdf/" in target_filename:
                execution_id = target_filename.split("/pdf/")[1].replace(".pdf", "")
                print(f"\n🆔 Execution ID: {execution_id}")
                print(f"🔍 Monitor logs with: tail -f /tmp/azure-functions.log | grep '{execution_id}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_to_azurite.py <source_file_path> [target_filename]")
        sys.exit(1)
    
    source_file = sys.argv[1]
    target_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = upload_file_to_azurite(source_file, target_name)
    sys.exit(0 if success else 1)
