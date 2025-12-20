# Authentication Guide

The Mem0 MCP server uses token-based authentication with PostgreSQL storage for secure multi-user access.

## Overview

Authentication requires two headers for each MCP request:
- `X-MCP-Token`: Authentication token (from `MEM0_TOKEN` env var)
- `X-MCP-UserID`: User identifier (from `MEM0_USER_ID` env var)

The system validates that:
1. The token exists in the database
2. The token is enabled (not revoked)
3. The token has not expired
4. The token belongs to the specified user

## Quick Setup

### 1. Run Database Migrations

First, set up the authentication tables:

```bash
./scripts/migrate-auth.sh
```

This creates:
- `mcp_auth_tokens` table - Stores tokens with user mappings
- `mcp_auth_audit_log` table - Audit trail of authentication attempts

### 2. Create Your Token

```bash
python3 scripts/mcp-token.py create \
  --user-id john.doe@company.com \
  --name "John Doe" \
  --email john.doe@company.com
```

Output:
```
✅ Token created successfully!

Token: mcp_abc123def456...
User ID: john.doe@company.com

Add these to your shell profile (~/.zshrc or ~/.bashrc):

export MEM0_TOKEN='mcp_abc123def456...'
export MEM0_USER_ID='john.doe@company.com'
```

### 3. Configure Environment

Add to `~/.zshrc` or `~/.bashrc`:

```bash
export MEM0_TOKEN='mcp_abc123def456...'
export MEM0_USER_ID='john.doe@company.com'
```

Reload:
```bash
source ~/.zshrc  # or ~/.bashrc
```

### 4. Configure Claude Code

**Using Claude CLI (Recommended):**

```bash
# HTTP Stream transport (modern, recommended)
claude mcp add mem0 http://localhost:8080/mcp/ -t http \
  -H "X-MCP-Token: ${MEM0_TOKEN}" \
  -H "X-MCP-UserID: ${MEM0_USER_ID}"

# Verify
claude mcp list
```

**Manual Configuration:**

Edit `~/.config/claude-code/config.json`:

```json
{
  "mcpServers": {
    "mem0": {
      "url": "http://localhost:8080/mcp/",
      "transport": "http",
      "headers": {
        "X-MCP-Token": "your-token-here",
        "X-MCP-UserID": "your.email@company.com"
      }
    }
  }
}
```

## Token Management

### List Tokens

```bash
# All tokens
python3 scripts/mcp-token.py list

# Tokens for specific user
python3 scripts/mcp-token.py list --user-id john.doe@company.com
```

Output:
```
Token: mcp_abc123... | User: john.doe@company.com | Status: enabled | Expires: 2026-01-10
```

### Create Token

```bash
python3 scripts/mcp-token.py create \
  --user-id john.doe@company.com \
  --name "John Doe" \
  --email john.doe@company.com \
  --expires-days 365  # Optional, defaults to 365
```

### Revoke Token

Disable a token without deleting it:

```bash
python3 scripts/mcp-token.py revoke mcp_abc123def456
```

### Re-enable Token

Re-activate a revoked token:

```bash
python3 scripts/mcp-token.py enable mcp_abc123def456
```

### Delete Token

Permanently delete a token:

```bash
python3 scripts/mcp-token.py delete mcp_abc123def456
```

**Warning:** This is permanent and cannot be undone.

### View Audit Log

```bash
# Last 30 days
python3 scripts/mcp-token.py audit --days 30

# Last 7 days
python3 scripts/mcp-token.py audit --days 7
```

Output shows:
- Timestamp
- User ID
- Event type (success/failure)
- Token used
- Error message (if failed)

### User Statistics

```bash
python3 scripts/mcp-token.py stats john.doe@company.com
```

Shows:
- Total tokens for user
- Active tokens
- Last authentication
- Authentication counts (success/failure)

## Database Schema

### mcp_auth_tokens

| Column | Type | Description |
|--------|------|-------------|
| token | VARCHAR(255) | Primary key, token string |
| user_id | VARCHAR(255) | User identifier |
| name | VARCHAR(255) | User's full name |
| email | VARCHAR(255) | User's email |
| created_at | TIMESTAMP | Creation time |
| expires_at | TIMESTAMP | Expiration time |
| is_enabled | BOOLEAN | Active status |
| last_used_at | TIMESTAMP | Last successful auth |
| permissions | TEXT | JSON permissions (future use) |

### mcp_auth_audit_log

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| timestamp | TIMESTAMP | Event time |
| user_id | VARCHAR(255) | User identifier |
| event_type | VARCHAR(50) | success/auth_failed |
| token_used | VARCHAR(255) | Token string |
| error_message | TEXT | Error details |

## Security Best Practices

### Token Storage

1. **Never commit tokens to git**
   - Add to `.gitignore`: `.env`, `*.token`
   - Use environment variables

2. **Use strong tokens**
   - Tokens are generated with `secrets.token_urlsafe(32)` (256 bits)
   - Format: `mcp_` prefix + 43 random characters

3. **Rotate tokens regularly**
   - Create new token
   - Update environment variables
   - Revoke old token
   - Verify new token works
   - Delete old token

### Access Control

1. **One token per user**
   - Each team member should have their own token
   - Enables individual audit trails
   - Allows selective revocation

2. **Set expiration dates**
   - Default: 365 days
   - Use shorter periods for sensitive environments
   - Set up reminders to rotate before expiration

3. **Monitor audit logs**
   - Review failed authentication attempts
   - Identify unusual access patterns
   - Investigate unauthorized access attempts

### Production Deployment

1. **Use HTTPS**
   - Add TLS termination via reverse proxy
   - Prevents token interception

2. **Restrict network access**
   - Don't expose MCP server publicly
   - Use VPN or SSH tunnels
   - Whitelist IP addresses if needed

3. **Secure database**
   - Change default PostgreSQL password
   - Restrict database network access
   - Enable PostgreSQL audit logging

4. **Backup tokens**
   - Export token list regularly
   - Store securely (password manager, vault)
   - Document token ownership

## Testing Authentication

Run the test suite:

```bash
./tests/test_auth.sh
```

Tests include:
- ✅ Missing authentication headers
- ✅ Invalid token
- ✅ User ID mismatch
- ✅ Valid authentication
- ✅ Token revocation
- ✅ Token re-enabling
- ✅ Expired tokens

## Troubleshooting

### "Missing authentication headers"

**Cause:** Headers not sent with request

**Solutions:**
1. Verify environment variables:
   ```bash
   echo $MEM0_TOKEN
   echo $MEM0_USER_ID
   ```

2. Check Claude Code configuration:
   ```bash
   claude mcp list
   # Should show headers configured
   ```

3. Restart shell and Claude Code

### "Invalid authentication token"

**Cause:** Token doesn't exist, is disabled, or expired

**Solutions:**
1. List all tokens:
   ```bash
   python3 scripts/mcp-token.py list
   ```

2. Check token status (enabled/disabled/expired)

3. Create new token if needed:
   ```bash
   python3 scripts/mcp-token.py create --user-id your.email@company.com --name "Your Name" --email your.email@company.com
   ```

### "User ID mismatch"

**Cause:** Token belongs to different user

**Solutions:**
1. Check which user owns the token:
   ```bash
   python3 scripts/mcp-token.py list
   ```

2. Either:
   - Update `MEM0_USER_ID` to match token's user
   - Create new token for your user ID

### "Token has been disabled"

**Cause:** Token was revoked

**Solutions:**
1. Re-enable token:
   ```bash
   python3 scripts/mcp-token.py enable mcp_abc123
   ```

2. Or create new token:
   ```bash
   python3 scripts/mcp-token.py create --user-id your.email@company.com --name "Your Name" --email your.email@company.com
   ```

### Server not showing in `claude mcp list`

**Cause:** Incorrect URL or configuration

**Solutions:**
1. Ensure URL has trailing slash:
   - ✅ `http://localhost:8080/mcp/`
   - ❌ `http://localhost:8080/mcp`

2. Remove and re-add:
   ```bash
   claude mcp remove mem0
   claude mcp add mem0 http://localhost:8080/mcp/ -t http \
     -H "X-MCP-Token: ${MEM0_TOKEN}" \
     -H "X-MCP-UserID: ${MEM0_USER_ID}"
   ```

3. Check server is running:
   ```bash
   docker compose ps
   curl http://localhost:8080/
   ```

## Multi-User Setup

### Team Environment

1. **Create tokens for each team member:**

```bash
# User 1
python3 scripts/mcp-token.py create \
  --user-id alice@company.com \
  --name "Alice Smith" \
  --email alice@company.com

# User 2
python3 scripts/mcp-token.py create \
  --user-id bob@company.com \
  --name "Bob Jones" \
  --email bob@company.com
```

2. **Each user configures their environment:**

```bash
# Alice's ~/.zshrc
export MEM0_TOKEN='mcp_alice_token_here'
export MEM0_USER_ID='alice@company.com'

# Bob's ~/.zshrc
export MEM0_TOKEN='mcp_bob_token_here'
export MEM0_USER_ID='bob@company.com'
```

3. **Project isolation:**

With `PROJECT_ID_MODE=auto`, each user's memories are isolated per project directory. Users can collaborate in shared projects while maintaining separate memories.

### Shared vs. Individual Memories

**Individual memories (default):**
- `PROJECT_ID_MODE=auto`
- Each user has separate memories per project
- Best for personal development

**Shared memories:**
- `PROJECT_ID_MODE=global`
- All users share same memory pool
- Best for team knowledge bases
- Still requires individual authentication

## API Reference

### Authentication Flow

```python
# 1. Client sends headers with MCP request
headers = {
    "X-MCP-Token": "mcp_abc123...",
    "X-MCP-UserID": "john.doe@company.com"
}

# 2. MCP server validates
def validate_auth(token: str, user_id: str) -> bool:
    # Check token exists
    # Check token enabled
    # Check token not expired
    # Check token belongs to user_id
    # Log authentication attempt
    return True/False

# 3. If valid, proceed with MCP tool call
# 4. If invalid, return error message
```

### Direct Database Access

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d postgres

# Query tokens
SELECT token, user_id, name, email, created_at, expires_at, is_enabled, last_used_at
FROM mcp_auth_tokens
WHERE user_id = 'john.doe@company.com';

# Query audit log
SELECT timestamp, user_id, event_type, error_message
FROM mcp_auth_audit_log
WHERE user_id = 'john.doe@company.com'
ORDER BY timestamp DESC
LIMIT 10;
```

## Migration from Unauthenticated Setup

If upgrading from previous version without authentication:

1. **Backup existing data:**
   ```bash
   docker compose exec postgres pg_dump -U postgres postgres > backup.sql
   ```

2. **Run authentication migration:**
   ```bash
   ./scripts/migrate-auth.sh
   ```

3. **Create tokens for existing users:**
   ```bash
   python3 scripts/mcp-token.py create \
     --user-id your.email@company.com \
     --name "Your Name" \
     --email your.email@company.com
   ```

4. **Update Claude Code configuration** with headers

5. **Existing memories remain accessible** after authentication is configured

## Additional Resources

- [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
- [MCP_TOOLS.md](MCP_TOOLS.md) - MCP tools documentation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting
- [GitHub: Model Context Protocol](https://github.com/modelcontextprotocol) - MCP specification
