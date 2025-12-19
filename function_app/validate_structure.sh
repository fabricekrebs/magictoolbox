#!/bin/bash
# Test script to validate Azure Function App structure

echo "🔍 Validating Azure Function App structure..."
echo ""

cd "$(dirname "$0")"

# Check required files
echo "✓ Checking required files..."
required_files=("function_app.py" "host.json" "requirements.txt")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file exists"
    else
        echo "  ❌ $file missing"
        exit 1
    fi
done
echo ""

# Check host.json is valid JSON
echo "✓ Validating host.json..."
if python3 -m json.tool host.json > /dev/null 2>&1; then
    echo "  ✅ host.json is valid JSON"
else
    echo "  ❌ host.json is invalid JSON"
    exit 1
fi
echo ""

# Check Python syntax
echo "✓ Checking Python syntax..."
if python3 -m py_compile function_app.py 2>/dev/null; then
    echo "  ✅ function_app.py has valid syntax"
else
    echo "  ❌ function_app.py has syntax errors"
    exit 1
fi
echo ""

# Check for FunctionApp initialization
echo "✓ Checking FunctionApp initialization..."
if grep -q "app = func.FunctionApp()" function_app.py; then
    echo "  ✅ FunctionApp is properly initialized"
else
    echo "  ❌ FunctionApp initialization not found"
    exit 1
fi
echo ""

# Count decorated functions
echo "✓ Counting Azure Functions..."
function_count=$(grep -c "@app.route(" function_app.py || echo "0")
echo "  ✅ Found $function_count HTTP-triggered functions"
echo ""

# List all functions
echo "📋 Registered functions:"
grep "@app.route(" function_app.py | sed 's/.*route="\([^"]*\)".*/  - \1/' | sort
echo ""

echo "✅ Azure Function App structure is valid!"
echo ""
echo "📝 Summary:"
echo "  - Function App file: function_app.py"
echo "  - Total functions: $function_count"
echo "  - Host configuration: host.json"
echo "  - Dependencies: requirements.txt"
echo ""
echo "🚀 Ready for deployment!"
