#!/usr/bin/env python3
"""
Script to create required containers in Azurite for local development.
This script works around Azurite account validation issues by using direct HTTP requests.
"""
import subprocess
import time
import sys

# Required containers
CONTAINERS = ['uploads', 'processed', 'video-uploads', 'video-processed']

# Standard Azurite connection details
AZURITE_BLOB_ENDPOINT = "http://127.0.0.1:10000"
ACCOUNT_NAME = "devstorageaccount1"

def wait_for_azurite():
    """Wait for Azurite to be ready."""
    print("Waiting for Azurite to start...")
    for i in range(30):
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
                 f"{AZURITE_BLOB_ENDPOINT}/{ACCOUNT_NAME}?comp=list"],
                capture_output=True,
                text=True,
                timeout=2
            )
            # Even 404 means Azurite is responding
            if result.stdout:
                print(f"✓ Azurite is responding (HTTP {result.stdout})")
                return True
        except Exception:
            pass
        time.sleep(1)
    print("✗ Azurite failed to start")
    return False

def create_containers_via_azcopy():
    """Create containers using azcopy which might have better Azurite compatibility."""
    conn_str = f"DefaultEndpointsProtocol=http;AccountName={ACCOUNT_NAME};AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint={AZURITE_BLOB_ENDPOINT}/{ACCOUNT_NAME};"
    
    print("\nAttempting to create containers using Azure CLI...")
    for container in CONTAINERS:
        try:
            result = subprocess.run(
                ["az", "storage", "container", "create",
                 "--name", container,
                 "--connection-string", conn_str],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"✓ Created: {container}")
            else:
                if "ContainerAlreadyExists" in result.stderr or "already exists" in result.stderr:
                    print(f"✓ Exists: {container}")
                else:
                    print(f"✗ Failed {container}: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout creating {container}")
        except Exception as e:
            print(f"✗ Error creating {container}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Azurite Container Setup Script")
    print("=" * 60)
    
    if not wait_for_azurite():
        print("\nERROR: Azurite is not accessible. Please start Azurite first:")
        print("  docker compose up -d azurite")
        sys.exit(1)
    
    create_containers_via_azcopy()
    
    print("\n" + "=" * 60)
    print("NOTE: Due to Azurite 3.x account validation issues,")
    print("containers might not be created successfully.")
    print("For local testing, you may need to use Azure Storage Account")
    print("or downgrade to Azurite 2.x")
    print("=" * 60)
