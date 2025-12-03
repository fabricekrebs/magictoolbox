#!/usr/bin/env python3
"""
Test PDF upload with authentication to trigger Azure Function blob trigger.
"""
import json
import time
import os
import sys

import requests

BASE_URL = "https://app-we-magictoolbox-dev-01.calmisland-ca0bbf54.westeurope.azurecontainerapps.io"
API_URL = f"{BASE_URL}/api/v1"

# Test credentials
TEST_EMAIL = "fabrice@services-web.ch"
TEST_PASSWORD = "suisse261286"

print("=" * 80)
print("Testing PDF to DOCX Conversion with Blob Trigger")
print("=" * 80)

# Step 1: Login
print(f"\n1. Logging in as {TEST_EMAIL}...")
login_url = f"{API_URL}/auth/api/login/"
login_data = {
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD
}

session = requests.Session()
response = session.post(login_url, json=login_data)

if response.status_code == 200:
    tokens = response.json()
    print(f"   ✅ Login successful!")
    access_token = tokens.get("access")
    
    # Set authorization header
    session.headers.update({
        "Authorization": f"Bearer {access_token}"
    })
else:
    print(f"   ❌ Login failed: {response.status_code}")
    print(f"   Response: {response.text}")
    print("\n   Note: You may need to create a test user first.")
    print(f"   Run: python scripts/testing/create_test_user.py")
    sys.exit(1)

# Step 2: Upload PDF
pdf_file = os.path.join(os.path.dirname(__file__), "../../tests/fixtures/demo_file.pdf")
upload_url = f"{API_URL}/tools/pdf-docx-converter/convert/"

print(f"\n2. Uploading {os.path.basename(pdf_file)} to {upload_url}")

with open(pdf_file, "rb") as f:
    files = {"file": ("demo_file.pdf", f, "application/pdf")}
    data = {"start_page": "0", "end_page": ""}

    response = session.post(upload_url, files=files, data=data)
    print(f"   Status Code: {response.status_code}")

    if response.status_code in [200, 201, 202]:
        try:
            result = response.json()
            print("   ✅ Upload successful!")
            print("\n3. Response data:")
            print(json.dumps(result, indent=2))

            # Check if we got an execution_id
            execution_id = result.get("execution_id") or result.get("executionId")
            if execution_id:
                print(f"\n4. Execution ID: {execution_id}")
                print("   📤 PDF uploaded to blob storage")
                print("   ⏳ Waiting for Azure Function blob trigger to fire...")
                print("   (This should happen within a few seconds)")
                
                # Wait for processing
                for i in range(6):
                    time.sleep(5)
                    print(f"   ... waiting {(i+1)*5}s")
                    
                    # Check execution status
                    status_url = f"{API_URL}/executions/{execution_id}/"
                    status_response = session.get(status_url)
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get("status", "unknown")
                        print(f"   📊 Current status: {status}")
                        
                        if status in ["completed", "failed", "error"]:
                            print(f"\n5. Final Status: {status}")
                            if status == "completed":
                                print("   ✅ PDF conversion completed successfully!")
                                output_url = status_data.get("output_url") or status_data.get("outputUrl")
                                if output_url:
                                    print(f"   📄 Output file: {output_url}")
                            else:
                                print(f"   ❌ Conversion failed")
                                error = status_data.get("error_message") or status_data.get("errorMessage")
                                if error:
                                    print(f"   Error: {error}")
                            break
                else:
                    print(f"\n   ⏰ Timeout waiting for completion")
                    print(f"   Check Azure Function App logs for processing status")
            else:
                print("   ⚠️  No execution_id in response")
                
        except json.JSONDecodeError:
            print(f"   Response (raw): {response.text[:500]}")
    else:
        print("   ❌ Upload failed")
        print(f"   Response: {response.text[:500]}")

print("\n" + "=" * 80)
print("Test completed")
print("=" * 80)
