#!/bin/bash
# Run authentication database migrations

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔧 Running Authentication Migrations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if PostgreSQL container is running
if ! docker compose ps postgres | grep -q "Up"; then
    echo "❌ PostgreSQL container is not running"
    echo "   Please start the stack first: ./scripts/start.sh"
    exit 1
fi

echo "📂 Found migrations:"
ls -1 migrations/*.sql | sed 's/^/   /'
echo ""

# Run each migration file
for migration in migrations/*.sql; do
    echo "🔄 Running $(basename "$migration")..."
    docker compose exec -T postgres psql -U postgres -d postgres < "$migration"

    if [ $? -eq 0 ]; then
        echo "   ✅ Success"
    else
        echo "   ❌ Failed"
        exit 1
    fi
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ All Migrations Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔧 Next Steps:"
echo "  1. Create a token: python3 scripts/mcp-token.py create --user-id your.email@company.com"
echo "  2. Configure Claude Code with the token"
echo "  3. Test authentication: ./tests/test_auth.sh"
echo ""
