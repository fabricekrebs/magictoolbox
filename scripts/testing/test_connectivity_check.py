#!/usr/bin/env python3
"""
Test script for the connectivity check HTTP function.
Tests storage and database connectivity from Function App perspective.
"""

import requests
import json
import sys
from datetime import datetime

# Function App URL
FUNCTION_APP_URL = "https://func-magictoolbox-dev-rze6cb73hmijy.azurewebsites.net"
ENDPOINT = f"{FUNCTION_APP_URL}/api/health/connectivity"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def format_operation_result(op_name: str, op_result: dict):
    """Format operation result for display."""
    if op_result["success"]:
        duration = op_result.get("duration_ms", "N/A")
        return f"  ✅ {op_name:10s}: SUCCESS ({duration}ms)"
    else:
        error = op_result.get("error", "Unknown error")
        return f"  ❌ {op_name:10s}: FAILED - {error}"


def main():
    print_section("Azure Function Connectivity Check")
    print(f"Testing endpoint: {ENDPOINT}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        print("\n🔄 Sending request...")
        response = requests.get(ENDPOINT, timeout=30)
        
        print(f"📊 HTTP Status: {response.status_code}")
        
        # Parse JSON response
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON response")
            print(f"Response text: {response.text}")
            return 1
        
        # Overall Status
        print_section("Overall Status")
        overall_status = data.get("overall_status", "unknown")
        status_icon = "✅" if overall_status == "healthy" else "⚠️" if overall_status == "degraded" else "❌"
        print(f"  {status_icon} Status: {overall_status.upper()}")
        print(f"  🕐 Timestamp: {data.get('timestamp', 'N/A')}")
        
        # Storage Results
        print_section("Storage Account Connectivity")
        storage = data.get("storage", {})
        print(f"  🔌 Accessible: {storage.get('accessible', False)}")
        if storage.get("details"):
            details = storage["details"]
            if "account_url" in details:
                print(f"  📦 Account: {details['account_url']}")
            if "test_blob" in details:
                print(f"  📄 Test Blob: {details['test_blob']}")
            if "bytes_read" in details:
                print(f"  📊 Bytes Read: {details['bytes_read']}")
        
        print("\n  Operations:")
        print(format_operation_result("WRITE", storage.get("write", {})))
        print(format_operation_result("READ", storage.get("read", {})))
        print(format_operation_result("DELETE", storage.get("delete", {})))
        
        # Database Results
        print_section("PostgreSQL Database Connectivity")
        database = data.get("database", {})
        print(f"  🔌 Accessible: {database.get('accessible', False)}")
        if database.get("details"):
            details = database["details"]
            if "host" in details:
                print(f"  🖥️  Host: {details['host']}")
            if "database" in details:
                print(f"  💾 Database: {details['database']}")
            if "user" in details:
                print(f"  👤 User: {details['user']}")
            if "row_found" in details:
                print(f"  📋 Row Found: {details['row_found']}")
            if "rows_deleted" in details:
                print(f"  🗑️  Rows Deleted: {details['rows_deleted']}")
        
        print("\n  Operations:")
        print(format_operation_result("CONNECT", database.get("connect", {})))
        print(format_operation_result("WRITE", database.get("write", {})))
        print(format_operation_result("READ", database.get("read", {})))
        print(format_operation_result("DELETE", database.get("delete", {})))
        
        # Summary
        print_section("Summary")
        storage_ok = storage.get("accessible") and all([
            storage.get("write", {}).get("success"),
            storage.get("read", {}).get("success"),
            storage.get("delete", {}).get("success")
        ])
        database_ok = database.get("accessible") and all([
            database.get("connect", {}).get("success"),
            database.get("write", {}).get("success"),
            database.get("read", {}).get("success"),
            database.get("delete", {}).get("success")
        ])
        
        print(f"  Storage:  {'✅ PASS' if storage_ok else '❌ FAIL'}")
        print(f"  Database: {'✅ PASS' if database_ok else '❌ FAIL'}")
        print(f"  Overall:  {status_icon} {overall_status.upper()}")
        
        # Save full response to file
        output_file = f"connectivity_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Full response saved to: {output_file}")
        
        print("\n" + "=" * 80)
        
        # Return exit code based on status
        return 0 if overall_status == "healthy" else 1
        
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out after 30 seconds")
        return 1
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
