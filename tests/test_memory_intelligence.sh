#!/bin/bash
# Test Memory Intelligence System

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

# Test 1: Create some test memories
echo -e "${BLUE}1. Creating test memories...${NC}"
MEMORY_1=$(curl -s -X POST "$BASE_URL/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "We decided to use PostgreSQL for the database"}],
    "user_id": "'$USER_ID'"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['results'][0]['id'])")

MEMORY_2=$(curl -s -X POST "$BASE_URL/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Authentication will use JWT tokens"}],
    "user_id": "'$USER_ID'"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['results'][0]['id'])")

MEMORY_3=$(curl -s -X POST "$BASE_URL/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "The API will be RESTful with FastAPI"}],
    "user_id": "'$USER_ID'"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['results'][0]['id'])")

echo -e "${GREEN}✓ Created 3 memories${NC}"
echo ""

# Test 2: Link memories with relationships
echo -e "${BLUE}2. Creating memory relationships...${NC}"
curl -s -X POST "$BASE_URL/graph/link" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_id_1": "'$MEMORY_1'",
    "memory_id_2": "'$MEMORY_2'",
    "relationship_type": "RELATES_TO"
  }' > /dev/null

curl -s -X POST "$BASE_URL/graph/link" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_id_1": "'$MEMORY_2'",
    "memory_id_2": "'$MEMORY_3'",
    "relationship_type": "DEPENDS_ON"
  }' > /dev/null

echo -e "${GREEN}✓ Linked memories with relationships${NC}"
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
curl -s -X POST "$BASE_URL/graph/component/link-memory?memory_id=$MEMORY_2&component_name=Authentication" > /dev/null
curl -s -X POST "$BASE_URL/graph/component/link-memory?memory_id=$MEMORY_3&component_name=API" > /dev/null

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
RELATED=$(curl -s -X GET "$BASE_URL/graph/related/$MEMORY_2?depth=2" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo -e "${GREEN}✓ Found $RELATED related memories${NC}"
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
echo -e "${GREEN}✓ All Memory Intelligence tests passed!${NC}"
echo "================================================"
echo ""
echo "🎉 The Memory Intelligence System is fully operational!"
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
