#!/usr/bin/env python3
"""
Setup script for local Azure Functions development environment.
Creates necessary blob storage containers in Azurite.
"""
from azure.storage.blob import BlobServiceClient

# Azurite default connection string
# Use UseDevelopmentStorage=true for automatic Azurite connection
AZURITE_ACCOUNT_URL = "http://127.0.0.1:10000/devstorageaccount1"
AZURITE_ACCOUNT_KEY = "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="

def setup_containers():
    """Create required blob containers for Azure Functions."""
    print("🔧 Setting up local Azure Storage containers...")
    
    try:
        # Connect to Azurite using account URL and key
        from azure.storage.blob import BlobServiceClient
        from azure.core.credentials import AzureNamedKeyCredential
        
        credential = AzureNamedKeyCredential("devstorageaccount1", AZURITE_ACCOUNT_KEY)
        blob_service_client = BlobServiceClient(
            account_url=AZURITE_ACCOUNT_URL,
            credential=credential
        )
        print("✓ Connected to Azurite")
        
        # Create containers
        containers = ["uploads", "processed"]
        
        for container_name in containers:
            try:
                container_client = blob_service_client.create_container(container_name)
                print(f"✓ Created container: {container_name}")
            except Exception as e:
                if "ContainerAlreadyExists" in str(e):
                    print(f"✓ Container already exists: {container_name}")
                else:
                    print(f"✗ Error creating container {container_name}: {e}")
        
        # Create subdirectories (blob prefixes)
        print("\n🔧 Setting up blob path structure...")
        
        # Upload a placeholder to create the pdf subdirectory
        container_client = blob_service_client.get_container_client("uploads")
        blob_client = container_client.get_blob_client("pdf/.placeholder")
        blob_client.upload_blob(b"", overwrite=True)
        print("✓ Created uploads/pdf/ path")
        
        # Upload a placeholder to create the docx subdirectory
        container_client = blob_service_client.get_container_client("processed")
        blob_client = container_client.get_blob_client("docx/.placeholder")
        blob_client.upload_blob(b"", overwrite=True)
        print("✓ Created processed/docx/ path")
        
        print("\n✅ Local Azure Storage setup complete!")
        print("\nContainer structure:")
        print("  uploads/")
        print("    └── pdf/        (PDF files uploaded here)")
        print("  processed/")
        print("    └── docx/       (DOCX files saved here)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Azurite is running:")
        print("  azurite --silent --location .azurite")
        return False
    
    return True

if __name__ == "__main__":
    setup_containers()
