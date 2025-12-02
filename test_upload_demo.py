import requests
import json
import time

BASE_URL = "https://app-we-magictoolbox-dev-01.calmisland-ca0bbf54.westeurope.azurecontainerapps.io"
API_URL = f"{BASE_URL}/api/v1"

print("=" * 60)
print("Testing PDF to DOCX Conversion via Django API")
print("=" * 60)

# Upload PDF
pdf_file = "demo_file.pdf"
url = f"{API_URL}/tools/pdf-docx-converter/convert/"

print(f"\n1. Uploading {pdf_file} to {url}")

with open(pdf_file, "rb") as f:
    files = {"file": ("demo_file.pdf", f, "application/pdf")}
    data = {"start_page": "0", "end_page": ""}

    response = requests.post(url, files=files, data=data)

    print(f"   Status Code: {response.status_code}")

    if response.status_code in [200, 201, 202]:
        try:
            result = response.json()
            print(f"   ✅ Upload successful!")
            print(f"\n2. Response data:")
            print(json.dumps(result, indent=2))

            # Check if we got an execution_id
            if "execution_id" in result or "executionId" in result:
                execution_id = result.get("execution_id") or result.get("executionId")
                print(f"\n3. Execution ID: {execution_id}")
                print(f"   Waiting for Azure Function to process...")

                # Wait a bit for processing
                time.sleep(5)

                # Check execution status
                status_url = f"{API_URL}/executions/{execution_id}/"
                print(f"\n4. Checking status at: {status_url}")
                status_response = requests.get(status_url)
                print(f"   Status Code: {status_response.status_code}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   Execution Status: {status_data.get('status', 'unknown')}")
                    print(f"   Full status data:")
                    print(json.dumps(status_data, indent=2))
        except json.JSONDecodeError:
            print(f"   Response (raw): {response.text[:500]}")
    else:
        print(f"   ❌ Upload failed")
        print(f"   Response: {response.text[:500]}")
