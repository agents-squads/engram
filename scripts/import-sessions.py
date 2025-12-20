#!/usr/bin/env python3
"""
Import Claude Code session history into Engram.

Reads session transcripts from ~/.claude/projects/ and sends them to Engram
for memory extraction. Processes chronologically so newer knowledge can
supersede older.

Usage:
    python3 scripts/import-sessions.py --projects "agents-squads,agents-squads/hq,claude"
    python3 scripts/import-sessions.py --dry-run  # Preview without importing
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, Dict, Any, List
import requests

# Configuration
ENGRAM_API_URL = os.environ.get("ENGRAM_API_URL", "http://localhost:8000")
USER_ID = os.environ.get("ENGRAM_USER_ID", "jorge@agents-squads.com")
CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"

# Rate limiting
DELAY_BETWEEN_REQUESTS = 2  # seconds - Ollama needs time


def parse_project_name(dir_name: str) -> str:
    """Convert directory name to readable project name."""
    return dir_name.replace("-Users-jorgevidaurre-", "").replace("-", "/")


def get_project_dirs(project_filter: List[str]) -> List[Path]:
    """Get project directories matching the filter."""
    dirs = []
    for proj_dir in PROJECTS_DIR.iterdir():
        if not proj_dir.is_dir():
            continue
        name = parse_project_name(proj_dir.name)
        # Match if any filter is a prefix of the name
        for f in project_filter:
            if name.startswith(f) or f in name:
                dirs.append(proj_dir)
                break
    return dirs


def get_sessions_chronologically(proj_dir: Path) -> Generator[Dict[str, Any], None, None]:
    """Yield sessions sorted by oldest first."""
    sessions = []

    for jsonl_file in proj_dir.glob("*.jsonl"):
        try:
            # Get first timestamp from file to sort
            first_ts = None
            messages = []

            with open(jsonl_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)

                        # Get timestamp for sorting
                        if first_ts is None and data.get("timestamp"):
                            ts = data["timestamp"]
                            if isinstance(ts, str):
                                first_ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            elif isinstance(ts, (int, float)):
                                first_ts = datetime.fromtimestamp(ts / 1000)

                        # Collect user and assistant messages
                        if data.get("type") == "user" and data.get("message"):
                            msg = data["message"]
                            if msg.get("content") and not data.get("isMeta"):
                                messages.append({
                                    "role": "user",
                                    "content": msg["content"],
                                    "timestamp": data.get("timestamp")
                                })

                        elif data.get("type") == "assistant" and data.get("message"):
                            msg = data["message"]
                            content = msg.get("content", [])
                            # Extract text content from assistant response
                            text_parts = []
                            for part in content:
                                if isinstance(part, dict) and part.get("type") == "text":
                                    text_parts.append(part.get("text", ""))
                            if text_parts:
                                messages.append({
                                    "role": "assistant",
                                    "content": "\n".join(text_parts),
                                    "timestamp": data.get("timestamp")
                                })
                    except json.JSONDecodeError:
                        continue

            if messages and first_ts:
                sessions.append({
                    "file": jsonl_file,
                    "timestamp": first_ts,
                    "messages": messages,
                    "session_id": jsonl_file.stem
                })
        except Exception as e:
            print(f"  Warning: Could not read {jsonl_file.name}: {e}")

    # Sort by timestamp (oldest first)
    sessions.sort(key=lambda s: s["timestamp"])

    for session in sessions:
        yield session


def chunk_messages(messages: List[Dict], max_chars: int = 4000) -> Generator[List[Dict], None, None]:
    """Split messages into chunks to avoid overwhelming the LLM."""
    chunk = []
    chunk_size = 0

    for msg in messages:
        msg_size = len(msg.get("content", ""))

        if chunk_size + msg_size > max_chars and chunk:
            yield chunk
            chunk = []
            chunk_size = 0

        chunk.append(msg)
        chunk_size += msg_size

    if chunk:
        yield chunk


def send_to_engram(messages: List[Dict], metadata: Dict[str, Any], dry_run: bool = False) -> bool:
    """Send messages to Engram for memory extraction."""
    payload = {
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
        "user_id": USER_ID,
        "metadata": metadata
    }

    if dry_run:
        preview = messages[0]["content"][:100] if messages else "empty"
        print(f"    [DRY RUN] Would send {len(messages)} messages: {preview}...")
        return True

    try:
        response = requests.post(
            f"{ENGRAM_API_URL}/memories",
            json=payload,
            timeout=120  # Ollama can be slow
        )

        if response.status_code == 200:
            result = response.json()
            count = len(result.get("results", []))
            return count > 0
        else:
            print(f"    Error: {response.status_code} - {response.text[:100]}")
            return False
    except Exception as e:
        print(f"    Error: {e}")
        return False


def import_project(proj_dir: Path, dry_run: bool = False, verbose: bool = False) -> Dict[str, int]:
    """Import all sessions from a project."""
    project_name = parse_project_name(proj_dir.name)
    stats = {"sessions": 0, "chunks": 0, "memories": 0, "errors": 0}

    print(f"\n📁 Importing: {project_name}")

    for session in get_sessions_chronologically(proj_dir):
        stats["sessions"] += 1
        session_date = session["timestamp"].strftime("%Y-%m-%d")

        if verbose:
            print(f"  📄 Session {session['session_id'][:8]}... ({session_date})")

        # Process in chunks
        for chunk in chunk_messages(session["messages"]):
            stats["chunks"] += 1

            metadata = {
                "source": "session_import",
                "project": project_name,
                "session_id": session["session_id"],
                "session_date": session_date,
                "imported_at": datetime.now().isoformat()
            }

            if send_to_engram(chunk, metadata, dry_run):
                stats["memories"] += 1
            else:
                stats["errors"] += 1

            if not dry_run:
                time.sleep(DELAY_BETWEEN_REQUESTS)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Import Claude Code sessions into Engram")
    parser.add_argument(
        "--projects",
        default="agents-squads,agents-squads/hq,claude",
        help="Comma-separated project names to import"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without importing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")
    parser.add_argument("--delay", type=float, default=2, help="Delay between API calls (seconds)")

    args = parser.parse_args()

    global DELAY_BETWEEN_REQUESTS
    DELAY_BETWEEN_REQUESTS = args.delay

    project_filter = [p.strip() for p in args.projects.split(",")]
    project_dirs = get_project_dirs(project_filter)

    if not project_dirs:
        print(f"No projects found matching: {project_filter}")
        print(f"Available projects:")
        for d in PROJECTS_DIR.iterdir():
            if d.is_dir():
                print(f"  - {parse_project_name(d.name)}")
        sys.exit(1)

    print("=" * 60)
    print("  Engram Session Import")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE IMPORT'}")
    print(f"API: {ENGRAM_API_URL}")
    print(f"User: {USER_ID}")
    print(f"Projects: {len(project_dirs)}")

    # Check API health
    if not args.dry_run:
        try:
            r = requests.get(f"{ENGRAM_API_URL}/health", timeout=5)
            if r.status_code != 200:
                print(f"\n❌ Engram API not healthy: {r.status_code}")
                sys.exit(1)
        except Exception as e:
            print(f"\n❌ Cannot connect to Engram: {e}")
            sys.exit(1)

    total_stats = {"sessions": 0, "chunks": 0, "memories": 0, "errors": 0}

    for proj_dir in sorted(project_dirs, key=lambda d: d.stat().st_mtime):
        stats = import_project(proj_dir, args.dry_run, args.verbose)
        for k in total_stats:
            total_stats[k] += stats[k]
        print(f"  ✓ {stats['sessions']} sessions, {stats['memories']} memory extractions")

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"Sessions processed: {total_stats['sessions']}")
    print(f"Chunks sent: {total_stats['chunks']}")
    print(f"Memory extractions: {total_stats['memories']}")
    print(f"Errors: {total_stats['errors']}")

    if args.dry_run:
        print("\n⚠️  This was a dry run. Use without --dry-run to import.")


if __name__ == "__main__":
    main()
