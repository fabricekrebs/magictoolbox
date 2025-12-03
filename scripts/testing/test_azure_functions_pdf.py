#!/usr/bin/env python3
"""
Test script for Azure Functions PDF to DOCX conversion.
Tests the complete async workflow: upload -> Azure Function processing -> result retrieval.
"""
import json
import os
import time

import requests

# Configuration
APP_URL = "https://app-we-magictoolbox-dev-01.calmisland-ca0bbf54.westeurope.azurecontainerapps.io"
USERNAME = "testuser"
EMAIL = "test@example.com"  # User model uses email for authentication
PASSWORD = "TestPass123"
PDF_FILE = "demo_file.pdf"


def login():
    """Authenticate and get JWT token."""
    print("=" * 80)
    print("Step 1: Authentication")
    print("=" * 80)

    # Login with JWT - User model uses email as USERNAME_FIELD
    login_url = f"{APP_URL}/api/v1/auth/api/login/"
    login_data = {"email": EMAIL, "password": PASSWORD}

    response = requests.post(login_url, json=login_data)

    if response.status_code == 200:
        result = response.json()
        access_token = result.get("access")
        if access_token:
            print(f"✅ Authentication successful as {USERNAME}")
            print(f"✅ JWT token obtained")
            return access_token
        else:
            print(f"❌ No access token in response")
            print(f"Response: {json.dumps(result, indent=2)}")
            return None
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response text: {response.text}")
        return None


def upload_pdf(access_token):
    """Upload PDF file for conversion."""
    print("\n" + "=" * 80)
    print("Step 2: Upload PDF for Async Conversion")
    print("=" * 80)

    if not os.path.exists(PDF_FILE):
        print(f"❌ PDF file not found: {PDF_FILE}")
        return None

    upload_url = f"{APP_URL}/api/v1/tools/pdf-docx-converter/convert/"

    with open(PDF_FILE, "rb") as f:
        files = {"file": (PDF_FILE, f, "application/pdf")}
        headers = {"Authorization": f"Bearer {access_token}"}

        print(f"Uploading {PDF_FILE} to {upload_url}")
        response = requests.post(upload_url, files=files, headers=headers)

    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")

    if response.status_code == 202:
        result = response.json()
        print(f"\n✅ SUCCESS: Azure Functions async processing initiated!")
        print(f"\nResponse:")
        print(json.dumps(result, indent=2))

        execution_id = result.get("executionId")
        if execution_id:
            print(f"\n📝 Execution ID: {execution_id}")
            return execution_id
        else:
            print("⚠️  No execution ID returned")
            return None
    elif response.status_code == 200:
        print("\n⚠️  WARNING: Synchronous processing (Azure Functions NOT used)")
        print("This means USE_AZURE_FUNCTIONS_PDF_CONVERSION is False")
        return None
    else:
        print(f"\n❌ ERROR: Upload failed with status {response.status_code}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response text: {response.text}")
        return None


def check_execution_status(access_token, execution_id):
    """Check the status of async execution."""
    print("\n" + "=" * 80)
    print("Step 3: Monitor Execution Status")
    print("=" * 80)

    status_url = f"{APP_URL}/api/v1/executions/{execution_id}/status/"
    max_attempts = 30
    poll_interval = 5

    print(f"Checking status at: {status_url}")
    print(f"Will poll every {poll_interval}s for up to {max_attempts} attempts")

    headers = {"Authorization": f"Bearer {access_token}"}

    for attempt in range(1, max_attempts + 1):
        time.sleep(poll_interval)

        try:
            response = requests.get(status_url, headers=headers)
            print(f"\n[Attempt {attempt}/{max_attempts}] Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                status = result.get("status", "").lower()
                print(f"Execution Status: {status}")

                if status == "completed":
                    print("\n✅ Processing completed successfully!")
                    print(f"\nFinal Result:")
                    print(json.dumps(result, indent=2))
                    return result
                elif status == "failed":
                    print(f"\n❌ Processing failed!")
                    print(f"Error: {result.get('error')}")
                    print(f"\nFull Response:")
                    print(json.dumps(result, indent=2))
                    return result
                elif status == "processing":
                    print("⏳ Still processing...")
                elif status == "pending":
                    print("⏳ Pending...")
                else:
                    print(f"Status: {status}")
            else:
                print(f"⚠️  Status check returned {response.status_code}")
                print(f"Response: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Error checking status: {e}")

    print(f"\n⏱️  Timeout: Processing did not complete within {max_attempts * poll_interval}s")
    return None


def verify_blob_upload(execution_id):
    """Verify that the PDF was uploaded to Azure Blob Storage."""
    print("\n" + "=" * 80)
    print("Step 4: Verify Blob Storage Upload")
    print("=" * 80)

    blob_name = f"pdf/{execution_id}.pdf"
    print(f"Expected blob: uploads/{blob_name}")

    try:
        result = os.popen(
            f"az storage blob exists "
            f"--account-name sawemagictoolboxdev01 "
            f"--container-name uploads "
            f"--name {blob_name} "
            f"--auth-mode login "
            f"-o json"
        ).read()

        blob_exists = json.loads(result).get("exists", False)
        if blob_exists:
            print(f"✅ PDF uploaded to blob storage successfully")
            return True
        else:
            print(f"❌ PDF not found in blob storage")
            return False
    except Exception as e:
        print(f"⚠️  Could not verify blob storage: {e}")
        return None


def check_processed_output(execution_id):
    """Check for the processed DOCX file in blob storage."""
    print("\n" + "=" * 80)
    print("Step 5: Check for Processed Output")
    print("=" * 80)

    docx_blob_name = f"docx/{execution_id}.docx"
    print(f"Expected output: processed/{docx_blob_name}")

    try:
        result = os.popen(
            f"az storage blob exists "
            f"--account-name sawemagictoolboxdev01 "
            f"--container-name processed "
            f"--name {docx_blob_name} "
            f"--auth-mode login "
            f"-o json"
        ).read()

        blob_exists = json.loads(result).get("exists", False)
        if blob_exists:
            print(f"✅ DOCX file found in processed container!")

            # Get blob properties
            props = os.popen(
                f"az storage blob show "
                f"--account-name sawemagictoolboxdev01 "
                f"--container-name processed "
                f"--name {docx_blob_name} "
                f"--auth-mode login "
                f"-o json"
            ).read()

            blob_props = json.loads(props)
            size = blob_props.get("properties", {}).get("contentLength", 0)
            print(f"File size: {size} bytes")
            return True
        else:
            print(f"❌ DOCX file not found in processed container")
            return False
    except Exception as e:
        print(f"⚠️  Could not check processed output: {e}")
        return None


def check_function_logs():
    """Check Azure Function logs for processing activity."""
    print("\n" + "=" * 80)
    print("Step 6: Check Azure Function Logs")
    print("=" * 80)

    try:
        print("Fetching recent Function App logs...")
        logs = os.popen(
            "az functionapp log tail "
            "--name func-magictoolbox-dev-rze6cb73hmijy "
            "--resource-group rg-westeurope-magictoolbox-dev-01 "
            "--timeout 5 2>&1 | head -30"
        ).read()

        if logs:
            print("Recent logs:")
            print(logs)
        else:
            print("No recent logs available")
    except Exception as e:
        print(f"⚠️  Could not fetch Function logs: {e}")


def main():
    """Run the complete test workflow."""
    print("\n" + "=" * 80)
    print("Azure Functions PDF to DOCX Conversion Test")
    print("=" * 80)
    print(f"Target: {APP_URL}")
    print(f"User: {USERNAME}")
    print(f"PDF: {PDF_FILE}")
    print("=" * 80)

    # Step 1: Login
    access_token = login()
    if not access_token:
        print("\n❌ Test failed: Could not authenticate")
        return False

    # Step 2: Upload PDF
    execution_id = upload_pdf(access_token)
    if not execution_id:
        print("\n❌ Test failed: Upload did not return execution ID")
        print("\nPossible issues:")
        print("1. USE_AZURE_FUNCTIONS_PDF_CONVERSION is False")
        print("2. Azure Functions configuration is incorrect")
        print("3. File processing happened synchronously")
        return False

    # Step 3: Verify blob upload
    verify_blob_upload(execution_id)

    # Step 4: Monitor execution status
    result = check_execution_status(access_token, execution_id)

    # Step 5: Check for output
    if result and result.get("status") == "completed":
        check_processed_output(execution_id)

    # Step 6: Check Function logs
    check_function_logs()

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
