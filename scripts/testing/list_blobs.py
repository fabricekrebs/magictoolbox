#!/usr/bin/env python3
"""
List all blobs in uploads and processed containers.
Uses Azure Managed Identity for authentication.
"""
import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

def list_blobs():
    """List all blobs in uploads and processed containers."""
    storage_account_name = "sawemagictoolboxdev01"
    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    
    print(f"🔐 Authenticating with Azure Managed Identity...")
    print(f"📦 Storage Account: {storage_account_name}")
    print()
    
    try:
        credential = DefaultAzureCredential()
        blob_service = BlobServiceClient(account_url=account_url, credential=credential)
        
        containers = ["uploads", "processed"]
        
        for container_name in containers:
            print(f"\n{'=' * 80}")
            print(f"📁 Container: {container_name}")
            print(f"{'=' * 80}")
            
            try:
                container_client = blob_service.get_container_client(container_name)
                blobs = list(container_client.list_blobs())
                
                if not blobs:
                    print(f"   (empty)")
                else:
                    print(f"\n   Total blobs: {len(blobs)}\n")
                    for idx, blob in enumerate(blobs, 1):
                        size_kb = blob.size / 1024
                        size_mb = size_kb / 1024
                        
                        if size_mb >= 1:
                            size_str = f"{size_mb:.2f} MB"
                        else:
                            size_str = f"{size_kb:.2f} KB"
                        
                        print(f"   {idx}. {blob.name}")
                        print(f"      Size: {size_str}")
                        print(f"      Last Modified: {blob.last_modified}")
                        print()
                        
            except Exception as e:
                print(f"   ❌ Error accessing container: {e}")
        
        print(f"\n{'=' * 80}")
        print("✅ Listing complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(list_blobs())
