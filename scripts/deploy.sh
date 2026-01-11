#!/usr/bin/env bash
# Deploy HF tools to remote server
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_CONFIG="$PROJECT_ROOT/local/deploy/config.yaml"
SSH_CONFIG="$PROJECT_ROOT/local/deploy/ssh_config"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AK6MJ HF Tools Deployment ===${NC}\n"

# Check if deployment config exists
if [ ! -f "$DEPLOY_CONFIG" ]; then
    echo -e "${RED}Error: Deployment config not found at $DEPLOY_CONFIG${NC}"
    echo ""
    echo "Create the config with:"
    echo "  mkdir -p local/deploy"
    echo "  nano local/deploy/config.yaml"
    echo ""
    echo "See docs/DEPLOYMENT.md for details."
    exit 1
fi

# Parse config (simple grep approach, could use yq for complex parsing)
REMOTE_HOST=$(grep -E '^\s*host:' "$DEPLOY_CONFIG" | awk '{print $2}' | tr -d '"' || echo "")
REMOTE_USER=$(grep -E '^\s*user:' "$DEPLOY_CONFIG" | awk '{print $2}' | tr -d '"' || echo "")
DEPLOY_PATH=$(grep -E '^\s*deploy_path:' "$DEPLOY_CONFIG" | awk '{print $2}' | tr -d '"' || echo "")

# Defaults
REMOTE_HOST=${REMOTE_HOST:-"hf-droplet"}
REMOTE_USER=${REMOTE_USER:-"$USER"}
DEPLOY_PATH=${DEPLOY_PATH:-"/var/www/ak6mj-hf"}

echo "Deployment configuration:"
echo "  Remote: $REMOTE_USER@$REMOTE_HOST"
echo "  Path: $DEPLOY_PATH"
echo ""

# Check SSH connectivity
echo -e "${YELLOW}Testing SSH connection...${NC}"
if ssh -o ConnectTimeout=5 -o BatchMode=yes "$REMOTE_USER@$REMOTE_HOST" "exit" 2>/dev/null; then
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo -e "${RED}✗ SSH connection failed${NC}"
    echo "Check SSH config at: $SSH_CONFIG"
    exit 1
fi

# Sync code
echo -e "\n${YELLOW}Syncing code to $REMOTE_HOST...${NC}"
rsync -avz --delete \
  --exclude='.git' \
  --exclude='local/' \
  --exclude='tests/' \
  --exclude='docs/' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='*.egg-info' \
  --exclude='.DS_Store' \
  "$PROJECT_ROOT/lib/" \
  "$PROJECT_ROOT/tools/" \
  "$PROJECT_ROOT/scripts/restart.sh" \
  "$REMOTE_USER@$REMOTE_HOST:$DEPLOY_PATH/"

echo -e "${GREEN}✓ Code synced${NC}"

# Copy secrets if they exist
SECRETS_FILE="$PROJECT_ROOT/local/deploy/secrets.env"
if [ -f "$SECRETS_FILE" ]; then
    echo -e "\n${YELLOW}Copying secrets...${NC}"
    scp "$SECRETS_FILE" "$REMOTE_USER@$REMOTE_HOST:$DEPLOY_PATH/.env"
    echo -e "${GREEN}✓ Secrets copied${NC}"
else
    echo -e "\n${YELLOW}Warning: No secrets file found at $SECRETS_FILE${NC}"
    echo "Skipping secrets deployment."
fi

# Restart services
echo -e "\n${YELLOW}Restarting services...${NC}"
ssh "$REMOTE_USER@$REMOTE_HOST" "cd $DEPLOY_PATH && bash scripts/restart.sh"

echo -e "\n${GREEN}=== Deployment Complete! ===${NC}"
echo ""
echo "Monitor logs:"
echo "  ssh $REMOTE_USER@$REMOTE_HOST 'sudo journalctl -u antenna-web -f'"
echo ""
echo "Check health:"
echo "  curl http://$REMOTE_HOST/health"
