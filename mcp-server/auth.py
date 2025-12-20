"""
MCP Server Authentication Module

Provides token-based authentication for MCP clients using PostgreSQL.
Validates X-MCP-Token and X-MCP-UserID headers against database.
"""

import asyncpg
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TokenAuthenticator:
    """
    Handles MCP token authentication and validation.

    Validates tokens against PostgreSQL database and ensures
    user_id matches the token owner.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize authenticator with database connection pool.

        Args:
            db_pool: asyncpg connection pool to auth database
        """
        self.db_pool = db_pool
        logger.info("TokenAuthenticator initialized")

    async def validate_token(
        self,
        token: str,
        user_id: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate token and user_id combination.

        Args:
            token: MCP token from X-MCP-Token header
            user_id: User ID from X-MCP-UserID header
            client_ip: Optional client IP address for audit
            user_agent: Optional user agent string for audit

        Returns:
            Dictionary with validation result:
            {
                "valid": bool,
                "user_id": str,  # if valid
                "permissions": list,  # if valid
                "error": str  # if invalid
            }
        """
        async with self.db_pool.acquire() as conn:
            try:
                # Query token from database
                row = await conn.fetchrow("""
                    SELECT
                        token,
                        user_id,
                        enabled,
                        expires_at,
                        permissions,
                        display_name
                    FROM mcp_auth_tokens
                    WHERE token = $1
                """, token)

                # Token doesn't exist
                if not row:
                    await self._log_auth_attempt(
                        conn, token, user_id, "denied",
                        "Invalid token",  False, client_ip, user_agent
                    )
                    return {
                        "valid": False,
                        "error": "Invalid authentication token. Please check your MEM0_TOKEN environment variable."
                    }

                # Token exists but is disabled
                if not row['enabled']:
                    await self._log_auth_attempt(
                        conn, token, user_id, "denied",
                        "Token disabled", False, client_ip, user_agent
                    )
                    return {
                        "valid": False,
                        "error": "This token has been disabled. Contact your administrator."
                    }

                # Token is expired
                if row['expires_at'] and datetime.utcnow() > row['expires_at']:
                    await self._log_auth_attempt(
                        conn, token, user_id, "expired",
                        f"Token expired on {row['expires_at']}",
                        False, client_ip, user_agent
                    )
                    expiry_date = row['expires_at'].strftime('%Y-%m-%d')
                    return {
                        "valid": False,
                        "error": f"Token expired on {expiry_date}. Please request a new token from your administrator."
                    }

                # User ID mismatch
                if row['user_id'] != user_id:
                    await self._log_auth_attempt(
                        conn, token, user_id, "denied",
                        f"User ID mismatch. Expected: {row['user_id']}, Got: {user_id}",
                        False, client_ip, user_agent
                    )
                    return {
                        "valid": False,
                        "error": f"User ID mismatch. This token belongs to '{row['user_id']}', but you provided '{user_id}'. Please check your MEM0_USER_ID environment variable."
                    }

                # SUCCESS - Update last_used_at timestamp
                await conn.execute("""
                    UPDATE mcp_auth_tokens
                    SET last_used_at = NOW()
                    WHERE token = $1
                """, token)

                # Log successful authentication
                await self._log_auth_attempt(
                    conn, token, user_id, "login",
                    "Authentication successful", True, client_ip, user_agent
                )

                logger.info(f"✅ Authenticated user: {user_id} ({row.get('display_name', 'N/A')})")

                return {
                    "valid": True,
                    "user_id": row['user_id'],
                    "permissions": row['permissions'],
                    "display_name": row.get('display_name')
                }

            except Exception as e:
                logger.exception(f"Error validating token: {e}")
                await self._log_auth_attempt(
                    conn, token, user_id, "error",
                    f"System error: {str(e)}", False, client_ip, user_agent
                )
                return {
                    "valid": False,
                    "error": "Authentication system error. Please try again or contact support."
                }

    async def _log_auth_attempt(
        self,
        conn: asyncpg.Connection,
        token: str,
        user_id: str,
        action: str,
        message: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log authentication attempt to audit table.

        Args:
            conn: Database connection
            token: MCP token
            user_id: User ID attempting authentication
            action: Action type (login, denied, expired, error)
            message: Descriptive message
            success: Whether authentication succeeded
            ip_address: Optional client IP
            user_agent: Optional user agent string
        """
        try:
            await conn.execute("""
                INSERT INTO mcp_auth_audit_log
                    (token, user_id, action, success, error_message, ip_address, user_agent)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, token, user_id, action, success, message, ip_address, user_agent)
        except Exception as e:
            # Don't fail auth if audit logging fails, but log the error
            logger.error(f"Failed to write audit log: {e}")

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics for a user's tokens.

        Args:
            user_id: User ID to get stats for

        Returns:
            Dictionary with user statistics
        """
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_tokens,
                    SUM(CASE WHEN enabled THEN 1 ELSE 0 END) as active_tokens,
                    MAX(last_used_at) as last_activity
                FROM mcp_auth_tokens
                WHERE user_id = $1
            """, user_id)

            recent_logins = await conn.fetch("""
                SELECT COUNT(*) as login_count
                FROM mcp_auth_audit_log
                WHERE user_id = $1
                    AND action = 'login'
                    AND timestamp > NOW() - INTERVAL '30 days'
            """, user_id)

            return {
                "user_id": user_id,
                "total_tokens": stats['total_tokens'],
                "active_tokens": stats['active_tokens'],
                "last_activity": stats['last_activity'],
                "logins_30d": recent_logins[0]['login_count'] if recent_logins else 0
            }
