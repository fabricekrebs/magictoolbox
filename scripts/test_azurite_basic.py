#!/usr/bin/env python3
"""Simple test to verify Azurite is working."""

from azure.storage.blob import BlobServiceClient

# Standard Azurite connection string
conn_str = "DefaultEndpointsProtocol=http;AccountName=devstorageaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstorageaccount1;"

print("Connecting to Azurite...")
blob_service = BlobServiceClient.from_connection_string(conn_str)

print("Creating test container...")
try:
    container_client = blob_service.create_container("test-container")
    print("✓ SUCCESS! Container created")
    
    print("Uploading test blob...")
    blob_client = container_client.get_blob_client("test.txt")
    blob_client.upload_blob("Hello Azurite!")
    print("✓ Blob uploaded")
    
    print("Listing containers...")
    for container in blob_service.list_containers():
        print(f"  - {container.name}")
    
    print("Cleaning up...")
    blob_service.delete_container("test-container")
    print("✓ Container deleted")
    
    print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
    
except Exception as e:
    print(f"✗ ERROR: {e}")
    exit(1)
