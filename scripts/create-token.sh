#!/bin/bash
# Create authentication token for Engram
# Usage: ./scripts/create-token.sh email@example.com "Display Name"

set -e

USER_ID="${1:-}"
DISPLAY_NAME="${2:-}"

if [ -z "$USER_ID" ]; then
    echo "Usage: ./scripts/create-token.sh email@example.com \"Display Name\""
    exit 1
fi

if [ -z "$DISPLAY_NAME" ]; then
    DISPLAY_NAME="$USER_ID"
fi

# Generate token
TOKEN="mcp_$(openssl rand -hex 16)"

# Insert into database
docker compose exec -T postgres psql -U postgres -d postgres -c "
INSERT INTO mcp_auth_tokens (token, user_id, display_name, user_email, enabled, created_by)
VALUES ('$TOKEN', '$USER_ID', '$DISPLAY_NAME', '$USER_ID', true, 'admin')
ON CONFLICT (token) DO NOTHING;
"

echo ""
echo "============================================"
echo "  Engram Authentication Token Created"
echo "============================================"
echo ""
echo "Token:   $TOKEN"
echo "User ID: $USER_ID"
echo ""
echo "Add to Claude Code:"
echo ""
echo "  claude mcp add engram http://localhost:8080/mcp/ -t http \\"
echo "    -H \"X-MCP-Token: $TOKEN\" \\"
echo "    -H \"X-MCP-UserID: $USER_ID\""
echo ""
echo "Or add to environment:"
echo ""
echo "  export MEM0_TOKEN='$TOKEN'"
echo "  export MEM0_USER_ID='$USER_ID'"
echo ""
