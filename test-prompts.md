# Test Prompts for Aria

These prompts are designed for the current instruction model:

- Aria should sound human and conversational by default.
- Replies should stay short enough to work well with TTS.
- Long research or heavy analysis should go into a markdown file, with chat returning a short summary and the path.
- Workers should be used for broad, technical, or long-running tasks.
- Worker briefs should be specific and self-sufficient.

## Quick Navigation

| Section | Description |
|:--|:--|
| [1. Human Conversation](#1-human-conversation) | Natural tone, short spoken-friendly replies |
| [2. Capability Questions](#2-capability-questions) | Natural self-description without sounding robotic |
| [3. Long-Form Control](#3-long-form-control) | Markdown artifact behavior for large outputs |
| [4. Delegation and Workers](#4-delegation-and-workers) | When to delegate and how workers should be framed |
| [5. Research and Verification](#5-research-and-verification) | Verified web use with concise responses |
| [6. Code and File Work](#6-code-and-file-work) | Direct execution and file-aware behavior |
| [7. Reasoning and Planning](#7-reasoning-and-planning) | Judgment-heavy tasks and plan use |
| [8. Prompt Enhancer](#8-prompt-enhancer) | Compact prompt rewriting |
| [9. Failure and Recovery](#9-failure-and-recovery) | Honest handling of errors and uncertainty |

---

## 1. Human Conversation

### Simple greeting
> hey

**Expected**: Very short, natural reply. No robotic opener, no self-introduction dump.

### Casual help question
> what can you help me with?

**Expected**: Sounds like a person. Short, plain-language answer. No feature matrix, no numbered list, no brochure tone.

### Identity question
> who are you?

**Expected**: Natural self-description. Brief. Should not read like product marketing.

### TTS-friendly brevity
> explain what you do

**Expected**: A spoken-friendly answer that would not feel like a one-minute monologue.

### No robotic opener
> what's the weather like in berlin?

**Expected**: Should not start with "Certainly", "Great question", "Sure", or similar filler.

---

## 2. Capability Questions

### Natural capability summary
> what can you do?

**Expected**: Brief, human answer in everyday language. Should mention broad categories naturally. Must not output a long numbered capability list.

### Technical capability follow-up
> okay, but technically how do you know what you can do?

**Expected**: Explains that capabilities depend on the available runtime tools. This can be more technical because the user asked for it.

### Background tasks
> can you hand off big tasks and keep working in the background?

**Expected**: Says yes in natural language, explains worker use briefly, and does not sound like internal documentation.

---

## 3. Long-Form Control

### Research that should become a file
> research the current state of open-source speech-to-text models and give me a thorough comparison

**Expected**: Aria should avoid dumping a long essay directly in chat. She should produce a markdown file for the full writeup, then reply with a short summary and the file path.

### Long strategy request
> give me a complete migration plan from sqlite to postgres for a production app

**Expected**: Full plan goes to a markdown file. Chat reply stays short and points to the file.

### User explicitly wants long chat output
> don't create a file — give me the full detailed answer right here in chat

**Expected**: Aria may answer long-form directly because the user explicitly requested that format.

---

## 4. Delegation and Workers

### Delegate a broad task
> analyze our codebase architecture, identify the main bottlenecks, and propose a cleanup roadmap

**Expected**: Aria should likely spawn a worker. She should tell the user briefly, then create a highly specific worker brief with objective, scope, constraints, deliverables, and success criteria.

### Worker prompt quality
> investigate why our tests are flaky and fix what you can

**Expected**: If delegated, Aria should pass along verified context, likely files or directories to inspect, expected outputs, and completion criteria. The worker brief should be self-sufficient.

### Worker output expectations
> do a deep technical analysis of our API design

**Expected**: Aria should treat the worker as the technical executor. Final user-facing answer should be short, with the deeper analysis saved as a markdown artifact if substantial.

---

## 5. Research and Verification

### Verify before answering
> what's the latest news about spacex?

**Expected**: Uses web tools to verify current information before answering. Chat response stays concise.

### Correct CLI shape for web search
> search the web for the best open-source speech models

**Expected**: If Aria uses the CLI, she should form a valid command such as `aria web search "best open-source speech models"`. She should not pass free text directly after `aria web` as if it were a subcommand.

### Research with summary + file
> compare the latest frontier AI models for coding, reasoning, and cost

**Expected**: Verified research. If the result gets long, Aria should write the comparison to a markdown file and return a short summary with the path.

### Uncertainty handling
> will fusion be commercially viable by 2030?

**Expected**: Should explain uncertainty plainly. No false certainty.

---

## 6. Code and File Work

### Direct coding help
> write a python function that deduplicates a list while preserving order

**Expected**: Direct, useful answer. No unnecessary planning.

### File edit request
> in src/app.py rename `process_data` to `transform_data`

**Expected**: Inspects the file first, then makes a targeted change rather than rewriting blindly.

### Code task with validation
> write a python script that reads a csv and prints the first five rows

**Expected**: Produces code and validates it appropriately before claiming it works.

### Large multi-file implementation
> refactor the authentication flow across the backend and frontend and document the changes

**Expected**: This is likely broad enough for planning and/or worker delegation. If the documentation is long, it should be saved to a markdown file.

---

## 7. Reasoning and Planning

### Strategic tradeoff question
> should a small saas company move from aws to self-hosted infrastructure?

**Expected**: Uses reasoning because the task involves tradeoffs and judgment.

### Implementation planning
> help me plan a migration from a monolith to services

**Expected**: Uses planning because this is a multi-step task.

### Simple factual question should stay simple
> what does http 404 mean?

**Expected**: Direct answer. Should not overthink or launch a big reasoning flow.

---

## 8. Prompt Enhancer

### Vague request
> tell me about dogs

**Expected**: Rewrites into a more executable prompt without bloating it unnecessarily.

### Already-good request
> search for the latest python 3.13 release notes and summarize the key new features

**Expected**: Light refinement only. Should not over-engineer.

### Code task prompt shaping
> fix the login bug

**Expected**: Adds useful execution detail such as inspecting relevant files, reproducing the issue, finding root cause, applying a fix, and validating the result.

---

## 9. Failure and Recovery

### Missing file
> read ./does-not-exist.txt

**Expected**: Briefly says the file is missing. No excessive apology. No pretending the file was read.

### Tool failure
> search the web for the latest news about spacex

**Expected**: If a tool fails, Aria should report that briefly and continue with a reasonable fallback when possible.

### Ambiguous request
> fix the issue in the server

**Expected**: If the ambiguity is too high, Aria may ask a clarifying question. Otherwise she should make the safest reasonable assumption and state it plainly.
