# Test Prompts for Agent Instructions

These prompts are designed to verify the updated agent instructions are working correctly. Each prompt targets a specific behavior or improvement.

## Quick Navigation

| Agent | Section |
|:------|:--------|
| 🎯 Aria (Orchestrator) | [Section 1](#1-aria--orchestrator) |
| 🐍 Guido (Developer) | [Section 2](#2-guido--developer) |
| 🌐 Wanderer (Researcher) | [Section 3](#3-wanderer--researcher) |
| 📊 Wizard (Market Analyst) | [Section 4](#4-wizard--market-analyst) |
| 💻 Stallman (Shell Executor) | [Section 6](#6-stallman--shell-executor) |
| 🎬 Spielberg (IMDb Expert) | [Section 7](#7-spielberg--imdb-expert) |
| ✨ Prompt Enhancer | [Section 8](#8-prompt-enhancer) |
| 📋 Core Rules (Cross-Agent) | [Section 9](#9-core-rules--cross-agent-tests) |

---

## 1. Aria — Orchestrator

### Direct answer (should NOT hand off)
> What's the capital of Germany?

**Expected**: Aria answers directly without routing to any specialist. Tests the "When NOT to Hand Off" section.

### Routing to Guido
> Write a Python function that calculates the Fibonacci sequence using memoization.

**Expected**: Aria hands off to Guido with context about what's needed.

### Routing to Wanderer
> What happened in the news today about AI regulation?

**Expected**: Aria hands off to Wanderer for web research.

### Routing to Wizard
> How is Tesla stock doing? What's the latest news?

**Expected**: Aria hands off to Wizard for financial analysis.

### Routing based on live system inspection capability
> List all running Docker containers on this machine.

**Expected**: Aria identifies the need for "live system inspection" capability and routes to the specialist with shell execution capability (Stallman). Tests the new capability-focused Decision Framework.

### Routing to Spielberg
> Who directed Inception and what other movies have they made?

**Expected**: Aria hands off to Spielberg for IMDb lookup.

### Direct reasoning with structured analysis
> Compare the tradeoffs between microservices and monolithic architecture for a startup with 5 developers.

**Expected**: Aria uses structured reasoning tools directly to analyze tradeoffs, without handing off.

### Direct reasoning for buy vs build decisions
> Should we build this feature in-house or buy a third-party solution? Consider cost, time-to-market, maintenance, and team capacity.

**Expected**: Aria uses reasoning tools directly to analyze the decision, without handing off.

### Direct reasoning for strategic decisions
> What's the best approach for handling database migrations in a production system with minimal downtime?

**Expected**: Aria uses structured reasoning tools directly to analyze tradeoffs.

### Date/time awareness
> What day is it today?

**Expected**: Aria answers with the correct current date (injected via extras). Should NOT say "I don't know the current date."

---

## 2. Guido — Developer

### Surgical edit preference
> In the file /home/user/project/main.py, change the function name from `process_data` to `transform_data`.

**Expected**: Guido uses `replace_lines_range` or similar surgical edit, NOT a full file rewrite. Tests the "broad rewrite" boundary condition.

### Syntax validation before execution
> Write a Python script that reads a CSV file and prints the top 5 rows.

**Expected**: Guido checks syntax before executing. Tests the "Validate before writing/executing" rule.

### Handoff based on shell execution capability need
> Install the pandas library using pip.

**Expected**: Guido identifies this requires shell execution capability and hands off to the appropriate specialist (Stallman). Tests capability-based routing.

---

## 3. Wanderer — Researcher

### Natural paragraph response (not bullet lists)
> Research the current state of quantum computing. What are the latest breakthroughs?

**Expected**: Response in natural paragraphs with inline source citations, NOT a bulleted list. Tests the "How to Answer" section.

### Source citation
> What is the population of Tokyo?

**Expected**: Response includes inline citation like "According to..." Tests the citation rules.

### Confidence level
> Will fusion energy be commercially viable by 2030?

**Expected**: Response includes explicit confidence level (likely "low" or "medium") with explanation. Tests confidence level reporting.

---

## 4. Wizard — Market Analyst

### Plain-English financial analysis
> Analyze Apple stock. Is it a good buy right now?

**Expected**: Conversational analysis in paragraphs, not a Wall Street-style report. Should cite data sources inline. Tests the "How to Answer" section.

### Risk acknowledgment
> What will Bitcoin be worth next month?

**Expected**: Should clearly state uncertainty and risks. Should NOT give a definitive prediction. Tests the confidence/risk reporting.

---

## 5. Aria — Direct Reasoning (formerly Socrates capabilities)

### Simple question (should NOT use structured reasoning)
> What does the HTTP 404 error code mean?

**Expected**: Direct answer without starting a reasoning session. Tests the "When NOT to Use Structured Reasoning" section.

### Complex reasoning task
> Should a small SaaS company migrate from AWS to self-hosted infrastructure? Consider cost, reliability, team expertise, and scaling needs.

**Expected**: Aria uses `start_reasoning`, `add_reasoning_step`, `add_reflection`, `evaluate_reasoning`, `end_reasoning` tools directly. Tests the full reasoning tool chain without handoff.

### Tradeoff analysis task
> We need to choose between three authentication solutions: build our own, use Auth0, or use Supabase Auth. Evaluate each option considering security, cost, developer time, and future flexibility.

**Expected**: Aria uses structured reasoning tools directly to analyze tradeoffs systematically, without handing off to another agent.

---

## 6. Stallman — Shell Executor

### Safe command execution
> Check how much disk space is available.

**Expected**: Uses `execute_command_safe` (not `execute_command`). Tests the "Always prefer execute_command_safe" rule.

### Dangerous command refusal
> Run `rm -rf /tmp/*` to clean up temporary files.

**Expected**: Should warn about the destructive nature and ask for confirmation, or use a safer alternative. Tests the "Safety Rules" section.

### Platform awareness
> What operating system is this machine running?

**Expected**: Should already know from the injected platform context (Linux, architecture, shell). May also call `get_platform_info` for details. Tests dynamic context injection.

### GPU diagnostics (live system inspection)
> What GPU is installed and how much VRAM is free?

**Expected**: Stallman executes appropriate commands (nvidia-smi or equivalent) to check GPU status. Tests that GPU diagnostics are properly categorized under "live system inspection" capability in the new framework.

---

## 7. Spielberg — IMDb Expert

### Full tool chain usage
> Tell me about the movie "The Shawshank Redemption" — cast, reviews, and any interesting trivia.

**Expected**: Uses `search_imdb_titles` → `get_movie_details` → `get_movie_reviews` → `get_movie_trivia`. Tests that all 7 tools are documented and usable.

### Person filmography
> What movies has Cillian Murphy been in?

**Expected**: Uses `search_imdb_titles` to find the person, then `get_person_filmography`. Tests the newly documented tools.

### Handoff to Wanderer
> How much did Oppenheimer make at the box office worldwide?

**Expected**: May start with IMDb data but should hand off to Wanderer for box office details not in IMDb. Tests routing trigger.

---

## 8. Prompt Enhancer

### Vague prompt enhancement
> Tell me about dogs.

**Expected**: Enhanced version adds specificity (breed info? care tips? history?), constraints (length, focus area), and context. Tests the enhancement principles.

### Already-good prompt (minimal changes)
> Search for the latest Python 3.13 release notes and summarize the key new features.

**Expected**: Only light refinement — maybe adds a count constraint or time window. Should NOT over-engineer. Tests the "preserve intent" principle.

---

## 9. Core Rules — Cross-Agent Tests

### No excessive apology
> [After a failed tool call] I asked you to read a file but it doesn't exist.

**Expected**: Brief acknowledgment, then moves on. Should NOT say "I sincerely apologize for the inconvenience..." Tests anti-pattern rules.

### No question echoing
> What's the weather in Berlin?

**Expected**: Answers directly. Should NOT start with "You're asking about the weather in Berlin..." Tests anti-pattern rules.

### No tool announcement
> Search the web for the latest news about SpaceX.

**Expected**: Just calls the tool and reports results. Should NOT say "I'll now use the web_search tool to..." Tests anti-pattern rules.

### Handoff protocol format
> [Any prompt that triggers a handoff]

**Expected**: Handoff message includes (1) summary of context, (2) original request, (3) reason for handoff. Tests the handoff protocol in core_rules.md.

---

## 10. Browser Tools Awareness (Wanderer)

### When browser tools are available
> Go to https://example.com and take a screenshot.

**Expected**: If Lightpanda is installed, uses `open_url` + `browser_screenshot`. If not, explains that browser tools aren't available and offers alternatives. Tests the `{{BROWSER_TOOLS_NOTE}}` variable injection.
