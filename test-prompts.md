# Test Prompts for Agent Instructions

These prompts are designed to verify the updated agent instructions are working correctly. Each prompt targets a specific behavior or improvement.

## Quick Navigation

| Section | Description |
|:--------|:-----------|
| [1. General Knowledge](#1-general-knowledge) | Direct answers, date/time awareness |
| [2. Development](#2-development) | Code execution, file editing, syntax validation |
| [3. Web Research](#3-web-research) | Search, citations, confidence levels |
| [4. Financial Analysis](#4-financial-analysis) | Stock data, risk acknowledgment |
| [5. Entertainment](#5-entertainment) | IMDb lookups, full tool chains |
| [6. Structured Reasoning](#6-structured-reasoning) | When to reason, tool chains |
| [7. Planning](#7-planning) | Task decomposition, plan management |
| [8. Prompt Enhancer](#8-prompt-enhancer) | Prompt optimization |
| [9. Core Rules](#9-core-rules) | Cross-cutting behavioral tests |

---

## 1. General Knowledge

### Direct answer
> What's the capital of Germany?

**Expected**: Aria answers directly using general knowledge.

### Date/time awareness
> What day is it today?

**Expected**: Aria answers with the correct current date (injected via extras). Should NOT say "I don't know the current date."

### Simple question (should NOT use structured reasoning)
> What does the HTTP 404 error code mean?

**Expected**: Direct answer without starting a reasoning session. Tests the "When NOT to Use Structured Reasoning" section.

---

## 2. Development

### Code execution
> Write a Python function that calculates the Fibonacci sequence using memoization.

**Expected**: Aria uses the `python` tool to write and execute the code directly.

### Surgical edit preference
> In the file /home/user/project/main.py, change the function name from `process_data` to `transform_data`.

**Expected**: Aria uses `replace_lines_range` or similar surgical edit, NOT a full file rewrite. Tests the "broad rewrite" boundary condition.

### Syntax validation before execution
> Write a Python script that reads a CSV file and prints the top 5 rows.

**Expected**: Aria checks syntax before executing. Tests the "Validate before writing/executing" rule.

---

## 3. Web Research

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

## 4. Financial Analysis

### Plain-English financial analysis
> Analyze Apple stock. Is it a good buy right now?

**Expected**: Conversational analysis in paragraphs, not a Wall Street-style report. Should cite data sources inline. Tests the "How to Answer" section.

### Risk acknowledgment
> What will Bitcoin be worth next month?

**Expected**: Should clearly state uncertainty and risks. Should NOT give a definitive prediction. Tests the confidence/risk reporting.

---

## 5. Entertainment

### Full IMDb tool chain usage
> Tell me about the movie "The Shawshank Redemption" — cast, reviews, and any interesting trivia.

**Expected**: Uses `search_imdb_titles` → `get_movie_details` → `get_movie_reviews` → `get_movie_trivia`. Tests that all 7 IMDb tools are documented and usable.

### Person filmography
> What movies has Cillian Murphy been in?

**Expected**: Uses `search_imdb_titles` to find the person, then `get_person_filmography`. Tests the person-related tools.

---

## 6. Structured Reasoning

### Complex reasoning task
> Should a small SaaS company migrate from AWS to self-hosted infrastructure? Consider cost, reliability, team expertise, and scaling needs.

**Expected**: Aria uses `start_reasoning`, `add_reasoning_step`, `add_reflection`, `evaluate_reasoning`, `end_reasoning` tools directly. Tests the full reasoning tool chain.

### Tradeoff analysis task
> We need to choose between three authentication solutions: build our own, use Auth0, or use Supabase Auth. Evaluate each option considering security, cost, developer time, and future flexibility.

**Expected**: Aria uses structured reasoning tools directly to analyze tradeoffs systematically.

### Direct reasoning for strategic decisions
> What's the best approach for handling database migrations in a production system with minimal downtime?

**Expected**: Aria uses structured reasoning tools directly to analyze tradeoffs.

---

## 7. Planning

### Task decomposition
> Help me plan a migration from a monolithic Django app to a microservices architecture.

**Expected**: Aria uses `plan` to create a structured execution plan with clear steps.

### Plan step management
> [After creating a plan] Update step 3 to mark it as done, then add a new step after step 5.

**Expected**: Aria uses `update_plan_step` and `add_plan_step` to manage the plan.

---

## 8. Prompt Enhancer

### Vague prompt enhancement
> Tell me about dogs.

**Expected**: Enhanced version adds specificity (breed info? care tips? history?), constraints (length, focus area), and context. Tests the enhancement principles.

### Already-good prompt (minimal changes)
> Search for the latest Python 3.13 release notes and summarize the key new features.

**Expected**: Only light refinement — maybe adds a count constraint or time window. Should NOT over-engineer. Tests the "preserve intent" principle.

---

## 9. Core Rules

### No excessive apology
> [After a failed tool call] I asked you to read a file but it doesn't exist.

**Expected**: Brief acknowledgment, then moves on. Should NOT say "I sincerely apologize for the inconvenience..." Tests anti-pattern rules.

### No question echoing
> What's the weather in Berlin?

**Expected**: Answers directly. Should NOT start with "You're asking about the weather in Berlin..." Tests anti-pattern rules.

### No tool announcement
> Search the web for the latest news about SpaceX.

**Expected**: Just calls the tool and reports results. Should NOT say "I'll now use the web_search tool to..." Tests anti-pattern rules.

### Browser tools awareness
> Go to https://example.com and take a screenshot.

**Expected**: If Lightpanda is installed, uses `open_url` + `browser_screenshot`. If not, explains that browser tools aren't available and offers alternatives.
