#!/bin/bash
# Start local Azure Functions development environment
# This script starts Azurite and Azure Functions Core Tools as background services

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting local Azure Functions environment...${NC}"

# Set up environment variables
export AZURITE_ACCOUNTS="devstorageaccount1:Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
export AZURE_STORAGE_CONNECTION_STRING='DefaultEndpointsProtocol=http;AccountName=devstorageaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstorageaccount1;'

# Check if Azurite is already running
if pgrep -f "azurite" > /dev/null; then
    echo -e "${YELLOW}Azurite is already running${NC}"
else
    echo -e "${GREEN}Starting Azurite...${NC}"
    mkdir -p /tmp/azurite
    nohup azurite --silent --location /tmp/azurite --blobPort 10000 --queuePort 10001 --tablePort 10002 > /tmp/azurite.log 2>&1 &
    AZURITE_PID=$!
    echo -e "${GREEN}Azurite started (PID: $AZURITE_PID)${NC}"
    
    # Wait for Azurite to be ready
    echo -e "${YELLOW}Waiting for Azurite to start...${NC}"
    sleep 2
    
    # Create containers if they don't exist
    echo -e "${GREEN}Creating storage containers...${NC}"
    az storage container create --name uploads 2>/dev/null || echo "uploads container already exists"
    az storage container create --name processed 2>/dev/null || echo "processed container already exists"
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Azure Functions is already running
if pgrep -f "func start" > /dev/null; then
    echo -e "${YELLOW}Azure Functions is already running${NC}"
else
    echo -e "${GREEN}Starting Azure Functions...${NC}"
    cd "$SCRIPT_DIR"
    
    # Activate virtual environment and start function
    source .venv/bin/activate
    nohup func start --python > /tmp/azure-functions.log 2>&1 &
    FUNC_PID=$!
    echo -e "${GREEN}Azure Functions started (PID: $FUNC_PID)${NC}"
    
    # Wait for function to initialize
    echo -e "${YELLOW}Waiting for Azure Functions to initialize...${NC}"
    sleep 5
fi

echo ""
echo -e "${GREEN}=== Local Environment Started ===${NC}"
echo -e "Azurite Blob Storage: ${YELLOW}http://127.0.0.1:10000${NC}"
echo -e "Azurite Queue Storage: ${YELLOW}http://127.0.0.1:10001${NC}"
echo -e "Azure Functions: ${YELLOW}http://localhost:7071${NC}"
echo ""
echo -e "Logs:"
echo -e "  Azurite: ${YELLOW}tail -f /tmp/azurite.log${NC}"
echo -e "  Azure Functions: ${YELLOW}tail -f /tmp/azure-functions.log${NC}"
echo ""
echo -e "To stop services:"
echo -e "  ${YELLOW}./stop_local_env.sh${NC}"
