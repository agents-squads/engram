"""
Memory Intelligence System - Graph Analysis Engine

Leverages Neo4j for advanced knowledge graph operations:
- Temporal knowledge tracking
- Dependency mapping
- Context chains
- Decision graphs
- Automated insights
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from neo4j import GraphDatabase, Driver
from collections import Counter

logger = logging.getLogger(__name__)


class MemoryIntelligence:
    """Advanced graph-based memory intelligence system."""

    def __init__(self, uri: str, username: str, password: str):
        """Initialize connection to Neo4j."""
        self.driver: Driver = GraphDatabase.driver(uri, auth=(username, password))
        logger.info(f"Memory Intelligence System connected to Neo4j at {uri}")

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    # ============================================
    # 1. MEMORY RELATIONSHIPS
    # ============================================

    def link_memories(
        self,
        memory_id_1: str,
        memory_id_2: str,
        relationship_type: str = "RELATES_TO",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a relationship between two memories.

        Relationship types:
        - RELATES_TO: General association
        - DEPENDS_ON: Dependency (e.g., feature depends on infrastructure)
        - SUPERSEDES: Replaces old knowledge
        - RESPONDS_TO: Conversation thread
        - EXTENDS: Adds detail to previous memory
        - CONFLICTS_WITH: Contradictory information
        """
        with self.driver.session() as session:
            if metadata:
                result = session.run("""
                    MATCH (m1:Memory {id: $id1})
                    MATCH (m2:Memory {id: $id2})
                    MERGE (m1)-[r:%s]->(m2)
                    SET r.created = datetime(),
                        r.metadata = $metadata
                    RETURN m1.id as from_id, type(r) as rel_type, m2.id as to_id
                """ % relationship_type, id1=memory_id_1, id2=memory_id_2, metadata=metadata)
            else:
                result = session.run("""
                    MATCH (m1:Memory {id: $id1})
                    MATCH (m2:Memory {id: $id2})
                    MERGE (m1)-[r:%s]->(m2)
                    SET r.created = datetime()
                    RETURN m1.id as from_id, type(r) as rel_type, m2.id as to_id
                """ % relationship_type, id1=memory_id_1, id2=memory_id_2)

            record = result.single()
            if record:
                return {
                    "from_memory_id": record["from_id"],
                    "relationship": record["rel_type"],
                    "to_memory_id": record["to_id"],
                    "metadata": metadata
                }
            return {"error": "Memories not found"}

    def get_related_memories(
        self,
        memory_id: str,
        depth: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get all memories related to a specific memory within N hops."""
        rel_filter = ""
        if relationship_types:
            rel_filter = f":{''|''.join(relationship_types)}"

        with self.driver.session() as session:
            result = session.run(f"""
                MATCH path = (start:Memory {{id: $id}})-[r{rel_filter}*1..{depth}]-(related:Memory)
                RETURN DISTINCT related.id as memory_id,
                       related.text as text,
                       [rel in relationships(path) | type(rel)] as relationship_path,
                       length(path) as distance
                ORDER BY distance
            """, id=memory_id)

            return [
                {
                    "memory_id": record["memory_id"],
                    "text": record["text"],
                    "relationship_path": record["relationship_path"],
                    "distance": record["distance"]
                }
                for record in result
            ]

    def find_path(self, from_memory_id: str, to_memory_id: str) -> Optional[List[Dict[str, Any]]]:
        """Find the shortest path between two memories."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = shortestPath(
                    (start:Memory {id: $from_id})-[*]-(end:Memory {id: $to_id})
                )
                RETURN [node in nodes(path) | node.id] as memory_ids,
                       [rel in relationships(path) | type(rel)] as relationships,
                       length(path) as path_length
            """, from_id=from_memory_id, to_id=to_memory_id)

            record = result.single()
            if record:
                return {
                    "memory_ids": record["memory_ids"],
                    "relationships": record["relationships"],
                    "path_length": record["path_length"]
                }
            return None

    # ============================================
    # 2. TEMPORAL KNOWLEDGE GRAPHS
    # ============================================

    def get_memory_evolution(
        self,
        topic: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Track how knowledge about a topic has evolved over time."""
        date_filter = ""
        params = {"topic": topic}

        if start_date:
            date_filter += " AND m.created >= $start_date"
            params["start_date"] = start_date.isoformat()
        if end_date:
            date_filter += " AND m.created <= $end_date"
            params["end_date"] = end_date.isoformat()

        with self.driver.session() as session:
            result = session.run(f"""
                MATCH (m:Memory)
                WHERE m.topic = $topic{date_filter}
                OPTIONAL MATCH (m)-[s:SUPERSEDES]->(old:Memory)
                RETURN m.id as memory_id,
                       m.text as text,
                       m.created as created,
                       m.version as version,
                       old.id as superseded_id,
                       old.text as superseded_text
                ORDER BY m.created ASC
            """, **params)

            return [
                {
                    "memory_id": record["memory_id"],
                    "text": record["text"],
                    "created": record["created"],
                    "version": record["version"],
                    "superseded": {
                        "id": record["superseded_id"],
                        "text": record["superseded_text"]
                    } if record["superseded_id"] else None
                }
                for record in result
            ]

    def find_superseded_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """Find all memories that have been superseded (outdated)."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (current:Memory)-[:SUPERSEDES]->(old:Memory)
                WHERE old.user_id = $user_id
                RETURN old.id as obsolete_id,
                       old.text as obsolete_text,
                       old.created as obsolete_date,
                       current.id as current_id,
                       current.text as current_text,
                       current.created as updated_date
                ORDER BY current.created DESC
            """, user_id=user_id)

            return [
                {
                    "obsolete_memory": {
                        "id": record["obsolete_id"],
                        "text": record["obsolete_text"],
                        "date": record["obsolete_date"]
                    },
                    "current_memory": {
                        "id": record["current_id"],
                        "text": record["current_text"],
                        "date": record["updated_date"]
                    }
                }
                for record in result
            ]

    # ============================================
    # 3. CONTEXT CHAINS & CONVERSATION THREADS
    # ============================================

    def create_conversation_thread(
        self,
        memories: List[str],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Link memories into a conversation thread."""
        if len(memories) < 2:
            return {"error": "Need at least 2 memories for a thread"}

        with self.driver.session() as session:
            # Create sequential RESPONDS_TO relationships
            for i in range(len(memories) - 1):
                session.run("""
                    MATCH (m1:Memory {id: $id1})
                    MATCH (m2:Memory {id: $id2})
                    MERGE (m2)-[r:RESPONDS_TO]->(m1)
                    SET r.position = $position,
                        r.session_id = $session_id
                """, id1=memories[i], id2=memories[i+1], position=i, session_id=session_id)

            return {
                "thread_length": len(memories),
                "session_id": session_id,
                "memory_ids": memories
            }

    def get_conversation_thread(self, memory_id: str) -> List[Dict[str, Any]]:
        """Get the full conversation thread for a memory."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = (start:Memory)-[:RESPONDS_TO*0..]->(m:Memory {id: $id})
                MATCH (m)-[:RESPONDS_TO*0..]->(end:Memory)
                WHERE NOT (end)-[:RESPONDS_TO]->()
                WITH nodes(path) + nodes((m)-[:RESPONDS_TO*]->(end)) as thread
                UNWIND thread as memory
                RETURN DISTINCT memory.id as memory_id,
                       memory.text as text,
                       memory.created as created
                ORDER BY created ASC
            """, id=memory_id)

            return [
                {
                    "memory_id": record["memory_id"],
                    "text": record["text"],
                    "created": record["created"]
                }
                for record in result
            ]

    # ============================================
    # 4. DEPENDENCY GRAPHS
    # ============================================

    def create_component(
        self,
        name: str,
        component_type: str = "Component",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a technical component node (Feature, Service, Database, etc)."""
        with self.driver.session() as session:
            if metadata:
                result = session.run("""
                    MERGE (c:Component {name: $name})
                    SET c.type = $type,
                        c.created = datetime(),
                        c.metadata = $metadata
                    RETURN c.name as name, c.type as type
                """, name=name, type=component_type, metadata=metadata)
            else:
                result = session.run("""
                    MERGE (c:Component {name: $name})
                    SET c.type = $type,
                        c.created = datetime()
                    RETURN c.name as name, c.type as type
                """, name=name, type=component_type)

            record = result.single()
            return {
                "name": record["name"],
                "type": record["type"],
                "metadata": metadata
            }

    def link_component_dependency(
        self,
        component_from: str,
        component_to: str,
        dependency_type: str = "DEPENDS_ON"
    ) -> Dict[str, Any]:
        """Create a dependency between components."""
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH (c1:Component {{name: $from}})
                MATCH (c2:Component {{name: $to}})
                MERGE (c1)-[r:{dependency_type}]->(c2)
                SET r.created = datetime()
                RETURN c1.name as from, type(r) as relationship, c2.name as to
            """, **{"from": component_from, "to": component_to})

            record = result.single()
            if record:
                return {
                    "from": record["from"],
                    "relationship": record["relationship"],
                    "to": record["to"]
                }
            return {"error": "Components not found"}

    def link_memory_to_component(
        self,
        memory_id: str,
        component_name: str
    ) -> Dict[str, Any]:
        """Link a memory to a component it affects."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:Memory {id: $memory_id})
                MATCH (c:Component {name: $component})
                MERGE (m)-[r:AFFECTS]->(c)
                SET r.created = datetime()
                RETURN m.id as memory_id, c.name as component
            """, memory_id=memory_id, component=component_name)

            record = result.single()
            if record:
                return {
                    "memory_id": record["memory_id"],
                    "affects": record["component"]
                }
            return {"error": "Memory or component not found"}

    def get_impact_analysis(self, component_name: str) -> Dict[str, Any]:
        """Analyze what would be impacted if a component changes."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Component {name: $component})

                // Find dependent components
                MATCH (dependent:Component)-[:DEPENDS_ON*]->(c)
                WITH c, collect(DISTINCT dependent.name) as dependent_components

                // Find memories affecting this component
                MATCH (m:Memory)-[:AFFECTS]->(c)
                WITH c, dependent_components, collect(DISTINCT {id: m.id, text: m.text}) as affecting_memories

                // Find memories affecting dependent components
                MATCH (dependent_mem:Memory)-[:AFFECTS]->(dep:Component)
                WHERE dep.name IN dependent_components

                RETURN c.name as component,
                       dependent_components,
                       affecting_memories,
                       collect(DISTINCT {id: dependent_mem.id, text: dependent_mem.text, affects: dep.name}) as cascade_impact
            """, component=component_name)

            record = result.single()
            if record:
                return {
                    "component": record["component"],
                    "dependent_components": record["dependent_components"],
                    "affecting_memories": record["affecting_memories"],
                    "cascade_impact": record["cascade_impact"],
                    "impact_score": len(record["dependent_components"]) + len(record["cascade_impact"])
                }
            return {"error": "Component not found"}

    # ============================================
    # 5. DECISION GRAPHS
    # ============================================

    def create_decision(
        self,
        text: str,
        user_id: str,
        pros: Optional[List[str]] = None,
        cons: Optional[List[str]] = None,
        alternatives: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a decision node with pros, cons, and alternatives."""
        decision_id = f"decision_{datetime.now().timestamp()}"

        with self.driver.session() as session:
            # Create decision node (metadata only set if provided)
            if metadata:
                session.run("""
                    CREATE (d:Decision {
                        id: $id,
                        text: $text,
                        user_id: $user_id,
                        created: datetime(),
                        metadata: $metadata
                    })
                """, id=decision_id, text=text, user_id=user_id, metadata=metadata)
            else:
                session.run("""
                    CREATE (d:Decision {
                        id: $id,
                        text: $text,
                        user_id: $user_id,
                        created: datetime()
                    })
                """, id=decision_id, text=text, user_id=user_id)

            # Add pros
            for i, pro in enumerate(pros or []):
                session.run("""
                    MATCH (d:Decision {id: $id})
                    CREATE (arg:Argument {
                        type: 'PRO',
                        text: $text,
                        order: $order
                    })
                    CREATE (d)-[:BASED_ON]->(arg)
                """, id=decision_id, text=pro, order=i)

            # Add cons
            for i, con in enumerate(cons or []):
                session.run("""
                    MATCH (d:Decision {id: $id})
                    CREATE (arg:Argument {
                        type: 'CON',
                        text: $text,
                        order: $order
                    })
                    CREATE (d)-[:CONSIDERED]->(arg)
                """, id=decision_id, text=con, order=i)

            # Link alternatives
            for alt in alternatives or []:
                session.run("""
                    MATCH (d:Decision {id: $id})
                    MERGE (alt:Decision {text: $alt_text})
                    ON CREATE SET alt.id = $alt_id,
                                  alt.created = datetime(),
                                  alt.chosen = false
                    CREATE (d)-[:CHOSEN_OVER]->(alt)
                """, id=decision_id, alt_text=alt, alt_id=f"alt_{datetime.now().timestamp()}_{alt[:10]}")

            return {
                "decision_id": decision_id,
                "text": text,
                "pros": pros or [],
                "cons": cons or [],
                "alternatives": alternatives or []
            }

    def get_decision_rationale(self, decision_id: str) -> Dict[str, Any]:
        """Get the complete rationale for a decision."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (d:Decision {id: $id})
                OPTIONAL MATCH (d)-[:BASED_ON]->(pro:Argument {type: 'PRO'})
                OPTIONAL MATCH (d)-[:CONSIDERED]->(con:Argument {type: 'CON'})
                OPTIONAL MATCH (d)-[:CHOSEN_OVER]->(alt:Decision)

                RETURN d.text as decision,
                       d.created as created,
                       d.metadata as metadata,
                       collect(DISTINCT pro.text) as pros,
                       collect(DISTINCT con.text) as cons,
                       collect(DISTINCT alt.text) as alternatives_considered
            """, id=decision_id)

            record = result.single()
            if record:
                return {
                    "decision": record["decision"],
                    "created": record["created"],
                    "metadata": record["metadata"],
                    "pros": [p for p in record["pros"] if p],
                    "cons": [c for c in record["cons"] if c],
                    "alternatives_considered": [a for a in record["alternatives_considered"] if a]
                }
            return {"error": "Decision not found"}

    # ============================================
    # 6. MEMORY CLUSTERING & DISCOVERY
    # ============================================

    def detect_memory_communities(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Detect clusters of related memories (topics/themes)."""
        with self.driver.session() as session:
            # Use Label Propagation algorithm for community detection
            result = session.run("""
                MATCH (m:Memory {user_id: $user_id})
                OPTIONAL MATCH (m)-[r:RELATES_TO|EXTENDS|RESPONDS_TO]-(other:Memory {user_id: $user_id})
                WITH m, count(r) as connections
                WHERE connections > 0
                RETURN m.id as memory_id,
                       m.text as text,
                       m.topic as topic,
                       connections
                ORDER BY connections DESC
            """, user_id=user_id)

            # Group by topic
            communities = {}
            for record in result:
                topic = record["topic"] or "uncategorized"
                if topic not in communities:
                    communities[topic] = []
                communities[topic].append({
                    "memory_id": record["memory_id"],
                    "text": record["text"],
                    "connections": record["connections"]
                })

            return communities

    # ============================================
    # 7. MEMORY QUALITY & TRUST SCORES
    # ============================================

    def calculate_trust_score(self, memory_id: str) -> Dict[str, Any]:
        """Calculate trust score based on validations, citations, and age."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:Memory {id: $id})
                OPTIONAL MATCH (m)<-[:VALIDATES]-(v:Validation {result: 'confirmed'})
                OPTIONAL MATCH (other:Memory)-[:CITES]->(m)

                RETURN m.id as memory_id,
                       m.created as created,
                       count(DISTINCT v) as validations,
                       count(DISTINCT other) as citations,
                       m.trust_score as current_score
            """, id=memory_id)

            record = result.single()
            if record:
                # Calculate score: validations * 2 + citations + recency_factor
                validations = record["validations"] or 0
                citations = record["citations"] or 0

                # Recency factor (newer memories get slight boost)
                age_days = (datetime.now() - record["created"]).days if record["created"] else 365
                recency_factor = max(0, 10 - (age_days / 30))  # Decay over time

                trust_score = (validations * 2) + citations + recency_factor

                # Update the score in DB
                session.run("""
                    MATCH (m:Memory {id: $id})
                    SET m.trust_score = $score
                """, id=memory_id, score=trust_score)

                return {
                    "memory_id": memory_id,
                    "trust_score": trust_score,
                    "factors": {
                        "validations": validations,
                        "citations": citations,
                        "recency_factor": round(recency_factor, 2),
                        "age_days": age_days
                    }
                }
            return {"error": "Memory not found"}

    # ============================================
    # 8. COMPREHENSIVE MEMORY INTELLIGENCE ANALYSIS
    # ============================================

    def analyze_memory_intelligence(self, user_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive intelligence report about user's memory graph.
        This is the GAME-CHANGER feature that combines everything.
        """
        with self.driver.session() as session:
            # Get basic stats
            stats_result = session.run("""
                MATCH (m:Memory {user_id: $user_id})
                OPTIONAL MATCH (m)-[r]-()
                WITH m, count(r) as relationships
                RETURN count(m) as total_memories,
                       avg(relationships) as avg_connections,
                       sum(CASE WHEN relationships = 0 THEN 1 ELSE 0 END) as isolated_memories
            """, user_id=user_id)
            stats = stats_result.single()

            # Find obsolete memories
            obsolete_count = session.run("""
                MATCH (:Memory {user_id: $user_id})-[:SUPERSEDES]->(old:Memory)
                RETURN count(DISTINCT old) as count
            """, user_id=user_id).single()["count"]

            # Find conflicting memories
            conflicts_result = session.run("""
                MATCH (m1:Memory {user_id: $user_id})-[:CONFLICTS_WITH]-(m2:Memory)
                RETURN m1.topic as topic, count(*) as conflicts
                ORDER BY conflicts DESC
                LIMIT 5
            """, user_id=user_id)
            conflicting_topics = [{"topic": r["topic"], "count": r["conflicts"]} for r in conflicts_result]

            # Detect communities
            communities = self.detect_memory_communities(user_id)

            # Find high-value memories (most connected)
            central_memories_result = session.run("""
                MATCH (m:Memory {user_id: $user_id})
                OPTIONAL MATCH (m)-[r]-()
                WITH m, count(r) as connections
                WHERE connections > 0
                RETURN m.id as memory_id, m.text as text, connections
                ORDER BY connections DESC
                LIMIT 10
            """, user_id=user_id)
            central_memories = [dict(r) for r in central_memories_result]

            # Calculate overall health score
            total = stats["total_memories"] or 1
            connectivity_score = (stats["avg_connections"] or 0) * 10
            isolation_penalty = (stats["isolated_memories"] or 0) / total * 100
            obsolete_penalty = obsolete_count / total * 50 if obsolete_count else 0

            health_score = max(0, min(10, connectivity_score - isolation_penalty - obsolete_penalty))

            return {
                "summary": {
                    "total_memories": stats["total_memories"],
                    "avg_connections": round(stats["avg_connections"] or 0, 2),
                    "isolated_memories": stats["isolated_memories"],
                    "obsolete_memories": obsolete_count,
                    "knowledge_health_score": round(health_score, 1)
                },
                "insights": {
                    "conflicting_knowledge": conflicting_topics,
                    "knowledge_clusters": {k: len(v) for k, v in communities.items()},
                    "central_memories": central_memories
                },
                "recommendations": self._generate_recommendations(
                    stats["isolated_memories"],
                    obsolete_count,
                    len(conflicting_topics),
                    health_score
                )
            }

    def _generate_recommendations(
        self,
        isolated: int,
        obsolete: int,
        conflicts: int,
        health_score: float
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        if isolated and isolated > 5:
            recommendations.append(f"Link {isolated} isolated memories to related knowledge for better context")

        if obsolete and obsolete > 3:
            recommendations.append(f"Archive or update {obsolete} obsolete memories")

        if conflicts and conflicts > 0:
            recommendations.append(f"Resolve {conflicts} conflicting topics to maintain knowledge consistency")

        if health_score < 5:
            recommendations.append("Knowledge graph health is low - consider adding more connections between related memories")

        if not recommendations:
            recommendations.append("Memory graph is healthy! Continue building interconnected knowledge")

        return recommendations
