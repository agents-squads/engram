#!/usr/bin/env python3
"""
MCP Token Management CLI

Manage authentication tokens for MCP clients.
"""
import asyncio
import secrets
import sys
from datetime import datetime, timedelta

import asyncpg
import click
from tabulate import tabulate


# Database connection parameters
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "database": "postgres"
}


async def get_db_connection():
    """Get database connection."""
    try:
        return await asyncpg.connect(**DB_CONFIG)
    except Exception as e:
        click.echo(f"❌ Failed to connect to database: {e}", err=True)
        click.echo("Ensure the mem0-mcp stack is running: ./scripts/start.sh", err=True)
        sys.exit(1)


def generate_token():
    """Generate a secure random token."""
    return f"mcp_{secrets.token_urlsafe(32)}"


@click.group()
def cli():
    """MCP Token Management - Manage authentication tokens for MCP clients."""
    pass


@cli.command()
@click.option('--user-id', required=True, help='User ID (email recommended, e.g., john.doe@company.com)')
@click.option('--email', help='User email (optional, defaults to user_id)')
@click.option('--name', help='Display name (e.g., "John Doe")')
@click.option('--expires-days', type=int, help='Token expiry in days (default: never)')
@click.option('--created-by', default='admin', help='Admin who created the token')
def create(user_id, email, name, expires_days, created_by):
    """Create a new MCP authentication token."""
    async def _create():
        conn = await get_db_connection()

        token = generate_token()
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        try:
            await conn.execute("""
                INSERT INTO mcp_auth_tokens
                    (token, user_id, user_email, display_name, expires_at, created_by)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, token, user_id, email or user_id, name, expires_at, created_by)

            await conn.close()

            # Print success message with setup instructions
            click.echo("=" * 80)
            click.echo("✅ Token created successfully!")
            click.echo("=" * 80)
            click.echo(f"Token:        {token}")
            click.echo(f"User ID:      {user_id}")
            click.echo(f"Display Name: {name or 'N/A'}")
            if expires_at:
                click.echo(f"Expires:      {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            else:
                click.echo("Expires:      Never")
            click.echo()
            click.echo("🔧 Setup Instructions:")
            click.echo()
            click.echo("1. Add to your shell profile (~/.zshrc or ~/.bashrc):")
            click.echo(f"   export MEM0_TOKEN='{token}'")
            click.echo(f"   export MEM0_USER_ID='{user_id}'")
            click.echo()
            click.echo("2. Configure Claude Code (~/.config/claude-code/config.json):")
            click.echo('''   {
     "mcpServers": {
       "mem0": {
         "url": "http://localhost:8080/sse",
         "headers": {
           "X-MCP-Token": "${MEM0_TOKEN}",
           "X-MCP-UserID": "${MEM0_USER_ID}"
         }
       }
     }
   }''')
            click.echo()
            click.echo("3. Restart your shell and Claude Code")
            click.echo("=" * 80)

        except asyncpg.UniqueViolationError:
            click.echo("❌ Error: A token already exists. This should never happen (UUID collision).", err=True)
            await conn.close()
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Error creating token: {e}", err=True)
            await conn.close()
            sys.exit(1)

    asyncio.run(_create())


@cli.command()
@click.option('--user-id', help='Filter by user ID')
@click.option('--show-tokens', is_flag=True, help='Show full tokens (security risk!)')
def list(user_id, show_tokens):
    """List all authentication tokens."""
    async def _list():
        conn = await get_db_connection()

        query = """
            SELECT
                token, user_id, user_email, display_name, enabled,
                created_at, last_used_at, expires_at
            FROM mcp_auth_tokens
        """
        params = []

        if user_id:
            query += " WHERE user_id = $1"
            params.append(user_id)

        query += " ORDER BY created_at DESC"

        rows = await conn.fetch(query, *params)
        await conn.close()

        if not rows:
            click.echo("No tokens found.")
            return

        table_data = []
        for row in rows:
            # Check if expired
            is_expired = row['expires_at'] and datetime.utcnow() > row['expires_at']
            status = "❌ Disabled" if not row['enabled'] else ("⏰ Expired" if is_expired else "✅ Active")

            table_data.append([
                row['token'] if show_tokens else row['token'][:16] + "...",
                row['user_id'],
                row['display_name'] or "N/A",
                status,
                row['created_at'].strftime('%Y-%m-%d'),
                row['last_used_at'].strftime('%Y-%m-%d %H:%M') if row['last_used_at'] else "Never",
                row['expires_at'].strftime('%Y-%m-%d') if row['expires_at'] else "Never"
            ])

        headers = ['Token', 'User ID', 'Name', 'Status', 'Created', 'Last Used', 'Expires']
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        click.echo(f"\nTotal: {len(table_data)} token(s)")

    asyncio.run(_list())


@cli.command()
@click.argument('token_prefix')
@click.confirmation_option(prompt='Are you sure you want to revoke this token?')
def revoke(token_prefix):
    """Revoke (disable) a token without deleting it."""
    async def _revoke():
        conn = await get_db_connection()

        result = await conn.execute("""
            UPDATE mcp_auth_tokens
            SET enabled = false
            WHERE token LIKE $1
        """, f"{token_prefix}%")

        await conn.close()

        if result == "UPDATE 1":
            click.echo(f"✅ Token {token_prefix}... revoked successfully")
        elif result == "UPDATE 0":
            click.echo("❌ Token not found", err=True)
            sys.exit(1)
        else:
            click.echo(f"⚠️  Warning: Multiple tokens matched ({result})")

    asyncio.run(_revoke())


@cli.command()
@click.argument('token_prefix')
def enable(token_prefix):
    """Re-enable a previously revoked token."""
    async def _enable():
        conn = await get_db_connection()

        result = await conn.execute("""
            UPDATE mcp_auth_tokens
            SET enabled = true
            WHERE token LIKE $1
        """, f"{token_prefix}%")

        await conn.close()

        if result == "UPDATE 1":
            click.echo(f"✅ Token {token_prefix}... enabled successfully")
        elif result == "UPDATE 0":
            click.echo("❌ Token not found", err=True)
            sys.exit(1)

    asyncio.run(_enable())


@cli.command()
@click.argument('token_prefix')
@click.confirmation_option(prompt='Are you sure you want to permanently delete this token?')
def delete(token_prefix):
    """Permanently delete a token (cannot be undone)."""
    async def _delete():
        conn = await get_db_connection()

        result = await conn.execute("""
            DELETE FROM mcp_auth_tokens
            WHERE token LIKE $1
        """, f"{token_prefix}%")

        await conn.close()

        if result == "DELETE 1":
            click.echo(f"✅ Token {token_prefix}... deleted permanently")
        elif result == "DELETE 0":
            click.echo("❌ Token not found", err=True)
            sys.exit(1)

    asyncio.run(_delete())


@cli.command()
@click.option('--days', default=30, help='Number of days to look back (default: 30)')
@click.option('--user-id', help='Filter by user ID')
def audit(days, user_id):
    """Show authentication audit log."""
    async def _audit():
        conn = await get_db_connection()

        query = """
            SELECT
                timestamp, user_id, action, success, error_message, ip_address
            FROM mcp_auth_audit_log
            WHERE timestamp > NOW() - INTERVAL '{} days'
        """.format(days)

        params = []
        if user_id:
            query += " AND user_id = $1"
            params.append(user_id)

        query += " ORDER BY timestamp DESC LIMIT 100"

        rows = await conn.fetch(query, *params)
        await conn.close()

        if not rows:
            click.echo("No audit log entries found.")
            return

        table_data = []
        for row in rows:
            status_icon = "✅" if row['success'] else "❌"
            table_data.append([
                row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                row['user_id'],
                row['action'],
                status_icon,
                row['error_message'] or "Success",
                row['ip_address'] or "N/A"
            ])

        headers = ['Timestamp', 'User ID', 'Action', 'Status', 'Message', 'IP Address']
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        click.echo(f"\nShowing last 100 entries from past {days} days")

    asyncio.run(_audit())


@cli.command()
@click.argument('user_id')
def stats(user_id):
    """Show statistics for a user."""
    async def _stats():
        conn = await get_db_connection()

        # Token stats
        token_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_tokens,
                SUM(CASE WHEN enabled THEN 1 ELSE 0 END) as active_tokens,
                MAX(last_used_at) as last_activity
            FROM mcp_auth_tokens
            WHERE user_id = $1
        """, user_id)

        # Login stats
        login_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_logins,
                COUNT(CASE WHEN success THEN 1 END) as successful_logins,
                COUNT(CASE WHEN NOT success THEN 1 END) as failed_logins
            FROM mcp_auth_audit_log
            WHERE user_id = $1 AND timestamp > NOW() - INTERVAL '30 days'
        """, user_id)

        await conn.close()

        click.echo("=" * 60)
        click.echo(f"📊 Statistics for {user_id}")
        click.echo("=" * 60)
        click.echo(f"Total Tokens:      {token_stats['total_tokens']}")
        click.echo(f"Active Tokens:     {token_stats['active_tokens']}")
        if token_stats['last_activity']:
            click.echo(f"Last Activity:     {token_stats['last_activity'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            click.echo("Last Activity:     Never")
        click.echo()
        click.echo("Last 30 Days:")
        click.echo(f"  Total Logins:    {login_stats['total_logins']}")
        click.echo(f"  Successful:      {login_stats['successful_logins']}")
        click.echo(f"  Failed:          {login_stats['failed_logins']}")
        click.echo("=" * 60)

    asyncio.run(_stats())


if __name__ == '__main__':
    cli()
