#!/bin/bash
# Stop local Azure Functions development environment

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Stopping local Azure Functions environment...${NC}"

# Stop Azurite
if pgrep -f "azurite" > /dev/null; then
    echo -e "${YELLOW}Stopping Azurite...${NC}"
    pkill -f "azurite" || true
    echo -e "${GREEN}Azurite stopped${NC}"
else
    echo -e "${YELLOW}Azurite is not running${NC}"
fi

# Stop Azure Functions
if pgrep -f "func start" > /dev/null; then
    echo -e "${YELLOW}Stopping Azure Functions...${NC}"
    pkill -f "func start" || true
    # Also kill any Python workers
    pkill -f "azure_functions_worker" || true
    echo -e "${GREEN}Azure Functions stopped${NC}"
else
    echo -e "${YELLOW}Azure Functions is not running${NC}"
fi

echo -e "${GREEN}Local environment stopped${NC}"
