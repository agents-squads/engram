# Security Guide

Comprehensive security features and best practices for the Mem0 MCP Server.

## Overview

The Mem0 MCP Server implements multiple layers of security:

1. **Token-Based Authentication** - MCP-level authentication with PostgreSQL storage
2. **Memory Ownership Validation** - User-scoped access control for all memory operations
3. **Project Isolation** - Automatic memory segregation by project/user
4. **Audit Logging** - Complete authentication and access tracking

---

## Memory Ownership & Access Control

### How It Works

Every memory operation validates ownership to ensure users can only access their own data:

```
User Request → Token Auth → User ID Validation → Ownership Check → Action
```

### Protected Operations

All memory operations require ownership validation:

| Operation | Endpoint | Protection |
|-----------|----------|------------|
| **Read Memory** | `GET /memories/{id}` | ✅ User ID required |
| **Update Memory** | `PUT /memories/{id}` | ✅ User ID required |
| **Delete Memory** | `DELETE /memories/{id}` | ✅ User ID required |
| **View History** | `GET /memories/{id}/history` | ✅ User ID required |
| **Search** | `POST /search` | ✅ User ID scoped |
| **Get All** | `GET /memories` | ✅ User ID scoped |

### Example: Ownership Validation

```bash
# User A creates a memory
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Secret data"}],"user_id":"user_a"}'

# Returns: {"results":[{"id":"abc123",...}]}

# User B tries to read User A's memory
curl http://localhost:8000/memories/abc123?user_id=user_b

# Returns: 403 Forbidden
# {"detail":"Access denied: Memory abc123 does not belong to user user_b"}
```

### MCP Tools Protection

All MCP tools automatically validate ownership:

```python
# delete_memory tool
@mcp.tool()
async def delete_memory(memory_id: str) -> str:
    # Authentication validated from headers
    auth_result = await validate_auth()

    # Ownership validated via user_id parameter
    uid = config.CURRENT_PROJECT_ID
    response = await http_client.delete(
        f"/memories/{memory_id}",
        params={"user_id": uid}  # ← Ownership check
    )
```

---

## Authentication Security

### Token Management

**Token Format:**
- Prefix: `mcp_`
- Length: 43 characters (256-bit security)
- Generation: `secrets.token_urlsafe(32)`

**Token Lifecycle:**
```
Create → Active → [Optional: Revoke] → [Optional: Re-enable] → Delete
```

**Security Features:**
- ✅ Cryptographically secure random generation
- ✅ Expiration dates (default: 365 days)
- ✅ Revocation support
- ✅ Last-used tracking
- ✅ Audit logging

### Best Practices

#### 1. Token Storage

**❌ Never:**
```bash
# Don't commit tokens to git
git add .env  # BAD!

# Don't hardcode in code
TOKEN = "mcp_abc123..."  # BAD!
```

**✅ Always:**
```bash
# Use environment variables
export MEM0_TOKEN='mcp_...'

# Add to .gitignore
echo ".env" >> .gitignore

# Use password manager for backup
1password add "Mem0 Token" --vault=Work
```

#### 2. Token Rotation

Rotate tokens regularly:

```bash
# Create new token
NEW_TOKEN=$(python3 scripts/mcp-token.py create \
  --user-id your.email@company.com \
  --name "Your Name" \
  --email your.email@company.com | grep "Token:" | cut -d' ' -f2)

# Update environment
export MEM0_TOKEN="$NEW_TOKEN"

# Update Claude Code
claude mcp remove mem0
claude mcp add mem0 http://localhost:8080/mcp/ -t http \
  -H "X-MCP-Token: ${MEM0_TOKEN}" \
  -H "X-MCP-UserID: ${MEM0_USER_ID}"

# Verify working
claude mcp list

# Revoke old token
python3 scripts/mcp-token.py revoke $OLD_TOKEN
```

#### 3. Multi-User Setup

Each team member should have their own token:

```bash
# Team Lead creates tokens
for user in alice@company.com bob@company.com charlie@company.com; do
  python3 scripts/mcp-token.py create \
    --user-id "$user" \
    --name "$(echo $user | cut -d'@' -f1)" \
    --email "$user"
done

# Each user configures their environment
# Alice's ~/.zshrc
export MEM0_TOKEN='mcp_alice_...'
export MEM0_USER_ID='alice@company.com'

# Bob's ~/.zshrc
export MEM0_TOKEN='mcp_bob_...'
export MEM0_USER_ID='bob@company.com'
```

---

## Project Isolation

### Isolation Modes

**1. Auto Mode (Recommended for Multi-Project)**

```bash
PROJECT_ID_MODE=auto
```

Each directory gets unique project ID:
- `/projects/app1` → `project_app1_abc123`
- `/projects/app2` → `project_app2_def456`

Memories are isolated per project + user.

**2. Manual Mode (Recommended for Single Project)**

```bash
PROJECT_ID_MODE=manual
DEFAULT_USER_ID=my_project_name
```

Explicit project ID for all memories.

**3. Global Mode (Shared Memories)**

```bash
PROJECT_ID_MODE=global
DEFAULT_USER_ID=shared_knowledge_base
```

All users share the same memory pool.

### Security Implications

| Mode | Isolation | Use Case |
|------|-----------|----------|
| **auto** | High - Per project+user | Multiple projects, multiple users |
| **manual** | Medium - Per user | Single project, multiple users |
| **global** | Low - Shared | Team knowledge base |

---

## Audit Logging

### What's Logged

Every authentication attempt is logged:

```sql
SELECT * FROM mcp_auth_audit_log ORDER BY timestamp DESC LIMIT 5;
```

**Logged Information:**
- Timestamp
- User ID
- Event type (success/auth_failed)
- Token used
- Error message (if failed)
- IP address (from request)

### Monitoring

**View recent activity:**
```bash
python3 scripts/mcp-token.py audit --days 7
```

**Check user statistics:**
```bash
python3 scripts/mcp-token.py stats john.doe@company.com
```

**Alert on suspicious activity:**
```bash
# Check for failed attempts
docker compose exec postgres psql -U postgres -d postgres -c \
  "SELECT user_id, COUNT(*) as failed_attempts
   FROM mcp_auth_audit_log
   WHERE event_type='auth_failed'
     AND timestamp > NOW() - INTERVAL '1 hour'
   GROUP BY user_id
   HAVING COUNT(*) > 5;"
```

---

## Production Deployment

### 1. Network Security

**Docker Compose Configuration:**

```yaml
services:
  mcp:
    ports:
      - "127.0.0.1:8080:8080"  # Only localhost

  mem0:
    ports:
      - "127.0.0.1:8000:8000"  # Only localhost

  postgres:
    # No external ports
    networks:
      - mem0_network
```

**Reverse Proxy (nginx):**

```nginx
server {
    listen 443 ssl http2;
    server_name mem0.company.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    location /mcp/ {
        proxy_pass http://127.0.0.1:8080/mcp/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Rate limiting
        limit_req zone=mcp_limit burst=10 nodelay;
    }
}
```

### 2. Database Security

**Strong Passwords:**

```bash
# Generate secure password
POSTGRES_PASSWORD=$(openssl rand -base64 32)
```

**Restrict Access:**

```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    networks:
      - mem0_network  # Internal only
```

**Regular Backups:**

```bash
# Backup script
#!/bin/bash
docker compose exec postgres pg_dump -U postgres postgres | \
  gzip > "backup-$(date +%Y%m%d).sql.gz"
```

### 3. Token Security

**Expiration Policy:**

```bash
# Short-lived tokens for sensitive environments
python3 scripts/mcp-token.py create \
  --user-id user@company.com \
  --expires-days 30  # 30 days instead of 365
```

**Automated Rotation:**

```bash
#!/bin/bash
# Monthly token rotation
0 0 1 * * /usr/local/bin/rotate-tokens.sh
```

### 4. Monitoring & Alerts

**Health Checks:**

```bash
# Add to monitoring (Prometheus/Grafana)
curl -f http://localhost:8080/ || alert "MCP server down"
curl -f http://localhost:8000/health || alert "Mem0 server down"
```

**Failed Auth Alerts:**

```bash
# Alert on 10+ failed attempts in 1 hour
*/15 * * * * /usr/local/bin/check-failed-auth.sh
```

---

## Security Testing

### Run Security Tests

```bash
# Ownership validation
./tests/test_ownership_simple.sh

# Authentication
./tests/test_auth.sh

# Full test suite
./scripts/test.sh
```

### Manual Security Audit

**1. Test Ownership Isolation:**

```bash
# Create memory as User A
MEMORY_ID=$(curl -s -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Secret"}],"user_id":"user_a"}' | \
  jq -r '.results[0].id')

# Try to access as User B (should fail)
curl -s "http://localhost:8000/memories/$MEMORY_ID?user_id=user_b" | \
  jq '.detail'

# Expected: "Access denied: Memory {id} does not belong to user user_b"
```

**2. Test Authentication:**

```bash
# Invalid token (should fail)
curl -s http://localhost:8080/mcp \
  -H "X-MCP-Token: invalid" \
  -H "X-MCP-UserID: test" | \
  jq '.error'

# No token (should fail)
curl -s http://localhost:8080/mcp | jq '.error'
```

**3. Test Token Revocation:**

```bash
# Create and revoke token
TOKEN=$(python3 scripts/mcp-token.py create --user-id test@test.com --name Test --email test@test.com | grep Token | cut -d' ' -f2)
python3 scripts/mcp-token.py revoke $TOKEN

# Try to use revoked token (should fail)
curl -s http://localhost:8080/mcp \
  -H "X-MCP-Token: $TOKEN" \
  -H "X-MCP-UserID: test@test.com" | \
  jq '.error'
```

---

## Incident Response

### Suspected Compromise

**1. Immediate Actions:**

```bash
# Revoke all tokens
python3 scripts/mcp-token.py list | grep "mcp_" | \
  while read token rest; do
    python3 scripts/mcp-token.py revoke "$token"
  done

# Check audit log
python3 scripts/mcp-token.py audit --days 30 > security-audit.log

# Review suspicious activity
grep "auth_failed" security-audit.log
```

**2. Investigation:**

```bash
# Check database for unauthorized access
docker compose exec postgres psql -U postgres -d postgres <<EOF
SELECT user_id, COUNT(*)
FROM mcp_auth_audit_log
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY user_id;
EOF

# Review memory access patterns
docker compose logs mcp --since 24h | grep "Access denied"
```

**3. Recovery:**

```bash
# Create new tokens for legitimate users
for user in $(cat authorized_users.txt); do
  python3 scripts/mcp-token.py create --user-id "$user" --name "$user"
done

# Notify users to update tokens
./scripts/notify-users.sh "Please update your MEM0_TOKEN"
```

---

## Compliance

### Data Residency

All data stays local:
- ✅ Vector embeddings: PostgreSQL (local)
- ✅ Authentication tokens: PostgreSQL (local)
- ✅ LLM inference: Ollama (local) or Cloud (configurable)

### GDPR Compliance

**Right to be Forgotten:**

```bash
# Delete all user data
python3 scripts/delete-user-data.py --user-id user@example.com
```

**Data Export:**

```bash
# Export user's memories
curl "http://localhost:8000/memories?user_id=user@example.com" > user_data.json
```

**Audit Trail:**

```bash
# Export audit log for user
python3 scripts/mcp-token.py audit --user-id user@example.com > audit.log
```

---

## Security Checklist

### Initial Setup
- [ ] Change default PostgreSQL password
- [ ] Enable token authentication
- [ ] Create individual tokens for each user
- [ ] Configure firewall rules
- [ ] Enable HTTPS (production)

### Ongoing Maintenance
- [ ] Rotate tokens every 90 days
- [ ] Review audit logs weekly
- [ ] Update dependencies monthly
- [ ] Test backups quarterly
- [ ] Security audit annually

### Before Production
- [ ] Run security tests
- [ ] Configure rate limiting
- [ ] Setup monitoring/alerts
- [ ] Document incident response plan
- [ ] Train team on security practices

---

## Additional Resources

- [AUTHENTICATION.md](AUTHENTICATION.md) - Detailed authentication guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Security-related troubleshooting
- [CLAUDE.md](../CLAUDE.md) - Development security notes
- [MCP Specification](https://modelcontextprotocol.io) - MCP security standards

---

## Report Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email: security@your-company.com (or create private security advisory)
3. Include: Description, impact, reproduction steps
4. We'll respond within 48 hours

---

**Last Updated:** 2025-10-10
**Version:** 1.1.0
