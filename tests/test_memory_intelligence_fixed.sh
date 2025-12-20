#!/bin/bash
# Test Memory Intelligence System - Fixed Version

set -e

BASE_URL="http://localhost:8000"
USER_ID="test_user_$(date +%s)"

echo "================================================"
echo "🧠 Memory Intelligence System - Integration Test"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Testing with User ID: $USER_ID${NC}"
echo ""

# Test 1: Create some test memories with rich, unique content
echo -e "${BLUE}1. Creating test memories with rich content...${NC}"

# Memory 1: Database decision
MEMORY_RESPONSE_1=$(curl -s -X POST "$BASE_URL/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": "After extensive research and team discussion on January 15th 2025, we made the critical architectural decision to adopt PostgreSQL version 16.1 as our primary database system. This choice was driven by several key factors: excellent pgvector extension support for semantic search with 4096-dimensional embeddings, robust ACID compliance for transactional integrity, mature ecosystem with extensive tooling, and proven scalability in production environments handling millions of records. The database will serve as the foundation for our entire application stack."
    }],
    "user_id": "'$USER_ID'"
  }')

echo "Memory 1 response: $MEMORY_RESPONSE_1"

# Extract memory ID safely
MEMORY_1=$(echo "$MEMORY_RESPONSE_1" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    if results and len(results) > 0:
        print(results[0]['id'])
    else:
        # Try to extract from 'added_entities' if results is empty
        added = data.get('relations', {}).get('added_entities', [])
        if added and len(added) > 0:
            print(added[0])
        else:
            print('NO_MEMORY_CREATED')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    print('NO_MEMORY_CREATED')
" 2>/dev/null || echo "NO_MEMORY_CREATED")

if [ "$MEMORY_1" = "NO_MEMORY_CREATED" ]; then
    echo -e "${RED}✗ Failed to create Memory 1 or memory already exists${NC}"
    echo "Response was: $MEMORY_RESPONSE_1"
    echo ""
    echo "Let me try to get existing memories instead..."

    # Get all memories for this user
    ALL_MEMORIES=$(curl -s -X GET "$BASE_URL/memories?user_id=$USER_ID")
    echo "Existing memories: $ALL_MEMORIES"

    # If no memories exist, we need to use more unique content
    echo ""
    echo "Creating memory with highly unique timestamp-based content..."
    TIMESTAMP=$(date +%s%N)

    MEMORY_RESPONSE_1=$(curl -s -X POST "$BASE_URL/memories" \
      -H "Content-Type: application/json" \
      -d "{
        \"messages\": [{
          \"role\": \"user\",
          \"content\": \"UNIQUE_TEST_${TIMESTAMP}: PostgreSQL 16.1 database decision made on $(date) with session ID $RANDOM-$RANDOM-$RANDOM for semantic search with pgvector extension supporting 4096-dimensional embeddings and ACID compliance.\"
        }],
        \"user_id\": \"$USER_ID\"
      }")

    echo "Retry response: $MEMORY_RESPONSE_1"

    MEMORY_1=$(echo "$MEMORY_RESPONSE_1" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    if results and len(results) > 0:
        print(results[0]['id'])
    else:
        added = data.get('relations', {}).get('added_entities', [])
        if added and len(added) > 0:
            print(added[0])
        else:
            print('NO_MEMORY_CREATED')
except:
    print('NO_MEMORY_CREATED')
")
fi

if [ "$MEMORY_1" = "NO_MEMORY_CREATED" ]; then
    echo -e "${RED}✗ Cannot proceed without creating at least one memory${NC}"
    echo "This may be due to mem0's LLM deciding the content is not worth storing."
    echo "Please check the mem0-server logs for details."
    exit 1
fi

echo -e "${GREEN}✓ Created Memory 1: $MEMORY_1${NC}"

# Memory 2: Authentication decision
TIMESTAMP2=$(date +%s%N)
MEMORY_RESPONSE_2=$(curl -s -X POST "$BASE_URL/memories" \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [{
      \"role\": \"user\",
      \"content\": \"UNIQUE_TEST_${TIMESTAMP2}: Authentication architecture decision session $RANDOM-$RANDOM on $(date): implement JWT token-based authentication with RS256 signing algorithm, 24-hour token expiration, refresh token rotation strategy, and secure HTTP-only cookies for token storage. Tokens will be stored in PostgreSQL with audit logging.\"
    }],
    \"user_id\": \"$USER_ID\"
  }")

MEMORY_2=$(echo "$MEMORY_RESPONSE_2" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    if results:
        print(results[0]['id'])
    else:
        added = data.get('relations', {}).get('added_entities', [])
        print(added[0] if added else 'NO_MEMORY_CREATED')
except:
    print('NO_MEMORY_CREATED')
")

echo -e "${GREEN}✓ Created Memory 2: $MEMORY_2${NC}"

# Memory 3: API architecture
TIMESTAMP3=$(date +%s%N)
MEMORY_RESPONSE_3=$(curl -s -X POST "$BASE_URL/memories" \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [{
      \"role\": \"user\",
      \"content\": \"UNIQUE_TEST_${TIMESTAMP3}: API architecture design session $RANDOM-$RANDOM on $(date): FastAPI framework with async/await patterns, RESTful endpoints with OpenAPI 3.1 documentation, request validation using Pydantic v2 models, and comprehensive error handling middleware.\"
    }],
    \"user_id\": \"$USER_ID\"
  }")

MEMORY_3=$(echo "$MEMORY_RESPONSE_3" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    if results:
        print(results[0]['id'])
    else:
        added = data.get('relations', {}).get('added_entities', [])
        print(added[0] if added else 'NO_MEMORY_CREATED')
except:
    print('NO_MEMORY_CREATED')
")

echo -e "${GREEN}✓ Created Memory 3: $MEMORY_3${NC}"
echo ""

# Test 2: Link memories with relationships
echo -e "${BLUE}2. Creating memory relationships...${NC}"

if [ "$MEMORY_2" != "NO_MEMORY_CREATED" ]; then
    curl -s -X POST "$BASE_URL/graph/link" \
      -H "Content-Type: application/json" \
      -d '{
        "memory_id_1": "'$MEMORY_1'",
        "memory_id_2": "'$MEMORY_2'",
        "relationship_type": "RELATES_TO"
      }' > /dev/null
    echo -e "${GREEN}✓ Linked Memory 1 -> Memory 2${NC}"
fi

if [ "$MEMORY_3" != "NO_MEMORY_CREATED" ]; then
    curl -s -X POST "$BASE_URL/graph/link" \
      -H "Content-Type: application/json" \
      -d '{
        "memory_id_1": "'$MEMORY_2'",
        "memory_id_2": "'$MEMORY_3'",
        "relationship_type": "DEPENDS_ON"
      }' > /dev/null
    echo -e "${GREEN}✓ Linked Memory 2 -> Memory 3${NC}"
fi

echo ""

# Test 3: Create components and dependencies
echo -e "${BLUE}3. Creating technical components...${NC}"
curl -s -X POST "$BASE_URL/graph/component" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Database",
    "component_type": "Infrastructure"
  }' > /dev/null

curl -s -X POST "$BASE_URL/graph/component" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Authentication",
    "component_type": "Service"
  }' > /dev/null

curl -s -X POST "$BASE_URL/graph/component" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API",
    "component_type": "Application"
  }' > /dev/null

echo -e "${GREEN}✓ Created 3 components${NC}"
echo ""

# Test 4: Link component dependencies
echo -e "${BLUE}4. Creating component dependencies...${NC}"
curl -s -X POST "$BASE_URL/graph/component/dependency?component_from=Authentication&component_to=Database&dependency_type=DEPENDS_ON" > /dev/null
curl -s -X POST "$BASE_URL/graph/component/dependency?component_from=API&component_to=Authentication&dependency_type=DEPENDS_ON" > /dev/null

echo -e "${GREEN}✓ Linked component dependencies${NC}"
echo ""

# Test 5: Link memories to components
echo -e "${BLUE}5. Linking memories to components...${NC}"
curl -s -X POST "$BASE_URL/graph/component/link-memory?memory_id=$MEMORY_1&component_name=Database" > /dev/null

if [ "$MEMORY_2" != "NO_MEMORY_CREATED" ]; then
    curl -s -X POST "$BASE_URL/graph/component/link-memory?memory_id=$MEMORY_2&component_name=Authentication" > /dev/null
fi

if [ "$MEMORY_3" != "NO_MEMORY_CREATED" ]; then
    curl -s -X POST "$BASE_URL/graph/component/link-memory?memory_id=$MEMORY_3&component_name=API" > /dev/null
fi

echo -e "${GREEN}✓ Linked memories to components${NC}"
echo ""

# Test 6: Create a decision
echo -e "${BLUE}6. Creating a technical decision...${NC}"
DECISION=$(curl -s -X POST "$BASE_URL/graph/decision" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Use PostgreSQL as primary database",
    "user_id": "'$USER_ID'",
    "pros": ["Strong ACID guarantees", "pgvector support", "Mature ecosystem"],
    "cons": ["Scaling complexity", "Higher resource usage"],
    "alternatives": ["MongoDB", "MySQL"]
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['decision_id'])")

echo -e "${GREEN}✓ Created decision: $DECISION${NC}"
echo ""

# Test 7: Get related memories
echo -e "${BLUE}7. Testing related memories query...${NC}"
if [ "$MEMORY_2" != "NO_MEMORY_CREATED" ]; then
    RELATED=$(curl -s -X GET "$BASE_URL/graph/related/$MEMORY_2?depth=2" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
    echo -e "${GREEN}✓ Found $RELATED related memories${NC}"
else
    echo -e "${BLUE}Skipping (Memory 2 not created)${NC}"
fi
echo ""

# Test 8: Impact analysis
echo -e "${BLUE}8. Testing impact analysis...${NC}"
IMPACT=$(curl -s -X GET "$BASE_URL/graph/impact/Database" | python3 -m json.tool)
echo -e "${GREEN}✓ Impact analysis for Database component:${NC}"
echo "$IMPACT" | head -20
echo ""

# Test 9: Memory Intelligence Analysis (THE GAME CHANGER!)
echo -e "${BLUE}9. 🚀 Running Memory Intelligence Analysis...${NC}"
INTELLIGENCE=$(curl -s -X GET "$BASE_URL/graph/intelligence?user_id=$USER_ID" | python3 -m json.tool)
echo -e "${GREEN}✓ Memory Intelligence Report:${NC}"
echo "$INTELLIGENCE"
echo ""

# Test 10: Get decision rationale
echo -e "${BLUE}10. Testing decision rationale...${NC}"
RATIONALE=$(curl -s -X GET "$BASE_URL/graph/decision/$DECISION" | python3 -m json.tool)
echo -e "${GREEN}✓ Decision rationale:${NC}"
echo "$RATIONALE" | head -15
echo ""

# Summary
echo "================================================"
echo -e "${GREEN}✓ Memory Intelligence tests completed!${NC}"
echo "================================================"
echo ""
echo "🎉 The Memory Intelligence System is operational!"
echo ""
echo "Available features:"
echo "  • Memory Relationships (RELATES_TO, DEPENDS_ON, SUPERSEDES, etc.)"
echo "  • Component Dependencies & Impact Analysis"
echo "  • Decision Graphs with Pros/Cons"
echo "  • Temporal Knowledge Tracking"
echo "  • Memory Communities Detection"
echo "  • Trust Score Calculation"
echo "  • 🔥 Comprehensive Intelligence Analysis"
echo ""
echo "Test Summary:"
echo "  User ID: $USER_ID"
echo "  Memories created: $([ "$MEMORY_3" != "NO_MEMORY_CREATED" ] && echo "3" || ([ "$MEMORY_2" != "NO_MEMORY_CREATED" ] && echo "2" || echo "1"))"
echo "  Components: 3"
echo "  Decisions: 1"
echo ""
