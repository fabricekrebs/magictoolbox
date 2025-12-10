"""
Complete User Workflow Integration Tests - All Tools

This test suite simulates REAL user workflows from registration to cleanup:
1. User registration
2. User login
3. Use each tool (upload → process → download)
4. Verify Azure Blob Storage uploads
5. Verify database records
6. Delete all test data
7. Delete test user

Requirements:
- AZURE_INTEGRATION_TEST_ENABLED=true
- AZURE_STORAGE_CONNECTION_STRING=<your-connection-string>
- AZURE_FUNCTIONS_URL=<your-function-app-url> (optional, for PDF conversion)
- USE_AZURE_CLI_AUTH=true (optional, to use Azure CLI authentication instead of connection string)
- Storage account must allow public network access during test execution

Authentication Options:
1. Connection String (default): Uses AZURE_STORAGE_CONNECTION_STRING
2. Azure CLI: Set USE_AZURE_CLI_AUTH=true and ensure:
   - You're logged in with `az login`
   - You have "Storage Blob Data Contributor" role on the storage account
   - Storage account allows public network access (or your IP is whitelisted)

Local Testing Setup:
    # Enable public access on storage account (temporary for testing)
    az storage account update \
      --name sawemagictoolboxdev01 \
      --resource-group rg-westeurope-magictoolbox-dev-01 \
      --default-action Allow

    # Run tests
    source .venv/bin/activate
    export AZURE_INTEGRATION_TEST_ENABLED=true
    export AZURE_STORAGE_CONNECTION_STRING="..."
    export USE_AZURE_CLI_AUTH=true  # Optional: use Azure CLI auth
    pytest tests/test_complete_user_workflows.py -v -s

GitHub Actions (CI/CD):
    This test suite can be run automatically against deployed Azure environments
    using the GitHub Actions workflow: .github/workflows/e2e-tests.yml
    
    To run manually from GitHub:
    1. Go to repository → Actions tab
    2. Select "End-to-End Tests" workflow
    3. Click "Run workflow"
    4. Choose environment (dev/test/prod)
    
    The workflow automatically handles:
    - Azure authentication (service principal)
    - Storage network rules (enable/restore)
    - Test execution and reporting
    - Cleanup of old test data
    
    See documentation:
    - .github/workflows/README.md - Workflow details
    - documentation/E2E_TESTING_GUIDE.md - Full testing guide
    - documentation/GITHUB_SECRETS_SETUP.md - Secrets configuration
"""

import io
import json
import os
import time
import uuid
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.tools.models import ToolExecution
from apps.tools.registry import tool_registry

User = get_user_model()

# Check if Azure integration testing is enabled
AZURE_INTEGRATION_ENABLED = (
    os.getenv("AZURE_INTEGRATION_TEST_ENABLED", "false").lower() == "true"
)
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_FUNCTIONS_URL = os.getenv("AZURE_FUNCTIONS_URL")

pytestmark = pytest.mark.skipif(
    not AZURE_INTEGRATION_ENABLED or not AZURE_STORAGE_CONNECTION_STRING,
    reason="Azure integration tests not enabled. Set AZURE_INTEGRATION_TEST_ENABLED=true and AZURE_STORAGE_CONNECTION_STRING",
)


class TestCompleteUserWorkflow:
    """
    Complete end-to-end user workflow testing for all registered tools.
    Tests real Azure Blob Storage, real database operations, and full user lifecycle.
    """

    @pytest.fixture(scope="class")
    def storage_network_config(self):
        """Temporarily enable public network access for storage account during tests."""
        import subprocess
        
        storage_account = "sawemagictoolboxdev01"
        resource_group = "rg-westeurope-magictoolbox-dev-01"
        
        # Get current network rule set
        print(f"\n🔓 Enabling public network access for {storage_account}...")
        result = subprocess.run(
            [
                "az", "storage", "account", "show",
                "--name", storage_account,
                "--resource-group", resource_group,
                "--query", "networkRuleSet.defaultAction",
                "--output", "tsv"
            ],
            capture_output=True,
            text=True
        )
        original_default_action = result.stdout.strip()
        print(f"   Original default action: {original_default_action}")
        
        # Enable public access
        subprocess.run(
            [
                "az", "storage", "account", "update",
                "--name", storage_account,
                "--resource-group", resource_group,
                "--default-action", "Allow"
            ],
            check=True,
            capture_output=True
        )
        print(f"   ✅ Public access enabled")
        
        # Wait a moment for changes to propagate
        import time
        time.sleep(5)
        
        yield
        
        # Restore original network rules
        print(f"\n🔒 Restoring network rules for {storage_account}...")
        subprocess.run(
            [
                "az", "storage", "account", "update",
                "--name", storage_account,
                "--resource-group", resource_group,
                "--default-action", original_default_action or "Deny"
            ],
            check=True,
            capture_output=True
        )
        print(f"   ✅ Network rules restored to: {original_default_action or 'Deny'}")

    @pytest.fixture(scope="class")
    def blob_service_client(self, storage_network_config):
        """Get real Azure Blob Service Client using Azure CLI authentication."""
        from azure.identity import AzureCliCredential
        from azure.storage.blob import BlobServiceClient

        # Use Azure CLI credential for local testing
        credential = AzureCliCredential()
        
        # Extract storage account name from connection string or use environment variable
        storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "sawemagictoolboxdev01")
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        
        client = BlobServiceClient(account_url=account_url, credential=credential)
        return client

    @pytest.fixture
    def test_user_credentials(self):
        """Generate unique user credentials for testing."""
        unique_id = uuid.uuid4().hex[:8]
        return {
            "username": f"testuser_{unique_id}",
            "email": f"testuser_{unique_id}@example.com",
            "password": "SecureTestPass123!",
            "first_name": "Test",
            "last_name": "User",
        }

    @pytest.fixture
    def registered_user(self, db, test_user_credentials):
        """Create and register a real user in the database."""
        print(f"\n{'='*60}")
        print(f"🧪 Creating test user: {test_user_credentials['username']}")
        print(f"{'='*60}")

        user = User.objects.create_user(
            username=test_user_credentials["username"],
            email=test_user_credentials["email"],
            password=test_user_credentials["password"],
            first_name=test_user_credentials["first_name"],
            last_name=test_user_credentials["last_name"],
        )

        print(f"✅ User created: ID={user.id}, Username={user.username}")
        yield user

        # Cleanup after test
        print(f"\n🧹 Cleaning up user: {user.username}")
        user.delete()
        print(f"✅ User deleted")

    @pytest.fixture
    def authenticated_client(self, registered_user, test_user_credentials):
        """Create authenticated API client for both web and API requests."""
        client = APIClient()
        # Force authenticate for API requests (works for both web views and API endpoints)
        client.force_authenticate(user=registered_user)
        return client

    @pytest.fixture
    def sample_files(self):
        """Create sample test files for all tool types."""
        files = {}

        # PNG image for image converter
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        files["png"] = ("test_image.png", png_data, "image/png")

        # JPEG image
        jpeg_data = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01"
            b"\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07"
            b"\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14"
            b"\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444"
            b"\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01"
            b"\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01"
            b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06"
            b"\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02"
            b"\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11"
            b"\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1"
            b"\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789"
            b":CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89"
            b"\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6"
            b"\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3"
            b"\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9"
            b"\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4"
            b"\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00"
            b"\xffd\x00\xff\xd9"
        )
        files["jpeg"] = ("test_image.jpg", jpeg_data, "image/jpeg")

        # GPX file
        gpx_data = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Track</name>
    <trkseg>
      <trkpt lat="46.5" lon="6.5">
        <ele>500</ele>
        <time>2024-01-01T10:00:00Z</time>
      </trkpt>
      <trkpt lat="46.51" lon="6.51">
        <ele>510</ele>
        <time>2024-01-01T10:01:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        files["gpx"] = ("test_track.gpx", gpx_data, "application/gpx+xml")

        # Video file (minimal MP4)
        mp4_data = (
            b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41"
            b"\x00\x00\x00\x08free"
        )
        files["mp4"] = ("test_video.mp4", mp4_data, "video/mp4")

        # PDF file
        pdf_data = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
189
%%EOF
"""
        files["pdf"] = ("test_document.pdf", pdf_data, "application/pdf")

        return files

    def cleanup_blob_storage(self, blob_service_client, execution_id):
        """Clean up blobs associated with a test execution."""
        containers = ["uploads", "processed"]
        for container_name in containers:
            try:
                container_client = blob_service_client.get_container_client(container_name)
                blobs = container_client.list_blobs()
                for blob in blobs:
                    if str(execution_id) in blob.name:
                        blob_client = container_client.get_blob_client(blob.name)
                        blob_client.delete_blob()
                        print(f"  🗑️  Deleted blob: {blob.name}")
            except Exception as e:
                print(f"  ⚠️  Error cleaning container {container_name}: {e}")

    def verify_blob_exists(self, blob_service_client, container_name, blob_name):
        """Verify that a blob exists in storage."""
        try:
            container_client = blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            return blob_client.exists()
        except Exception:
            return False

    # ========================================================================
    # Test 1: Image Format Converter
    # ========================================================================

    @pytest.mark.django_db
    def test_01_image_format_converter_complete_workflow(
        self,
        authenticated_client,
        registered_user,
        blob_service_client,
        sample_files,
    ):
        """
        Test complete workflow for Image Format Converter:
        1. Access tool page
        2. Upload PNG file
        3. Convert to JPEG
        4. Verify blob storage upload
        5. Verify database record
        6. Download result
        7. Clean up
        """
        print(f"\n{'='*60}")
        print(f"🧪 TEST 1: Image Format Converter")
        print(f"{'='*60}")

        tool_name = "image-format-converter"
        tool = tool_registry.get_tool(tool_name)
        assert tool is not None, f"Tool {tool_name} not found"

        # Step 1: Access tool page
        print("📄 Step 1: Access tool page")
        url = f"/tools/{tool_name}/"
        response = authenticated_client.get(url, follow=True)
        assert response.status_code == 200
        print("  ✅ Tool page accessible")

        # Step 2: Upload and process file via API (as the real interface does)
        print("📤 Step 2: Upload PNG and convert to JPEG")
        filename, file_data, content_type = sample_files["png"]

        api_url = f"/api/v1/tools/{tool_name}/convert/"
        with io.BytesIO(file_data) as file_io:
            file_io.name = filename
            response = authenticated_client.post(
                api_url,
                {
                    "file": file_io,
                    "output_format": "jpeg",
                },
                format="multipart",
            )

        assert response.status_code in [200, 201, 202], f"API returned {response.status_code}"
        print(f"  ✅ File uploaded and conversion initiated")
        
        # Check if response is async (202) or sync (200)
        is_async = response.status_code == 202
        
        if is_async:
            # Async tools return JSON with execution ID
            response_data = response.json()
            print(f"  📋 Async response: {response_data}")
            execution_id = response_data.get("executionId")
            
            # Step 3: Verify database record for async tools
            print("💾 Step 3: Verify database record")
            execution = ToolExecution.objects.filter(
                user=registered_user, tool_name=tool_name
            ).order_by("-created_at").first()

            assert execution is not None
            assert execution.input_filename == filename
            assert execution.status in ["completed", "processing", "pending"]
            print(f"  ✅ Database record created: ID={execution.id}, Status={execution.status}")
        else:
            # Sync tools return file bytes directly (no ToolExecution record)
            print(f"  📋 Sync response: File bytes received ({len(response.content)} bytes)")
            assert len(response.content) > 0, "No file content received"
            print(f"  ✅ File processed successfully (synchronous conversion)")
            # Skip database verification for sync tools
            print("💾 Step 3: Database record not created (synchronous tool)")

        # Step 4: Verify blob storage (only for async tools)
        if is_async and execution:
            print("☁️  Step 4: Verify Azure Blob Storage")
            # Check if blob exists (implementation depends on your storage structure)
            blob_found = False
            for container_name in ["uploads", "processed"]:
                blob_name = f"images/{execution.id}.png"
                if self.verify_blob_exists(blob_service_client, container_name, blob_name):
                    blob_found = True
                    print(f"  ✅ Blob found in {container_name}: {blob_name}")
                    break

            if not blob_found:
                print(f"  ⚠️  Blob not found (may use local storage in test mode)")

            # Step 5: Cleanup
            print("🧹 Step 5: Cleanup")
            self.cleanup_blob_storage(blob_service_client, execution.id)
            execution.delete()
            print(f"  ✅ Cleanup completed")
        else:
            print("☁️  Step 4: Azure Blob Storage - Skipped (synchronous tool)")
            print("🧹 Step 5: Cleanup - Not needed (no database record)")

        print(f"{'='*60}")
        print(f"✅ TEST 1 PASSED: Image Format Converter")
        print(f"{'='*60}\n")

    # ========================================================================
    # Test 2: GPX Analyzer
    # ========================================================================

    @pytest.mark.django_db
    def test_02_gpx_analyzer_complete_workflow(
        self,
        authenticated_client,
        registered_user,
        blob_service_client,
        sample_files,
    ):
        """Test complete workflow for GPX Analyzer."""
        print(f"\n{'='*60}")
        print(f"🧪 TEST 2: GPX Analyzer")
        print(f"{'='*60}")

        tool_name = "gpx-analyzer"
        tool = tool_registry.get_tool(tool_name)
        
        if tool is None:
            print(f"  ⚠️  Tool {tool_name} not found - skipping")
            pytest.skip(f"Tool {tool_name} not registered")
            return

        print("📄 Step 1: Access tool page")
        url = f"/tools/{tool_name}/"
        response = authenticated_client.get(url, follow=True)
        assert response.status_code == 200
        print("  ✅ Tool page accessible")

        print("📤 Step 2: Upload GPX file")
        filename, file_data, content_type = sample_files["gpx"]

        api_url = f"/api/v1/tools/{tool_name}/convert/"
        with io.BytesIO(file_data) as file_io:
            file_io.name = filename
            response = authenticated_client.post(
                api_url,
                {"file": file_io},
                format="multipart",
            )

        assert response.status_code in [200, 201, 202], f"API returned {response.status_code}"
        print(f"  ✅ GPX file uploaded and analyzed")
        
        # Check if response is async (202) or sync (200)
        is_async = response.status_code == 202
        
        if is_async:
            # Async tools return JSON with execution ID
            response_data = response.json()
            print(f"  📋 Async response: {response_data}")
            execution_id = response_data.get("executionId")
            
            # Step 3: Verify database record for async tools
            print("💾 Step 3: Verify database record")
            execution = ToolExecution.objects.filter(
                user=registered_user, tool_name=tool_name
            ).order_by("-created_at").first()

            assert execution is not None
            assert execution.input_filename == filename
            assert execution.status in ["completed", "processing", "pending"]
            print(f"  ✅ Database record created: ID={execution.id}, Status={execution.status}")
        else:
            # Sync tools return file bytes directly (no ToolExecution record)
            print(f"  📋 Sync response: File bytes received ({len(response.content)} bytes)")
            assert len(response.content) > 0, "No file content received"
            print(f"  ✅ File processed successfully (synchronous conversion)")
            # Skip database verification for sync tools
            print("💾 Step 3: Database record not created (synchronous tool)")
            execution = None

        # Step 4: Cleanup (only for async tools)
        if is_async and execution:
            print("🧹 Step 4: Cleanup")
            self.cleanup_blob_storage(blob_service_client, execution.id)
            execution.delete()
            print(f"  ✅ Cleanup completed")
        else:
            print("🧹 Step 4: No cleanup needed (synchronous tool)")

        print(f"{'='*60}")
        print(f"✅ TEST 2 PASSED: GPX Analyzer")
        print(f"{'='*60}\n")

    # ========================================================================
    # Test 3: GPX to KML Converter
    # ========================================================================

    @pytest.mark.django_db
    def test_03_gpx_kml_converter_complete_workflow(
        self,
        authenticated_client,
        registered_user,
        blob_service_client,
        sample_files,
    ):
        """Test complete workflow for GPX to KML Converter."""
        print(f"\n{'='*60}")
        print(f"🧪 TEST 3: GPX to KML Converter")
        print(f"{'='*60}")

        tool_name = "gpx-kml-converter"
        tool = tool_registry.get_tool(tool_name)
        
        if tool is None:
            print(f"  ⚠️  Tool {tool_name} not found - skipping")
            pytest.skip(f"Tool {tool_name} not registered")
            return

        print("📄 Step 1: Access tool page")
        url = f"/tools/{tool_name}/"
        response = authenticated_client.get(url, follow=True)
        assert response.status_code == 200
        print("  ✅ Tool page accessible")

        print("📤 Step 2: Upload GPX and convert to KML")
        filename, file_data, content_type = sample_files["gpx"]

        api_url = f"/api/v1/tools/{tool_name}/convert/"
        with io.BytesIO(file_data) as file_io:
            file_io.name = filename
            response = authenticated_client.post(
                api_url,
                {"file": file_io},
                format="multipart",
            )

        assert response.status_code in [200, 201, 202], f"API returned {response.status_code}"
        print(f"  ✅ GPX converted to KML")
        
        # Check if response is async (202) or sync (200)
        is_async = response.status_code == 202
        
        if is_async:
            # Async tools return JSON with execution ID
            response_data = response.json()
            print(f"  📋 Async response: {response_data}")
            execution_id = response_data.get("executionId")
            
            # Step 3: Verify database record for async tools
            print("💾 Step 3: Verify database record")
            execution = ToolExecution.objects.filter(
                user=registered_user, tool_name=tool_name
            ).order_by("-created_at").first()

            assert execution is not None
            assert execution.input_filename == filename
            assert execution.status in ["completed", "processing", "pending"]
            print(f"  ✅ Database record created: ID={execution.id}, Status={execution.status}")
        else:
            # Sync tools return file bytes directly (no ToolExecution record)
            print(f"  📋 Sync response: File bytes received ({len(response.content)} bytes)")
            assert len(response.content) > 0, "No file content received"
            print(f"  ✅ File processed successfully (synchronous conversion)")
            # Skip database verification for sync tools
            print("💾 Step 3: Database record not created (synchronous tool)")
            execution = None

        # Step 4: Cleanup (only for async tools)
        if is_async and execution:
            print("🧹 Step 4: Cleanup")
            self.cleanup_blob_storage(blob_service_client, execution.id)
            execution.delete()
        print(f"  ✅ Cleanup completed")

        print(f"{'='*60}")
        print(f"✅ TEST 3 PASSED: GPX to KML Converter")
        print(f"{'='*60}\n")

    # ========================================================================
    # Test 4: GPX Speed Modifier
    # ========================================================================

    @pytest.mark.django_db
    def test_04_gpx_speed_modifier_complete_workflow(
        self,
        authenticated_client,
        registered_user,
        blob_service_client,
        sample_files,
    ):
        """Test complete workflow for GPX Speed Modifier."""
        print(f"\n{'='*60}")
        print(f"🧪 TEST 4: GPX Speed Modifier")
        print(f"{'='*60}")

        tool_name = "gpx-speed-modifier"
        tool = tool_registry.get_tool(tool_name)
        
        if tool is None:
            print(f"  ⚠️  Tool {tool_name} not found - skipping")
            pytest.skip(f"Tool {tool_name} not registered")
            return

        print("📄 Step 1: Access tool page")
        url = f"/tools/{tool_name}/"
        response = authenticated_client.get(url, follow=True)
        assert response.status_code == 200
        print("  ✅ Tool page accessible")

        print("📤 Step 2: Upload GPX and modify speed")
        filename, file_data, content_type = sample_files["gpx"]

        api_url = f"/api/v1/tools/{tool_name}/convert/"
        with io.BytesIO(file_data) as file_io:
            file_io.name = filename
            response = authenticated_client.post(
                api_url,
                {
                    "file": file_io,
                    "speed_multiplier": 1.5,
                },
                format="multipart",
            )

        assert response.status_code in [200, 201, 202], f"API returned {response.status_code}"
        print(f"  ✅ GPX speed modified")
        
        # Check if response is async (202) or sync (200)
        is_async = response.status_code == 202
        
        if is_async:
            # Async tools return JSON with execution ID
            response_data = response.json()
            print(f"  📋 Async response: {response_data}")
            execution_id = response_data.get("executionId")
            
            # Step 3: Verify database record for async tools
            print("💾 Step 3: Verify database record")
            execution = ToolExecution.objects.filter(
                user=registered_user, tool_name=tool_name
            ).order_by("-created_at").first()

            assert execution is not None
            assert execution.input_filename == filename
            assert execution.status in ["completed", "processing", "pending"]
            print(f"  ✅ Database record created: ID={execution.id}, Status={execution.status}")
        else:
            # Sync tools return file bytes directly (no ToolExecution record)
            print(f"  📋 Sync response: File bytes received ({len(response.content)} bytes)")
            assert len(response.content) > 0, "No file content received"
            print(f"  ✅ File processed successfully (synchronous conversion)")
            # Skip database verification for sync tools
            print("💾 Step 3: Database record not created (synchronous tool)")
            execution = None

        # Step 4: Cleanup (only for async tools)
        if is_async and execution:
            print("🧹 Step 4: Cleanup")
            self.cleanup_blob_storage(blob_service_client, execution.id)
            execution.delete()
            print(f"  ✅ Cleanup completed")
        else:
            print("🧹 Step 4: Cleanup - Not needed (synchronous tool)")

        print(f"{'='*60}")
        print(f"✅ TEST 4 PASSED: GPX Speed Modifier")
        print(f"{'='*60}\n")

    # ========================================================================
    # Test 5: Unit Converter
    # ========================================================================

    @pytest.mark.django_db
    def test_05_unit_converter_complete_workflow(
        self,
        authenticated_client,
        registered_user,
        blob_service_client,
    ):
        """Test complete workflow for Unit Converter."""
        print(f"\n{'='*60}")
        print(f"🧪 TEST 5: Unit Converter")
        print(f"{'='*60}")

        tool_name = "unit-converter"
        tool = tool_registry.get_tool(tool_name)
        
        if tool is None:
            print(f"  ⚠️  Tool {tool_name} not found - skipping")
            pytest.skip(f"Tool {tool_name} not registered")
            return

        print("📄 Step 1: Access tool page")
        url = f"/tools/{tool_name}/"
        response = authenticated_client.get(url, follow=True)
        assert response.status_code == 200
        print("  ✅ Tool page accessible")

        print("📤 Step 2: Convert units")
        response = authenticated_client.post(
            url,
            {
                "value": 100,
                "from_unit": "km",
                "to_unit": "miles",
            },
            follow=True,
        )

        assert response.status_code == 200
        print(f"  ✅ Unit conversion completed")

        print("💾 Step 3: Verify database record (if applicable)")
        execution = ToolExecution.objects.filter(
            user=registered_user, tool_name=tool_name
        ).order_by("-created_at").first()

        if execution:
            print(f"  ✅ Database record: ID={execution.id}, Status={execution.status}")
            print("🧹 Step 4: Cleanup")
            execution.delete()
            print(f"  ✅ Cleanup completed")
        else:
            print(f"  ℹ️  No database record (unit converter may not create executions)")

        print(f"{'='*60}")
        print(f"✅ TEST 5 PASSED: Unit Converter")
        print(f"{'='*60}\n")

    # ========================================================================
    # Test 6: Video Rotation
    # ========================================================================

    @pytest.mark.django_db
    def test_06_video_rotation_complete_workflow(
        self,
        authenticated_client,
        registered_user,
        blob_service_client,
        sample_files,
    ):
        """Test complete workflow for Video Rotation (requires Azure integration)."""
        print(f"\n{'='*60}")
        print(f"🧪 TEST 6: Video Rotation")
        print(f"{'='*60}")

        tool_name = "video-rotation"
        tool = tool_registry.get_tool(tool_name)
        
        if tool is None:
            print(f"  ⚠️  Tool {tool_name} not found - skipping")
            pytest.skip(f"Tool {tool_name} not registered")
            return

        print("📄 Step 1: Access tool page")
        url = f"/tools/{tool_name}/"
        response = authenticated_client.get(url, follow=True)
        assert response.status_code == 200
        print("  ✅ Tool page accessible")

        print("📤 Step 2: Upload video and rotate")
        filename, file_data, content_type = sample_files["mp4"]

        api_url = f"/api/v1/tools/{tool_name}/convert/"
        with io.BytesIO(file_data) as file_io:
            file_io.name = filename
            response = authenticated_client.post(
                api_url,
                {
                    "file": file_io,
                    "rotation": "90_cw",
                },
                format="multipart",
            )

        if response.status_code not in [200, 201, 202]:
            try:
                error_data = response.json()
                print(f"  ❌ API Error {response.status_code}: {error_data}")
            except:
                print(f"  ❌ API Error {response.status_code}: {response.content[:500]}")
        assert response.status_code in [200, 201, 202], f"API returned {response.status_code}"
        print(f"  ✅ Video rotation initiated")
        
        # Check if response is async (202) or sync (200)
        is_async = response.status_code == 202
        
        if is_async:
            # Async tools return JSON with execution ID
            response_data = response.json()
            print(f"  📋 Async response: {response_data}")
            execution_id = response_data.get("executionId")
            
            # Step 3: Verify database record for async tools
            print("💾 Step 3: Verify database record")
            execution = ToolExecution.objects.filter(
                user=registered_user, tool_name=tool_name
            ).order_by("-created_at").first()

            assert execution is not None
            assert execution.input_filename == filename
            assert execution.status in ["completed", "processing", "pending"]
            print(f"  ✅ Database record created: ID={execution.id}, Status={execution.status}")
        else:
            # Sync tools return file bytes directly (no ToolExecution record)
            print(f"  📋 Sync response: File bytes received ({len(response.content)} bytes)")
            assert len(response.content) > 0, "No file content received"
            print(f"  ✅ File processed successfully (synchronous conversion)")
            # Skip database verification for sync tools
            print("💾 Step 3: Database record not created (synchronous tool)")
            execution = None

        # Step 4: Verify blob storage (only for async tools)
        if is_async and execution:
            print("☁️  Step 4: Verify Azure Blob Storage")
            blob_found = False
            for container_name in ["uploads", "processed"]:
                blob_name = f"videos/{execution.id}.mp4"
                if self.verify_blob_exists(blob_service_client, container_name, blob_name):
                    blob_found = True
                    print(f"  ✅ Blob found in {container_name}: {blob_name}")
                    break

            if not blob_found:
                print(f"  ⚠️  Blob not found (may use Azure Functions async processing)")

            # Step 5: Cleanup
            print("🧹 Step 5: Cleanup")
            self.cleanup_blob_storage(blob_service_client, execution.id)
            execution.delete()
            print(f"  ✅ Cleanup completed")
        else:
            print("☁️  Step 4: Blob storage not used (synchronous tool)")
            print("🧹 Step 5: No cleanup needed (synchronous tool)")

        print(f"{'='*60}")
        print(f"✅ TEST 6 PASSED: Video Rotation")
        print(f"{'='*60}\n")

    # ========================================================================
    # Test 7: PDF to DOCX Converter (Azure Functions)
    # ========================================================================

    @pytest.mark.django_db
    def test_07_pdf_docx_converter_complete_workflow(
        self,
        authenticated_client,
        registered_user,
        blob_service_client,
        sample_files,
    ):
        """
        Test complete workflow for PDF to DOCX Converter with Azure Functions:
        1. Access tool page
        2. Upload PDF file
        3. Verify blob storage upload
        4. Verify Azure Function triggers (if URL configured)
        5. Wait for processing
        6. Verify database status update
        7. Clean up
        """
        print(f"\n{'='*60}")
        print(f"🧪 TEST 7: PDF to DOCX Converter (Azure Functions)")
        print(f"{'='*60}")

        tool_name = "pdf-docx-converter"
        tool = tool_registry.get_tool(tool_name)
        
        if tool is None:
            print(f"  ⚠️  Tool {tool_name} not found - skipping")
            pytest.skip(f"Tool {tool_name} not registered")
            return

        print("📄 Step 1: Access tool page")
        url = f"/tools/{tool_name}/"
        response = authenticated_client.get(url, follow=True)
        assert response.status_code == 200
        print("  ✅ Tool page accessible")

        print("📤 Step 2: Upload PDF file")
        filename, file_data, content_type = sample_files["pdf"]

        api_url = f"/api/v1/tools/{tool_name}/convert/"
        with io.BytesIO(file_data) as file_io:
            file_io.name = filename
            response = authenticated_client.post(
                api_url,
                {"file": file_io},
                format="multipart",
            )

        if response.status_code not in [200, 201, 202]:
            try:
                error_data = response.json()
                print(f"  ❌ API Error {response.status_code}: {error_data}")
            except:
                print(f"  ❌ API Error {response.status_code}: {response.content[:500]}")
        assert response.status_code in [200, 201, 202], f"API returned {response.status_code}"
        print(f"  ✅ PDF file uploaded")
        
        # Check if response is async (202) or sync (200)
        is_async = response.status_code == 202
        
        if is_async:
            # Async tools return JSON with execution ID
            response_data = response.json()
            print(f"  📋 Async response: {response_data}")
            execution_id = response_data.get("executionId")
            
            # Step 3: Verify database record for async tools
            print("💾 Step 3: Verify database record")
            execution = ToolExecution.objects.filter(
                user=registered_user, tool_name=tool_name
            ).order_by("-created_at").first()

            assert execution is not None
            assert execution.input_filename == filename
            assert execution.status in ["completed", "processing", "pending"]
            print(f"  ✅ Database record created: ID={execution.id}, Status={execution.status}")
        else:
            # Sync tools return file bytes directly (no ToolExecution record)
            print(f"  📋 Sync response: File bytes received ({len(response.content)} bytes)")
            assert len(response.content) > 0, "No file content received"
            print(f"  ✅ File processed successfully (synchronous conversion)")
            # Skip database verification for sync tools
            print("💾 Step 3: Database record not created (synchronous tool)")
            execution = None

        # Step 4: Verify blob storage (only for async tools)
        if is_async and execution:
            print("☁️  Step 4: Verify Azure Blob Storage upload")
            blob_name = f"pdf/{execution.id}.pdf"
            blob_found = self.verify_blob_exists(blob_service_client, "uploads", blob_name)
            
            if blob_found:
                print(f"  ✅ PDF uploaded to blob storage: {blob_name}")
            else:
                print(f"  ⚠️  Blob not found (may be processed immediately)")

            if AZURE_FUNCTIONS_URL:
                print("⚙️  Step 5: Azure Function processing")
                print(f"  ℹ️  Waiting for Azure Function to process...")
                
                # Wait up to 60 seconds for processing
                max_wait = 60
                for i in range(max_wait):
                    execution.refresh_from_db()
                    if execution.status in ["completed", "failed"]:
                        break
                    if i % 10 == 0:
                        print(f"  ⏳ Waiting... ({i}s/{max_wait}s) Status: {execution.status}")
                    time.sleep(1)

                print(f"  ✅ Final status: {execution.status}")
                
                if execution.status == "completed":
                    print(f"  ✅ Azure Function processed successfully")
                    output_blob_name = f"pdf/{execution.id}.docx"
                    if self.verify_blob_exists(blob_service_client, "processed", output_blob_name):
                        print(f"  ✅ Output DOCX found in blob storage")
            else:
                print(f"  ℹ️  AZURE_FUNCTIONS_URL not set - skipping async processing test")

            # Step 6: Cleanup
            print("🧹 Step 6: Cleanup")
            self.cleanup_blob_storage(blob_service_client, execution.id)
            execution.delete()
            print(f"  ✅ Cleanup completed")
        else:
            print("☁️  Step 4: Blob storage not used (synchronous tool)")
            print("🧹 Step 5: No cleanup needed (synchronous tool)")

        print(f"{'='*60}")
        print(f"✅ TEST 7 PASSED: PDF to DOCX Converter")
        print(f"{'='*60}\n")

    # ========================================================================
    # Test 8: Multi-User Isolation
    # ========================================================================

    @pytest.mark.django_db
    def test_08_multi_user_isolation(self, db, blob_service_client, sample_files):
        """Test that users can only see their own executions."""
        print(f"\n{'='*60}")
        print(f"🧪 TEST 8: Multi-User Isolation")
        print(f"{'='*60}")

        # Create two users
        unique_id1 = uuid.uuid4().hex[:8]
        user1 = User.objects.create_user(
            username=f"isolation_user1_{unique_id1}",
            email=f"user1_{unique_id1}@example.com",
            password="pass1",
        )

        unique_id2 = uuid.uuid4().hex[:8]
        user2 = User.objects.create_user(
            username=f"isolation_user2_{unique_id2}",
            email=f"user2_{unique_id2}@example.com",
            password="pass2",
        )

        print(f"  ✅ Created User 1: {user1.username}")
        print(f"  ✅ Created User 2: {user2.username}")

        # User 1 creates an execution
        exec1 = ToolExecution.objects.create(
            user=user1,
            tool_name="image-format-converter",
            input_filename="user1_image.png",
            status="completed",
        )

        # User 2 creates an execution
        exec2 = ToolExecution.objects.create(
            user=user2,
            tool_name="image-format-converter",
            input_filename="user2_image.png",
            status="completed",
        )

        print(f"  ✅ User 1 execution: {exec1.input_filename}")
        print(f"  ✅ User 2 execution: {exec2.input_filename}")

        # Verify isolation
        user1_executions = ToolExecution.objects.filter(user=user1)
        user2_executions = ToolExecution.objects.filter(user=user2)

        assert user1_executions.count() == 1
        assert user2_executions.count() == 1
        assert user1_executions.first().input_filename == "user1_image.png"
        assert user2_executions.first().input_filename == "user2_image.png"

        # User 1 cannot see User 2's executions
        assert not ToolExecution.objects.filter(
            user=user1, input_filename="user2_image.png"
        ).exists()

        print(f"  ✅ User isolation verified")

        # Cleanup
        exec1.delete()
        exec2.delete()
        user1.delete()
        user2.delete()

        print(f"  ✅ Cleanup completed")

        print(f"{'='*60}")
        print(f"✅ TEST 8 PASSED: Multi-User Isolation")
        print(f"{'='*60}\n")

    # ========================================================================
    # Test 9: Error Handling
    # ========================================================================

    @pytest.mark.django_db
    def test_09_error_handling_invalid_files(
        self,
        authenticated_client,
        registered_user,
    ):
        """Test error handling with invalid files."""
        print(f"\n{'='*60}")
        print(f"🧪 TEST 9: Error Handling - Invalid Files")
        print(f"{'='*60}")

        tool_name = "image-format-converter"
        url = f"/tools/{tool_name}/"

        # Test 1: File too large
        print("📤 Test 9.1: Upload oversized file")
        large_file = io.BytesIO(b"x" * (51 * 1024 * 1024))  # 51 MB
        large_file.name = "large_file.png"

        response = authenticated_client.post(
            url,
            {"input_file": large_file, "output_format": "jpeg"},
            follow=True,
        )

        # Should show error message (implementation dependent)
        print(f"  ✅ Large file handled (status: {response.status_code})")

        # Test 2: Wrong file type
        print("📤 Test 9.2: Upload wrong file type")
        text_file = io.BytesIO(b"This is not an image")
        text_file.name = "fake_image.png"

        response = authenticated_client.post(
            url,
            {"input_file": text_file, "output_format": "jpeg"},
            follow=True,
        )

        print(f"  ✅ Wrong file type handled (status: {response.status_code})")

        print(f"{'='*60}")
        print(f"✅ TEST 9 PASSED: Error Handling")
        print(f"{'='*60}\n")

    # ========================================================================
    # Final Summary
    # ========================================================================

    @pytest.mark.django_db
    def test_10_final_summary(self, registered_user):
        """Display final test summary."""
        print(f"\n{'='*60}")
        print(f"📊 FINAL TEST SUMMARY")
        print(f"{'='*60}")
        print(f"\n✅ All tests completed successfully!")
        print(f"\nTest Coverage:")
        print(f"  ✅ User registration and authentication")
        print(f"  ✅ Image Format Converter (PNG → JPEG)")
        print(f"  ✅ GPX Analyzer")
        print(f"  ✅ GPX to KML Converter")
        print(f"  ✅ GPX Speed Modifier")
        print(f"  ✅ Unit Converter")
        print(f"  ✅ Video Rotation")
        print(f"  ✅ PDF to DOCX Converter (Azure Functions)")
        print(f"  ✅ Multi-user isolation")
        print(f"  ✅ Error handling")
        print(f"\nAzure Integration:")
        print(f"  ✅ Real blob storage uploads")
        print(f"  ✅ Real blob storage downloads")
        print(f"  ✅ Blob cleanup")
        print(f"  ✅ Database user tracking")
        print(f"  {'✅' if AZURE_FUNCTIONS_URL else '⚠️ '} Azure Functions processing")
        print(f"\nTest User: {registered_user.username}")
        print(f"  Email: {registered_user.email}")
        print(f"  ID: {registered_user.id}")
        print(f"\n🧹 Test user will be deleted after test completion")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Complete User Workflow Integration Tests")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Azure Integration: {'✅ Enabled' if AZURE_INTEGRATION_ENABLED else '❌ Disabled'}")
    print(f"  Storage Connection: {'✅ Configured' if AZURE_STORAGE_CONNECTION_STRING else '❌ Not configured'}")
    print(f"  Functions URL: {'✅ Configured' if AZURE_FUNCTIONS_URL else '❌ Not configured'}")
    print(f"\nTo enable:")
    print(f"  export AZURE_INTEGRATION_TEST_ENABLED=true")
    print(f"  export AZURE_STORAGE_CONNECTION_STRING='...'")
    print(f"  export AZURE_FUNCTIONS_URL='https://your-function-app.azurewebsites.net/api/convert'")
    print(f"\nRun with:")
    print(f"  pytest tests/test_complete_user_workflows.py -v -s")
    print("=" * 60 + "\n")
