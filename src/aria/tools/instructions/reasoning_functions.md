# Reasoning Tools (`aria.tools.reasoning.functions`)

This file documents the tools implemented in [`aria.tools.reasoning.functions`](src/aria2/tools/reasoning/functions.py:1).

## Critical Workflow

IMPORTANT: You MUST start reasoning BEFORE using any other reasoning tools.

### Session Management Pattern
```
1. start_reasoning("intent", "agent_id")  ← ALWAYS FIRST
.
.
.
N. end_reasoning("intent", "agent_id")    ← When complete
```

**All reasoning tools automatically use the active session - NO session_id parameter needed!**

## Session Management

### `start_reasoning(intent: str, agent_id: str)`
**When to use:** Start of any complex reasoning task (REQUIRED FIRST)
**Purpose:** Initialize a new reasoning session with automatic management
**Example:** `start_reasoning("Begin cost-benefit analysis", "agent_id")`
**Note:** Creates and activates a session. All tools will use this session automatically.

### `end_reasoning(intent: str, agent_id: str)`
**When to use:** When your analysis is complete
**Purpose:** Clean up the active reasoning session
**Example:** `end_reasoning("Analysis complete", "agent_id")`

### `list_reasoning_sessions(intent: str, agent_id: str)`
**When to use:** Debug or check active sessions
**Returns:** List of all sessions for this agent
**Example:** Useful for debugging session state

### `reset_reasoning(intent: str, agent_id: str)`
**When to use:** Clear active session for fresh start
**Purpose:** Reset all steps, reflections, and scratchpad while keeping session active
**Example:** Restarting analysis with new approach

## Reasoning Documentation

### `add_reasoning_step(intent: str, content: str, agent_id: str, cognitive_mode="analysis", reasoning_type="deductive", evidence=None, confidence=0.65)`
**When to use:** Document each logical step in your reasoning
**Parameters:**
- `content`: Description of the reasoning step
- `cognitive_mode`: "analysis", "synthesis", "evaluation", "planning", "creative", or "reflection"
- `reasoning_type`: "deductive", "inductive", "abductive", "causal", "probabilistic", or "analogical"
- `confidence`: 0.0-1.0 confidence level
- `evidence`: Supporting evidence (optional)
**Example:** Track problem decomposition, hypothesis formation, conclusions
**Note:** Uses active session automatically - NO session_id needed!

### `add_reflection(intent: str, reflection: str, agent_id: str, on_step: Optional[int] = None)`
**When to use:** Self-evaluate your reasoning process
**Parameters:**
- `reflection`: Your reflection on the reasoning
- `on_step`: Optional step number this reflection refers to
**Example:** "Should verify this assumption", "Potential bias detected"
**Note:** Uses active session automatically - NO session_id needed!

## Working Memory

### `use_scratchpad(intent: str, key: str, agent_id: str, value=None, operation="get")`
**When to use:** Store temporary hypotheses, variables, or intermediate results
**Operations:**
- `"set"`: Store a key-value pair (requires `value` parameter)
- `"get"`: Retrieve value for a key
- `"list"`: Get all keys
- `"clear"`: Clear all scratchpad data (use key="all")
**Example:** Track working hypotheses, store intermediate calculations
**Note:** Uses active session automatically - NO session_id needed!

## Quality Assessment

### `evaluate_reasoning(intent: str, agent_id: str)`
**When to use:** Get quality assessment of your reasoning
**Returns:** Metrics on clarity, completeness, consistency, confidence
**Example:** Before finalizing conclusions, check reasoning quality
**Note:** Uses active session automatically - NO session_id needed!

### `get_reasoning_summary(intent: str, agent_id: str)`
**When to use:** Review complete reasoning chain
**Returns:** All steps, reflections, scratchpad, and evaluation
**Example:** Final review before presenting conclusions
**Note:** Uses active session automatically - NO session_id needed!

## Quick Start

## JSON Return Format

All reasoning tools return **JSON objects** (Python `dict`) rather than formatted strings.

## Common response envelope

On success:

```json
{
  "status": "success",
  "tool": "add_reasoning_step",
  "intent": "Record the key inference",
  "agent_id": "agent_id",
  "session_id": "agent_id_session_1737981000000",
  "timestamp": "2026-01-27T12:34:46.541Z",
  "data": { }
}
```

On error:

```json
{
  "status": "error",
  "tool": "add_reasoning_step",
  "intent": "Record the key inference",
  "agent_id": "agent_id",
  "timestamp": "2026-01-27T12:34:46.541Z",
  "error": {
    "code": "NO_ACTIVE_SESSION",
    "message": "No active reasoning session for agent 'agent_id'.",
    "how_to_fix": "Call start_reasoning(reason, agent_id) first."
  }
}
```

### Quick Start

```python
# 1. Start reasoning
start_reasoning("Begin analysis", "agent_id")

# 2. Use reasoning tools (no session_id needed!)
add_reasoning_step("Identify variables", "Problem details...", "agent_id")
add_reflection("Check for missing assumptions", "Reflection...", "agent_id")
use_scratchpad("Store intermediate", "key1", "agent_id", value="data", operation="set")
evaluate_reasoning("Check quality before concluding", "agent_id")

# 3. End reasoning
end_reasoning("Analysis complete", "agent_id")
```

**No session_id tracking required!**

## Usage Patterns

## Pattern 1: Simple analysis
```python
start_reasoning("Initialize analysis for bug investigation", "agent_id")
add_reasoning_step("Identified problem: X", "Details...", "agent_id", cognitive_mode="analysis")
add_reasoning_step("Hypothesis: Y causes X", "Reasoning...", "agent_id", 
                   reasoning_type="abductive", confidence=0.7)
add_reflection("Need to verify Y", "agent_id")
evaluate_reasoning("Check reasoning quality", "agent_id")
get_reasoning_summary("Review complete analysis", "agent_id")
end_reasoning("Bug analysis complete", "agent_id")
```

## Pattern 2: Complex problem with working memory
```python
start_reasoning("Begin debugging session", "agent_id")
use_scratchpad("error_type", "agent_id", value="NullPointerException", operation="set")
add_reasoning_step("Error occurs in module A", "Details...", "agent_id")
use_scratchpad("suspect_line", "agent_id", value="line 42", operation="set")
add_reflection("Check initialization order", "agent_id")
# ... more analysis ...
end_reasoning("Debugging complete", "agent_id")
```

## Pattern 3: Starting new analysis
```python
# First analysis
start_reasoning("Analyze frontend issue", "agent_id")
add_reasoning_step("UI issue identified", "Details...", "agent_id")
# ... analysis ...
end_reasoning("Frontend analysis complete", "agent_id")

# New analysis (replaces previous session)
start_reasoning("Analyze backend issue", "agent_id")
add_reasoning_step("API timeout detected", "Details...", "agent_id")
# ... analysis ...
end_reasoning("Backend analysis complete", "agent_id")
```

## Best Practices

1. **Always start reasoning first:** Call `start_reasoning()` before using any reasoning tools
2. **Use specific intents:** Make each reason unique and descriptive
3. **Document incrementally:** Add steps as you reason, not all at once
4. **Reflect regularly:** Use `add_reflection` to catch biases and errors
5. **Track confidence:** Include confidence levels for uncertain conclusions
6. **Use scratchpad:** Store working hypotheses and intermediate results
7. **Evaluate before concluding:** Run `evaluate_reasoning` before final answers
8. **End when done:** Call `end_reasoning()` to clean up when analysis is complete

## Common Errors

### "No active reasoning session"
**Cause:** Trying to use reasoning tools without starting a session
**Fix:** Call `start_reasoning("your reason", "agent_id")` first

### Example Error Message:
```
ValueError: No active reasoning session for agent 'agent_id'.
Start reasoning first:
  start_reasoning('Describe your reasoning goal', 'agent_id')
```

## Migration from Old API

If you see old code with `session_id` parameters, update it:

**Old (deprecated):**
```python
create_reasoning_session("intent", "my_session", "agent_id")
add_reasoning_step("intent", "content", "agent_id", session_id="my_session")
delete_reasoning_session("intent", "my_session", "agent_id")
```

**New (current):**
```python
start_reasoning("intent", "agent_id")
add_reasoning_step("intent", "content", "agent_id")  # No session_id!
end_reasoning("intent", "agent_id")
```
