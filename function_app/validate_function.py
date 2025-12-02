"""
Validation script for Azure Function without running it.
Checks syntax, imports, and logic structure.
"""
import ast
import sys
from pathlib import Path


def validate_function_code():
    """Validate the function app code structure."""
    function_file = Path(__file__).parent / "function_app.py"

    print("🔍 Validating Azure Function...")

    # Check file exists
    if not function_file.exists():
        print("❌ function_app.py not found")
        return False

    # Parse AST to check syntax
    try:
        with open(function_file) as f:
            code = f.read()
        ast.parse(code)
        print("✓ Syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False

    # Check for required functions
    required_functions = [
        "get_blob_service_client",
        "update_execution_status",
        "convert_pdf_to_docx",
        "pdf_to_docx_converter",
        "http_trigger_test",
    ]

    for func_name in required_functions:
        if f"def {func_name}" in code:
            print(f"✓ Function '{func_name}' defined")
        else:
            print(f"❌ Function '{func_name}' missing")
            return False

    # Check for required imports
    required_imports = [
        "azure.functions",
        "azure.identity",
        "azure.storage.blob",
        "pdf2docx",
        "psycopg2",
    ]

    for import_name in required_imports:
        if import_name in code:
            print(f"✓ Import '{import_name}' present")
        else:
            print(f"⚠️  Import '{import_name}' not found")

    # Check for blob trigger decorator
    if "@app.blob_trigger" in code:
        print("✓ Blob trigger decorator present")
    else:
        print("❌ Blob trigger decorator missing")
        return False

    # Check for HTTP trigger (health check)
    if "@app.route" in code or "@app.function_name" in code:
        print("✓ HTTP trigger present")
    else:
        print("⚠️  HTTP trigger not found")

    print("\n✅ Function app structure validation passed!")
    print("\nNote: Runtime testing requires:")
    print("  - Azure Functions Core Tools (func start)")
    print("  - Azure Storage emulator (Azurite)")
    print("  - PostgreSQL connection")
    print("  - Azure SDK packages installed")

    return True


if __name__ == "__main__":
    success = validate_function_code()
    sys.exit(0 if success else 1)
