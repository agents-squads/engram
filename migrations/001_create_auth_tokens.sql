-- Migration: 001_create_auth_tokens
-- Description: Create authentication tables for MCP token-based auth
-- Created: 2025-01-09

-- =============================================================================
-- Main Auth Tokens Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS mcp_auth_tokens (
    -- Primary token identifier
    token VARCHAR(64) PRIMARY KEY,

    -- User identification
    user_id VARCHAR(255) NOT NULL,
    user_email VARCHAR(255),
    display_name VARCHAR(255),

    -- Token status
    enabled BOOLEAN DEFAULT true NOT NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,

    -- Audit trail
    created_by VARCHAR(255),

    -- Client information (JSON)
    client_info JSONB DEFAULT '{}'::jsonb,

    -- Permissions (JSON array)
    permissions JSONB DEFAULT '["read", "write"]'::jsonb
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_tokens_user_id
    ON mcp_auth_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_tokens_enabled
    ON mcp_auth_tokens(enabled);

CREATE INDEX IF NOT EXISTS idx_tokens_expires_at
    ON mcp_auth_tokens(expires_at)
    WHERE expires_at IS NOT NULL;

-- =============================================================================
-- Audit Log Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS mcp_auth_audit_log (
    id SERIAL PRIMARY KEY,

    -- References
    token VARCHAR(64),
    user_id VARCHAR(255) NOT NULL,

    -- Event details
    action VARCHAR(50) NOT NULL,  -- 'login', 'denied', 'expired', 'revoked'
    success BOOLEAN DEFAULT true NOT NULL,
    error_message TEXT,

    -- Request metadata
    ip_address INET,
    user_agent TEXT,

    -- Timestamp
    timestamp TIMESTAMP DEFAULT NOW() NOT NULL
);

-- =============================================================================
-- Audit Log Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_audit_timestamp
    ON mcp_auth_audit_log(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_user_id
    ON mcp_auth_audit_log(user_id);

CREATE INDEX IF NOT EXISTS idx_audit_token
    ON mcp_auth_audit_log(token);

-- =============================================================================
-- Example Data (Optional - for development/testing)
-- =============================================================================

-- Uncomment to insert sample token for testing
-- INSERT INTO mcp_auth_tokens
--     (token, user_id, user_email, display_name, created_by, client_info)
-- VALUES (
--     'mcp_dev_test_token_12345678901234567890',
--     'dev@localhost',
--     'dev@localhost',
--     'Development User',
--     'system',
--     '{"os": "development", "hostname": "localhost", "client": "test"}'::jsonb
-- ) ON CONFLICT (token) DO NOTHING;

-- =============================================================================
-- Comments for Documentation
-- =============================================================================

COMMENT ON TABLE mcp_auth_tokens IS 'Stores authentication tokens for MCP client access';
COMMENT ON COLUMN mcp_auth_tokens.token IS 'Unique token identifier (format: mcp_<random>)';
COMMENT ON COLUMN mcp_auth_tokens.user_id IS 'User identifier - must match X-MCP-UserID header';
COMMENT ON COLUMN mcp_auth_tokens.enabled IS 'Flag to disable token without deletion';
COMMENT ON COLUMN mcp_auth_tokens.expires_at IS 'Token expiration timestamp (NULL = never expires)';
COMMENT ON COLUMN mcp_auth_tokens.permissions IS 'JSON array of permissions (e.g., ["read", "write", "admin"])';

COMMENT ON TABLE mcp_auth_audit_log IS 'Audit log for all authentication attempts';
COMMENT ON COLUMN mcp_auth_audit_log.action IS 'Authentication action type';
COMMENT ON COLUMN mcp_auth_audit_log.success IS 'Whether the authentication attempt succeeded';

-- =============================================================================
-- Migration Complete
-- =============================================================================

-- Verify tables were created
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 001_create_auth_tokens completed successfully';
    RAISE NOTICE 'Tables created: mcp_auth_tokens, mcp_auth_audit_log';
END $$;
