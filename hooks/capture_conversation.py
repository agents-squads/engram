#!/usr/bin/env python3
"""
Conversation Capture Hook for Claude Code

Captures user messages and assistant responses, sends to mem0 for extraction.
Runs async to avoid blocking Claude Code.
"""
import json
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path

MEM0_API_URL = os.environ.get("MEM0_API_URL", "http://localhost:8000")
USER_ID = os.environ.get("MEM0_USER_ID", "jorge@agents-squads.com")
HOOKS_DIR = Path(__file__).parent

def read_hook_input():
    """Read JSON input from stdin."""
    try:
        return json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        return {}

def get_last_assistant_response(transcript_path: str) -> dict:
    """Extract the last assistant response from transcript."""
    if not transcript_path or not Path(transcript_path).exists():
        return None

    last_assistant = None
    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get('type') == 'assistant':
                        last_assistant = entry
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        sys.stderr.write(f"Error reading transcript: {e}\n")
        return None

    return last_assistant

def extract_thinking_conclusions(assistant_response: dict) -> dict:
    """Extract conclusions from assistant's thinking blocks."""
    if not assistant_response:
        return {"response": "", "thinking_conclusions": ""}

    message = assistant_response.get('message', {})
    content = message.get('content', [])

    conclusions = []
    text_content = []

    for block in content:
        if isinstance(block, dict):
            if block.get('type') == 'thinking':
                thinking_text = block.get('thinking', '')
                paragraphs = thinking_text.strip().split('\n\n')
                if paragraphs:
                    conclusions.append(paragraphs[-1])
            elif block.get('type') == 'text':
                text_content.append(block.get('text', ''))
        elif isinstance(block, str):
            text_content.append(block)

    return {
        'response': '\n'.join(text_content),
        'thinking_conclusions': '\n'.join(conclusions)
    }

def store_memory_async(content: str, metadata: dict):
    """Fire and forget - store memory in background process."""
    if not content or len(content.strip()) < 10:
        return

    # Create a background script to do the actual API call
    payload = json.dumps({
        "messages": [{"role": "user", "content": content}],
        "user_id": USER_ID,
        "metadata": metadata
    })

    # Use curl in background - won't block
    cmd = f'''curl -s -X POST "{MEM0_API_URL}/memories" \
        -H "Content-Type: application/json" \
        -d '{payload}' \
        > /dev/null 2>&1 &'''

    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sys.stderr.write(f"[mem0] Queued memory for storage\n")

def handle_user_prompt(hook_input: dict):
    """Handle UserPromptSubmit hook - capture user message."""
    prompt = hook_input.get('prompt', '')
    if not prompt or len(prompt) < 5:
        return

    store_memory_async(
        content=f"User said: {prompt}",
        metadata={
            "type": "user_message",
            "session_id": hook_input.get('session_id', ''),
            "timestamp": datetime.now().isoformat(),
            "source": "hook:UserPromptSubmit"
        }
    )

def handle_stop(hook_input: dict):
    """Handle Stop hook - capture assistant response."""
    transcript_path = hook_input.get('transcript_path', '')

    assistant_response = get_last_assistant_response(transcript_path)
    if not assistant_response:
        return

    extracted = extract_thinking_conclusions(assistant_response)

    # Store the main response (truncated to key content)
    if extracted['response'] and len(extracted['response']) > 50:
        # Only store substantial responses
        store_memory_async(
            content=f"Claude responded: {extracted['response'][:2000]}",
            metadata={
                "type": "assistant_response",
                "session_id": hook_input.get('session_id', ''),
                "timestamp": datetime.now().isoformat(),
                "source": "hook:Stop"
            }
        )

    # Store thinking conclusions separately (high value)
    if extracted['thinking_conclusions'] and len(extracted['thinking_conclusions']) > 30:
        store_memory_async(
            content=f"Claude's reasoning: {extracted['thinking_conclusions'][:1500]}",
            metadata={
                "type": "thinking_conclusion",
                "session_id": hook_input.get('session_id', ''),
                "timestamp": datetime.now().isoformat(),
                "source": "hook:Stop",
                "importance": "high"
            }
        )

def main():
    hook_input = read_hook_input()
    hook_event = hook_input.get('hook_event_name', '')

    if hook_event == 'UserPromptSubmit':
        handle_user_prompt(hook_input)
    elif hook_event in ('Stop', 'SubagentStop'):
        handle_stop(hook_input)

    # Exit 0 = success, don't block
    sys.exit(0)

if __name__ == '__main__':
    main()
