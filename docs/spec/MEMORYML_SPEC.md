# MemoryML Specification v0.1

> Declarative Memory Modeling Language for AI Agents

## Overview

MemoryML (MML) is a declarative language for defining agent memory schemas, storage mappings, and retrieval strategies. Inspired by LookML's semantic layer approach, MML provides a code-first abstraction over diverse storage backends.

## Design Principles

1. **Declarative over Imperative**: Define what memories look like, not how to store them
2. **Schema-First**: Validate memory shapes before storage
3. **Backend-Agnostic**: Same schema maps to any supported backend
4. **Version-Controlled**: Memory schemas live in git
5. **Testable**: Unit tests for memory schemas
6. **Transparent**: Human-readable, auditable definitions

---

## 1. Project Structure

### Directory Layout

```
memory/
├── memory.yaml                 # Root project configuration
├── types/                      # Memory type definitions
│   ├── episodic.mml
│   ├── semantic.mml
│   └── procedural.mml
├── explores/                   # Combined retrieval views
│   ├── project_context.mml
│   └── decision_history.mml
├── backends/                   # Backend configurations
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
├── policies/                   # Retention and privacy policies
│   ├── retention.yaml
│   └── privacy.yaml
└── tests/                      # Schema and integration tests
    ├── schema_tests.yaml
    └── integration_tests.yaml
```

### File Extensions

| Extension | Purpose |
|-----------|---------|
| `.mml` | Memory type and explore definitions |
| `.yaml` | Configuration files (backends, policies, tests) |
| `memory.yaml` | Root project configuration (required) |

---

## 2. Root Configuration (memory.yaml)

The `memory.yaml` file defines project-level settings and file references.

### Schema

```yaml
# memory.yaml
version: "0.1"                    # MML spec version (required)
project: string                   # Project identifier (required)

# File references
types:                            # List of memory type files
  - types/*.mml

explores:                         # List of explore files
  - explores/*.mml

backends:                         # Backend configs per environment
  development: backends/development.yaml
  staging: backends/staging.yaml
  production: backends/production.yaml

policies:
  retention: policies/retention.yaml
  privacy: policies/privacy.yaml

# Global settings
settings:
  embedding:
    default_model: string         # Default embedding model
    dimensions: integer           # Default dimensions
    batch_size: integer           # Batch size for bulk operations

  defaults:
    retention_days: integer       # Default retention period
    importance: float             # Default importance score

  privacy:
    pii_detection: boolean        # Enable PII detection
    anonymization: enum           # none | hash | mask | redact
    audit_log: boolean            # Log all memory operations

# MCP server configuration
mcp:
  enabled: boolean
  port: integer
  tools: string[]                 # Exposed MCP tools

  sharing:
    enabled: boolean
    format: enum                  # json-ld | json | msgpack
    export_endpoint: string
    import_endpoint: string

# CLI configuration
cli:
  validate: string                # Validation command
  migrate: string                 # Migration command
  test: string                    # Test command
  serve: string                   # Server command
```

### Example

```yaml
version: "0.1"
project: agents-squads

types:
  - types/*.mml

explores:
  - explores/*.mml

backends:
  development: backends/development.yaml
  production: backends/production.yaml

settings:
  embedding:
    default_model: text-embedding-3-small
    dimensions: 1536
    batch_size: 100

  defaults:
    retention_days: 90
    importance: 0.5

  privacy:
    pii_detection: true
    anonymization: hash
    audit_log: true

mcp:
  enabled: true
  port: 8080
  tools:
    - add_memory
    - search_memories
    - get_related
    - analyze_intelligence
    - link_memories
    - delete_memory

  sharing:
    enabled: true
    format: json-ld
    export_endpoint: /export
    import_endpoint: /import
```

---

## 3. Memory Type Definitions (.mml)

Memory types define the schema, storage hints, and computed properties for a category of memories.

### Schema

```yaml
# types/{type_name}.mml
memory_type: string               # Type identifier (required)
version: string                   # Schema version (required)
description: string               # Human-readable description

# Field definitions
schema:
  required:                       # Required fields
    {field_name}:
      type: enum                  # Field type (see Type System)
      description: string
      index: enum                 # Index type (optional)
      embedding: boolean          # Generate embedding (optional)
      embedding_model: string     # Override default model (optional)
      # Type-specific options...

  optional:                       # Optional fields
    {field_name}:
      type: enum
      default: any                # Default value
      nullable: boolean           # Allow null (default: true)
      # Type-specific options...

# Computed fields (derived at query time)
computed:
  {field_name}:
    expression: string            # SQL/expression syntax
    type: enum                    # Result type
    description: string

# Relationships to other memory types
relationships:
  - name: string                  # Relationship name
    target: string                # Target memory type
    type: enum                    # one_to_one | one_to_many | many_to_many
    via: enum                     # foreign_key | knowledge_graph
    inverse: string               # Inverse relationship name (optional)
    cascade: enum                 # none | delete | nullify (optional)

# Graph-specific definitions (for semantic memories)
graph:
  node_label: string              # Neo4j node label (supports templates)

  edge_types:
    - name: string                # Relationship type name
      bidirectional: boolean      # Two-way relationship
      properties:                 # Edge properties
        {prop_name}:
          type: enum
          default: any

# Storage configuration
storage:
  primary_backend: enum           # vector | graph | document | relational
  secondary_backend: enum         # Optional secondary storage

  indexes:
    - fields: string[]            # Fields to index
      type: enum                  # btree | hash | hnsw | gin | gist
      options:                    # Index-specific options
        distance: enum            # For HNSW: cosine | l2 | ip
        m: integer                # HNSW m parameter
        ef_construction: integer  # HNSW ef_construction

  partitioning:
    enabled: boolean
    key: string                   # Partition key field
    strategy: enum                # range | hash | list

  retention:
    default: duration             # Default retention (e.g., "90d")
    compressed_after: duration    # Compress after duration
    summarized_after: duration    # Summarize after duration
    archived_after: duration      # Archive after duration

# Access pattern hints (for query optimization)
access_patterns:
  - name: string
    description: string
    query: string                 # Example query pattern
    frequency: enum               # high | medium | low
```

### Type System

| Type | Description | Options |
|------|-------------|---------|
| `string` | Text up to max_length | `max_length`, `pattern` (regex) |
| `text` | Unlimited text | `embedding` |
| `integer` | Signed integer | `min`, `max` |
| `float` | Floating point | `range: [min, max]` |
| `boolean` | True/false | - |
| `datetime` | ISO 8601 timestamp | `auto_now`, `auto_now_add` |
| `date` | Date only | - |
| `duration` | Time duration | - |
| `uuid` | UUID v4 | `auto_generate` |
| `enum` | Enumerated values | `values: [...]` |
| `array` | List of items | `items: {type}`, `max_items` |
| `object` | Nested object | `properties: {...}` |
| `json` | Arbitrary JSON | - |

### Index Types

| Type | Use Case | Backends |
|------|----------|----------|
| `btree` | Range queries, sorting | PostgreSQL, SQLite |
| `hash` | Equality lookups | PostgreSQL |
| `hnsw` | Vector similarity | pgvector, Pinecone |
| `gin` | Full-text search | PostgreSQL |
| `gist` | Geometric/range types | PostgreSQL |
| `fulltext` | Text search | PostgreSQL, Elasticsearch |
| `temporal` | Time-series queries | TimescaleDB, PostgreSQL |
| `graph` | Graph traversal | Neo4j |

### Example: Episodic Memory Type

```yaml
# types/episodic.mml
memory_type: episodic
version: "1.0"
description: "Time-stamped interaction records, events, and experiences"

schema:
  required:
    id:
      type: uuid
      auto_generate: true
      description: "Unique memory identifier"

    timestamp:
      type: datetime
      auto_now_add: true
      index: temporal
      description: "When the memory was created"

    content:
      type: text
      embedding: true
      description: "The memory content"

    agent_id:
      type: string
      max_length: 64
      index: hash
      description: "Agent that created this memory"

    session_id:
      type: uuid
      index: hash
      description: "Session this memory belongs to"

  optional:
    context:
      type: object
      description: "Contextual metadata"
      properties:
        tool:
          type: string
          description: "Tool used (claude-code, cursor, etc.)"
        project:
          type: string
          description: "Project name"
        file:
          type: string
          description: "Current file path"
        branch:
          type: string
          description: "Git branch"
        commit:
          type: string
          description: "Git commit hash"

    importance:
      type: float
      range: [0, 1]
      default: 0.5
      description: "Relevance score for retrieval priority"

    tags:
      type: array
      items:
        type: string
      description: "Categorization tags"

    parent_id:
      type: uuid
      nullable: true
      description: "Parent memory for threading"

    metadata:
      type: json
      description: "Flexible additional data"

computed:
  age_seconds:
    expression: "EXTRACT(EPOCH FROM (NOW() - timestamp))"
    type: float
    description: "Age in seconds"

  age_hours:
    expression: "EXTRACT(EPOCH FROM (NOW() - timestamp)) / 3600"
    type: float
    description: "Age in hours"

  recency_score:
    expression: "EXP(-EXTRACT(EPOCH FROM (NOW() - timestamp)) / 604800)"
    type: float
    description: "Exponential decay score (1 week half-life)"

  retrieval_score:
    expression: "importance * recency_score"
    type: float
    description: "Combined retrieval priority"

relationships:
  - name: related_semantic
    target: semantic
    type: many_to_many
    via: knowledge_graph

  - name: triggered_actions
    target: procedural
    type: one_to_many
    via: foreign_key

  - name: parent
    target: episodic
    type: many_to_one
    via: foreign_key

storage:
  primary_backend: vector

  indexes:
    - fields: [timestamp]
      type: btree
    - fields: [agent_id, session_id]
      type: hash
    - fields: [content]
      type: hnsw
      options:
        distance: cosine
        m: 16
        ef_construction: 64
    - fields: [tags]
      type: gin

  partitioning:
    enabled: true
    key: timestamp
    strategy: range

  retention:
    default: 90d
    compressed_after: 7d
    summarized_after: 30d

access_patterns:
  - name: recent_context
    description: "Get recent memories for context window"
    query: |
      timestamp > NOW() - INTERVAL '24 hours'
      ORDER BY timestamp DESC
      LIMIT 20
    frequency: high

  - name: session_history
    description: "Get all memories from a session"
    query: |
      session_id = $session_id
      ORDER BY timestamp ASC
    frequency: high

  - name: semantic_search
    description: "Find similar memories by content"
    query: |
      ORDER BY content <=> $query_embedding
      LIMIT $k
    frequency: high

  - name: by_importance
    description: "Get most important memories"
    query: |
      ORDER BY retrieval_score DESC
      LIMIT $k
    frequency: medium
```

### Example: Semantic Memory Type

```yaml
# types/semantic.mml
memory_type: semantic
version: "1.0"
description: "Factual knowledge, concepts, entities, and their relationships"

schema:
  required:
    id:
      type: uuid
      auto_generate: true

    entity_type:
      type: enum
      values:
        - concept
        - fact
        - preference
        - decision
        - component
        - person
        - organization
        - technology
      index: hash
      description: "Classification of the entity"

    name:
      type: string
      max_length: 255
      index: fulltext
      description: "Entity name or title"

    content:
      type: text
      embedding: true
      description: "Detailed description or content"

    agent_id:
      type: string
      max_length: 64
      index: hash

  optional:
    properties:
      type: json
      description: "Flexible key-value attributes"

    confidence:
      type: float
      range: [0, 1]
      default: 1.0
      description: "Confidence in this knowledge"

    source:
      type: object
      properties:
        type:
          type: enum
          values: [user_stated, inferred, external, observed]
        reference:
          type: string
        timestamp:
          type: datetime

    valid_from:
      type: datetime
      auto_now_add: true
      description: "When this fact became true"

    valid_until:
      type: datetime
      nullable: true
      description: "When this fact stopped being true (null = current)"

    supersedes:
      type: uuid
      nullable: true
      description: "ID of memory this supersedes"

    tags:
      type: array
      items:
        type: string

computed:
  is_current:
    expression: "valid_until IS NULL OR valid_until > NOW()"
    type: boolean
    description: "Whether this fact is currently valid"

  age_days:
    expression: "EXTRACT(EPOCH FROM (NOW() - valid_from)) / 86400"
    type: float

relationships:
  - name: related_to
    target: semantic
    type: many_to_many
    via: knowledge_graph

  - name: derived_from
    target: episodic
    type: many_to_many
    via: knowledge_graph

graph:
  node_label: "{{entity_type | capitalize}}"

  edge_types:
    - name: RELATES_TO
      bidirectional: true
      properties:
        strength:
          type: float
          default: 1.0
        context:
          type: string

    - name: DEPENDS_ON
      bidirectional: false
      properties:
        dependency_type:
          type: string
        critical:
          type: boolean
          default: false

    - name: SUPERSEDES
      bidirectional: false
      properties:
        superseded_at:
          type: datetime
        reason:
          type: string

    - name: PART_OF
      bidirectional: false
      properties:
        role:
          type: string

    - name: CONFLICTS_WITH
      bidirectional: true
      properties:
        detected_at:
          type: datetime
        resolved:
          type: boolean
          default: false

storage:
  primary_backend: graph
  secondary_backend: vector

  indexes:
    - fields: [entity_type, name]
      type: btree
    - fields: [content]
      type: hnsw
      options:
        distance: cosine
    - fields: [name]
      type: fulltext

  retention:
    default: 365d
    archived_after: 180d

access_patterns:
  - name: by_type
    description: "Get all entities of a type"
    query: |
      entity_type = $type AND is_current = true
      ORDER BY confidence DESC
    frequency: high

  - name: graph_neighbors
    description: "Get connected entities"
    query: |
      MATCH (n:Memory {id: $id})-[r*1..2]-(m:Memory)
      RETURN m, r
    frequency: high
```

### Example: Procedural Memory Type

```yaml
# types/procedural.mml
memory_type: procedural
version: "1.0"
description: "Skills, patterns, workflows, and learned behaviors"

schema:
  required:
    id:
      type: uuid
      auto_generate: true

    name:
      type: string
      max_length: 255
      index: hash
      description: "Skill or pattern name"

    category:
      type: enum
      values:
        - coding_pattern
        - workflow
        - tool_usage
        - debugging
        - communication
        - refactoring
        - testing
        - deployment
      index: hash

    description:
      type: text
      embedding: true
      description: "What this skill does"

    agent_id:
      type: string
      max_length: 64
      index: hash

  optional:
    implementation:
      type: object
      description: "Code or workflow definition"
      properties:
        language:
          type: string
        code:
          type: text
        dependencies:
          type: array
          items:
            type: string
        inputs:
          type: array
          items:
            type: object
            properties:
              name:
                type: string
              type:
                type: string
              required:
                type: boolean
        outputs:
          type: array
          items:
            type: object
            properties:
              name:
                type: string
              type:
                type: string

    trigger_conditions:
      type: array
      description: "When to suggest this skill"
      items:
        type: object
        properties:
          context:
            type: string
          keywords:
            type: array
            items:
              type: string
          file_patterns:
            type: array
            items:
              type: string

    examples:
      type: array
      description: "Usage examples"
      items:
        type: object
        properties:
          input:
            type: text
          output:
            type: text
          context:
            type: string
          success:
            type: boolean

    metrics:
      type: object
      description: "Performance tracking"
      properties:
        usage_count:
          type: integer
          default: 0
        success_count:
          type: integer
          default: 0
        last_used:
          type: datetime
        avg_duration_ms:
          type: float

    version:
      type: string
      default: "1.0"

    deprecated:
      type: boolean
      default: false

    superseded_by:
      type: uuid
      nullable: true

computed:
  success_rate:
    expression: |
      CASE WHEN metrics->>'usage_count'::int > 0
      THEN (metrics->>'success_count'::float) / (metrics->>'usage_count'::float)
      ELSE 0 END
    type: float

  effectiveness_score:
    expression: |
      CASE WHEN metrics->>'usage_count'::int > 0
      THEN success_rate * LN(metrics->>'usage_count'::float + 1)
      ELSE 0 END
    type: float

  is_active:
    expression: "NOT deprecated AND superseded_by IS NULL"
    type: boolean

relationships:
  - name: depends_on
    target: procedural
    type: many_to_many
    via: knowledge_graph

  - name: related_concepts
    target: semantic
    type: many_to_many
    via: knowledge_graph

storage:
  primary_backend: document
  secondary_backend: vector

  indexes:
    - fields: [category, name]
      type: btree
    - fields: [description]
      type: hnsw
      options:
        distance: cosine
    - fields: [trigger_conditions]
      type: gin

  retention:
    default: 730d  # 2 years

access_patterns:
  - name: by_category
    description: "Get skills in a category"
    query: |
      category = $category AND is_active = true
      ORDER BY effectiveness_score DESC
    frequency: high

  - name: trigger_match
    description: "Find skills matching context"
    query: |
      trigger_conditions @> $context
      AND is_active = true
      ORDER BY effectiveness_score DESC
    frequency: high
```

---

## 4. Explore Definitions (.mml)

Explores define combined views over multiple memory types with retrieval strategies.

### Schema

```yaml
# explores/{explore_name}.mml
explore: string                   # Explore identifier (required)
version: string                   # Schema version (required)
description: string               # Human-readable description

# Data sources
sources:
  - type: string                  # Memory type name
    alias: string                 # Alias for this source
    filter: string                # Pre-filter expression (optional)
    required: boolean             # Must have results (default: false)

# Join definitions
joins:
  - from: string                  # Source alias
    to: string                    # Target alias
    on: string                    # Join condition or relationship name
    type: enum                    # inner | left | right | full
    via: enum                     # foreign_key | graph_path (optional)
    max_depth: integer            # For graph paths (optional)

# Output field selection
fields:
  - source: string                # Source alias
    include: string[]             # Fields to include (or "*")
    exclude: string[]             # Fields to exclude (optional)
    rename:                       # Field renames (optional)
      {old_name}: {new_name}
    when: string                  # Conditional inclusion (optional)

# Retrieval configuration
retrieval:
  default:
    method: enum                  # vector | graph | hybrid | keyword
    components:
      - type: enum                # Component type
        weight: float             # Weight in hybrid (0-1)
        source: string[]          # Fields to search (optional)
        filter: string            # Additional filter (optional)
        options: object           # Component-specific options

  strategies:                     # Named alternative strategies
    {strategy_name}:
      method: enum
      components: [...]

# Result limits and pagination
limits:
  default: integer
  max: integer

  token_budget:
    enabled: boolean
    max_tokens: integer
    priority: string[]            # Source priority for truncation

# Caching configuration
cache:
  enabled: boolean
  ttl: duration
  invalidation: enum              # write_through | write_behind | manual
```

### Retrieval Components

| Type | Description | Options |
|------|-------------|---------|
| `vector_search` | Semantic similarity | `embedding_field`, `k`, `threshold` |
| `keyword_search` | Full-text search | `fields`, `boost` |
| `graph_traversal` | Graph exploration | `start`, `depth`, `edge_types` |
| `recency` | Time-based ranking | `field`, `decay_rate` |
| `importance` | Score-based ranking | `field` |
| `procedural_match` | Skill matching | `context_field` |

### Example: Project Context Explore

```yaml
# explores/project_context.mml
explore: project_context
version: "1.0"
description: "Unified view for retrieving relevant project context"

sources:
  - type: episodic
    alias: events
    filter: "timestamp > NOW() - INTERVAL '7 days'"

  - type: semantic
    alias: knowledge
    filter: "is_current = true"

  - type: procedural
    alias: skills
    filter: "is_active = true"

joins:
  - from: events
    to: knowledge
    on: related_semantic
    type: left
    via: graph_path
    max_depth: 2

  - from: knowledge
    to: skills
    on: related_concepts
    type: left

fields:
  - source: events
    include:
      - content
      - timestamp
      - context
      - importance
    rename:
      content: event_content
      timestamp: event_time

  - source: knowledge
    include:
      - name
      - entity_type
      - content
      - confidence
    rename:
      content: knowledge_content
    when: "confidence > 0.5"

  - source: skills
    include:
      - name
      - category
      - description
      - implementation.code
    when: "effectiveness_score > 0.3"

retrieval:
  default:
    method: hybrid
    components:
      - type: vector_search
        weight: 0.5
        source:
          - events.content
          - knowledge.content
          - skills.description
        options:
          k: 20
          threshold: 0.7

      - type: graph_traversal
        weight: 0.3
        options:
          start: knowledge
          depth: 2
          edge_types:
            - RELATES_TO
            - DEPENDS_ON

      - type: recency
        weight: 0.2
        options:
          field: events.timestamp
          decay_rate: 0.1

  strategies:
    coding_focus:
      method: hybrid
      components:
        - type: vector_search
          weight: 0.4
          filter: "context->>'tool' = 'claude-code'"

        - type: procedural_match
          weight: 0.4
          options:
            context_field: trigger_conditions

        - type: recency
          weight: 0.2

    research_mode:
      method: hybrid
      components:
        - type: vector_search
          weight: 0.6
          source:
            - knowledge.content

        - type: graph_traversal
          weight: 0.4
          options:
            depth: 3

limits:
  default: 20
  max: 100

  token_budget:
    enabled: true
    max_tokens: 4000
    priority:
      - skills
      - knowledge
      - events

cache:
  enabled: true
  ttl: 5m
  invalidation: write_through
```

---

## 5. Backend Configuration

Backend configurations define storage connections and mappings.

### Schema

```yaml
# backends/{environment}.yaml
version: string
environment: string

# Connection definitions
connections:
  {connection_name}:
    type: enum                    # postgresql | neo4j | redis | sqlite | pinecone
    # Connection-specific options
    host: string
    port: integer
    database: string
    user: string
    password: string              # Supports ${ENV_VAR} syntax
    pool_size: integer
    # Additional options per type...

# Memory type to backend mapping
mapping:
  {memory_type}:
    primary: string               # Connection name
    secondary: string             # Optional secondary connection
    features:
      embedding: string           # Where embeddings stored
      graph: string               # Where graph data stored
      temporal_index: string      # Index type for time queries

# Caching configuration
cache:
  backend: string                 # Connection name
  ttl:
    {memory_type}: duration
  invalidation:
    strategy: enum

# Synchronization settings
sync:
  embedding_sync:
    enabled: boolean
    batch_size: integer
    interval: duration

  graph_sync:
    enabled: boolean
    conflict_resolution: enum     # latest_wins | manual | merge
```

### Example: Production Backend

```yaml
# backends/production.yaml
version: "1.0"
environment: production

connections:
  postgres:
    type: postgresql
    host: ${POSTGRES_HOST}
    port: 5432
    database: engram
    user: ${POSTGRES_USER}
    password: ${POSTGRES_PASSWORD}
    pool_size: 20
    ssl_mode: require
    extensions:
      - pgvector
      - pg_trgm

  neo4j:
    type: neo4j
    uri: ${NEO4J_URI}
    user: ${NEO4J_USER}
    password: ${NEO4J_PASSWORD}
    database: memories
    max_connection_lifetime: 3600
    encrypted: true

  redis:
    type: redis
    host: ${REDIS_HOST}
    port: 6379
    password: ${REDIS_PASSWORD}
    db: 0
    ssl: true

mapping:
  episodic:
    primary: postgres
    features:
      embedding: pgvector
      temporal_index: btree

  semantic:
    primary: neo4j
    secondary: postgres
    features:
      graph: neo4j
      embedding: postgres.pgvector

  procedural:
    primary: postgres
    features:
      document: jsonb
      embedding: pgvector

cache:
  backend: redis
  ttl:
    episodic: 5m
    semantic: 1h
    procedural: 24h
  invalidation:
    strategy: write_through

sync:
  embedding_sync:
    enabled: true
    batch_size: 100
    interval: 60s

  graph_sync:
    enabled: true
    conflict_resolution: latest_wins
```

---

## 6. Policy Definitions

### Retention Policy

```yaml
# policies/retention.yaml
version: "1.0"

defaults:
  retention: 90d
  archive_after: 30d
  delete_after: 365d

rules:
  - name: high_importance
    condition: "importance > 0.8"
    retention: 365d
    archive_after: 90d

  - name: low_importance
    condition: "importance < 0.2"
    retention: 30d
    summarize_after: 7d

  - name: system_memories
    condition: "agent_id = 'system'"
    retention: 730d

compression:
  enabled: true
  after: 7d
  algorithm: zstd

summarization:
  enabled: true
  after: 30d
  model: gpt-4o-mini
  max_length: 500

archival:
  enabled: true
  backend: s3
  bucket: ${ARCHIVE_BUCKET}
  prefix: memories/
```

### Privacy Policy

```yaml
# policies/privacy.yaml
version: "1.0"

pii_detection:
  enabled: true
  patterns:
    - name: email
      pattern: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
      action: hash
    - name: phone
      pattern: "\\+?[1-9]\\d{1,14}"
      action: mask
    - name: ssn
      pattern: "\\d{3}-\\d{2}-\\d{4}"
      action: redact
    - name: credit_card
      pattern: "\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}"
      action: redact

anonymization:
  default_action: hash
  salt: ${ANONYMIZATION_SALT}

audit_log:
  enabled: true
  include:
    - create
    - read
    - update
    - delete
    - export
  exclude_fields:
    - content  # Don't log actual content
  retention: 90d

access_control:
  enabled: true
  default_policy: owner_only
  policies:
    - name: shared_knowledge
      memory_types: [semantic]
      access: team
    - name: personal_history
      memory_types: [episodic]
      access: owner_only
```

---

## 7. Test Definitions

### Schema

```yaml
# tests/{test_file}.yaml
version: string

tests:
  - name: string                  # Test name
    type: enum                    # Test type
    # Type-specific options...
    expect: enum                  # Expected outcome
    error_contains: string        # For expected failures
```

### Test Types

| Type | Purpose | Options |
|------|---------|---------|
| `schema_validation` | Validate memory against schema | `memory_type`, `fixtures` |
| `relationship_validation` | Check graph integrity | `memory_type`, `assertions` |
| `explore_test` | Test explore queries | `explore`, `query`, `assertions` |
| `integration` | Test backend connectivity | `backends`, `assertions` |
| `performance` | Test query performance | `query`, `max_latency_ms` |

### Example

```yaml
# tests/schema_tests.yaml
version: "1.0"

tests:
  - name: episodic_valid_minimal
    type: schema_validation
    memory_type: episodic
    fixtures:
      - timestamp: "2025-01-15T10:30:00Z"
        content: "User asked about memory architecture"
        agent_id: "claude-code"
        session_id: "550e8400-e29b-41d4-a716-446655440000"
    expect: valid

  - name: episodic_missing_content
    type: schema_validation
    memory_type: episodic
    fixtures:
      - timestamp: "2025-01-15T10:30:00Z"
        agent_id: "claude-code"
        session_id: "550e8400-e29b-41d4-a716-446655440000"
    expect: invalid
    error_contains: "content is required"

  - name: episodic_invalid_importance
    type: schema_validation
    memory_type: episodic
    fixtures:
      - timestamp: "2025-01-15T10:30:00Z"
        content: "Test memory"
        agent_id: "claude-code"
        session_id: "550e8400-e29b-41d4-a716-446655440000"
        importance: 1.5  # Invalid: exceeds range
    expect: invalid
    error_contains: "importance must be between 0 and 1"

  - name: semantic_graph_no_cycles
    type: relationship_validation
    memory_type: semantic
    assertions:
      - "No circular DEPENDS_ON relationships exist"
      - "All SUPERSEDES edges have valid target"

  - name: project_context_returns_results
    type: explore_test
    explore: project_context
    query:
      text: "memory architecture design patterns"
      limit: 10
    assertions:
      - "result.count > 0"
      - "result.count <= 10"
      - "all results have 'event_content' or 'knowledge_content'"

  - name: backend_health
    type: integration
    backends:
      - postgres
      - neo4j
    assertions:
      - "connection.healthy = true"
      - "connection.latency_ms < 100"

  - name: search_performance
    type: performance
    query:
      explore: project_context
      text: "test query"
      limit: 20
    max_latency_ms: 500
```

---

## 8. CLI Commands

The engram CLI provides commands for working with MML files.

```bash
# Validate all MML files
engram validate

# Validate specific file
engram validate types/episodic.mml

# Generate migrations from schema changes
engram migrate generate

# Apply migrations
engram migrate apply

# Run tests
engram test

# Run specific test file
engram test tests/schema_tests.yaml

# Start MCP server
engram serve

# Export memories
engram export --format json-ld --output memories.jsonld

# Import memories
engram import --file memories.jsonld

# Show schema documentation
engram docs

# Generate TypeScript types from schemas
engram codegen --lang typescript --output types/
```

---

## 9. MCP Tool Specifications

When MCP is enabled, engram exposes these tools:

### add_memory

```json
{
  "name": "add_memory",
  "description": "Store a new memory",
  "parameters": {
    "type": "object",
    "properties": {
      "memory_type": {
        "type": "string",
        "enum": ["episodic", "semantic", "procedural"]
      },
      "content": {
        "type": "string",
        "description": "Memory content"
      },
      "metadata": {
        "type": "object",
        "description": "Additional fields per memory type schema"
      }
    },
    "required": ["memory_type", "content"]
  }
}
```

### search_memories

```json
{
  "name": "search_memories",
  "description": "Search memories using an explore",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "explore": {
        "type": "string",
        "default": "project_context"
      },
      "strategy": {
        "type": "string",
        "description": "Retrieval strategy name"
      },
      "limit": {
        "type": "integer",
        "default": 10
      },
      "filters": {
        "type": "object",
        "description": "Additional filters"
      }
    },
    "required": ["query"]
  }
}
```

### link_memories

```json
{
  "name": "link_memories",
  "description": "Create relationship between memories",
  "parameters": {
    "type": "object",
    "properties": {
      "from_id": {
        "type": "string"
      },
      "to_id": {
        "type": "string"
      },
      "relationship_type": {
        "type": "string",
        "enum": ["RELATES_TO", "DEPENDS_ON", "SUPERSEDES", "EXTENDS", "CONFLICTS_WITH"]
      },
      "properties": {
        "type": "object"
      }
    },
    "required": ["from_id", "to_id", "relationship_type"]
  }
}
```

### get_related

```json
{
  "name": "get_related",
  "description": "Get memories related to a specific memory",
  "parameters": {
    "type": "object",
    "properties": {
      "memory_id": {
        "type": "string"
      },
      "depth": {
        "type": "integer",
        "default": 2
      },
      "relationship_types": {
        "type": "array",
        "items": {"type": "string"}
      }
    },
    "required": ["memory_id"]
  }
}
```

### analyze_intelligence

```json
{
  "name": "analyze_intelligence",
  "description": "Generate intelligence report about memory graph",
  "parameters": {
    "type": "object",
    "properties": {
      "include": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["health", "clusters", "conflicts", "recommendations"]
        }
      }
    }
  }
}
```

---

## 10. Export/Import Format

For cross-tool memory sharing, engram uses JSON-LD format.

### JSON-LD Context

```json
{
  "@context": {
    "@vocab": "https://engram.dev/schema/",
    "memory": "https://engram.dev/schema/memory#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",

    "Memory": "memory:Memory",
    "Episodic": "memory:Episodic",
    "Semantic": "memory:Semantic",
    "Procedural": "memory:Procedural",

    "id": "@id",
    "type": "@type",
    "timestamp": {"@type": "xsd:dateTime"},
    "content": "memory:content",
    "embedding": "memory:embedding",
    "relationships": {"@container": "@set"}
  }
}
```

### Example Export

```json
{
  "@context": "https://engram.dev/schema/context.jsonld",
  "@graph": [
    {
      "@type": "Episodic",
      "id": "urn:engram:memory:550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2025-01-15T10:30:00Z",
      "content": "User prefers TypeScript over JavaScript",
      "agent_id": "claude-code",
      "session_id": "session-123",
      "importance": 0.8,
      "relationships": [
        {
          "@type": "RELATES_TO",
          "target": "urn:engram:memory:660f9500-f30c-52e5-b827-557766551111"
        }
      ]
    }
  ]
}
```

---

## Appendix A: Migration from Current Engram

### Phase 1: Add Schema Validation

1. Create `memory.yaml` and type definitions
2. Add validation layer to existing API
3. Migrate existing memories to include `memory_type` field

### Phase 2: Backend Abstraction

1. Create backend interface
2. Wrap existing pgvector operations
3. Wrap existing Neo4j operations
4. Add configuration-based backend selection

### Phase 3: Explore Engine

1. Implement explore parser
2. Build hybrid retrieval engine
3. Add token budget management
4. Optimize query planning

### Phase 4: Full MML Support

1. CLI tooling
2. Test framework
3. Documentation generator
4. Cross-tool export/import

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Memory Type** | Schema definition for a category of memories (episodic, semantic, procedural) |
| **Explore** | Combined view over multiple memory types with retrieval strategy |
| **Backend** | Storage engine (PostgreSQL, Neo4j, etc.) |
| **MML** | MemoryML - the declarative language for memory definitions |
| **Retrieval Strategy** | Algorithm for finding relevant memories (vector, graph, hybrid) |

---

*MemoryML Specification v0.1 - December 2025*
*Built by agents-squads*
