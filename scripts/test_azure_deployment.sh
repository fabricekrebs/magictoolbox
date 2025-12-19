#!/bin/bash
# Test Azure deployment end-to-end
# Usage: ./scripts/test_azure_deployment.sh [environment]

set -e

ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Azure Deployment E2E Tests"
echo "Environment: $ENVIRONMENT"
echo "=========================================="
echo ""

# Load environment-specific configuration
if [ -f "$PROJECT_ROOT/.env.$ENVIRONMENT" ]; then
    echo "Loading configuration from .env.$ENVIRONMENT"
    source "$PROJECT_ROOT/.env.$ENVIRONMENT"
else
    echo "Warning: .env.$ENVIRONMENT not found"
fi

# Set Azure testing environment variables
export AZURE_TEST_ENABLED=true

# Determine base URL based on environment
case $ENVIRONMENT in
    dev|development)
        export AZURE_TEST_BASE_URL="${AZURE_TEST_BASE_URL:-https://magictoolbox-dev.azurewebsites.net}"
        ;;
    test|staging)
        export AZURE_TEST_BASE_URL="${AZURE_TEST_BASE_URL:-https://magictoolbox-test.azurewebsites.net}"
        ;;
    prod|production)
        export AZURE_TEST_BASE_URL="${AZURE_TEST_BASE_URL:-https://magictoolbox.azurewebsites.net}"
        ;;
    *)
        echo "Unknown environment: $ENVIRONMENT"
        echo "Usage: $0 [dev|test|prod]"
        exit 1
        ;;
esac

echo "Base URL: $AZURE_TEST_BASE_URL"
echo ""

# Activate virtual environment
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/.venv/bin/activate"
else
    echo "Error: Virtual environment not found at $PROJECT_ROOT/.venv"
    exit 1
fi

# Run tests
echo ""
echo "Running Azure E2E tests..."
echo "------------------------------------------"

cd "$PROJECT_ROOT"

# Run Azure-specific tests
pytest tests/test_all_tools_e2e_azure.py -v --tb=short

echo ""
echo "------------------------------------------"
echo "Azure E2E tests completed!"
echo ""

# Optional: Run smoke tests on all tools
echo "Running local tool validation tests..."
pytest tests/test_all_tools_e2e.py -v --tb=short -k "test_all_tools_have_required_metadata or test_all_tools_e2e_summary"

echo ""
echo "=========================================="
echo "All tests completed successfully!"
echo "=========================================="
