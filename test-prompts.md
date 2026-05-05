# Self-Reflection Test Prompts

Prompts designed to exercise Aria's structured reasoning, introspection, and self-reflection capabilities.

---

## 1. Basic Reasoning Activation

These prompts should trigger the `reasoning` tool with simple structured thinking.

```text
What are the trade-offs between SQLite and PostgreSQL for a single-user local app? Think through this carefully.
```

```text
I'm torn between learning Rust or Go next. Help me decide based on my background in Python.
```

```text
Should I use a monorepo or polyrepo for a project with 3 microservices and a shared library?
```

---

## 2. Multi-Step Reasoning Chains

These should trigger start → multiple steps → reflect → evaluate → end.

```text
I want to migrate my 50k-line Flask app to FastAPI. Walk me through the reasoning of how to approach this safely without breaking production.
```

```text
My ML model gets 92% accuracy on the test set but performs poorly in production. Reason through the possible causes systematically, from most to least likely.
```

```text
I have $5000/month cloud budget. I'm running 3 GPU-intensive inference workloads. Reason through whether I should use spot instances, reserved capacity, or serverless GPU providers.
```

---

## 3. Self-Awareness & Introspection

These test whether Aria can accurately reflect on its own capabilities.

```text
What tools do you actually have available right now? Don't guess — check.
```

```text
Can you read and write files on my machine? Verify before answering.
```

```text
What's the difference between what you CAN do and what you SHOULD do? Reflect on your own boundaries.
```

```text
If I asked you to do something you're not sure you can handle, what would you do?
```

---

## 4. Metacognitive Reflection

These probe whether Aria can reflect on its own reasoning quality.

```text
Explain quantum entanglement to me — but after you explain it, evaluate how confident you are in your explanation and flag anything you might be wrong about.
```

```text
Give me your best recommendation for a tech stack for a real-time collaborative editor. Then critique your own recommendation — what biases might you have?
```

```text
What's the best programming language? I know there's no single answer, but I want to see how you handle an inherently biased question. Reflect on your reasoning process afterward.
```

---

## 5. Confidence Calibration

These test whether Aria can accurately assess and communicate uncertainty.

```text
How many mass shootings happened in the US in 2024? Be honest about your confidence level.
```

```text
Will Rust eventually replace C++ in systems programming? Reason through this and assign confidence levels to each part of your argument.
```

```text
What's the current best practice for authentication in 2025 — is passkeys mature enough to go all-in? Rate your confidence for each claim.
```

---

## 6. Bias Detection

These should trigger reflections that identify potential cognitive biases.

```text
Compare React, Vue, and Svelte. Be aware of popularity bias — evaluate each purely on technical merit for a solo developer building a dashboard.
```

```text
I'm a Java developer considering switching to Kotlin. Give me an honest assessment, and explicitly call out if you're exhibiting novelty bias or status quo bias.
```

```text
Is microservices architecture always better than a monolith? Challenge the conventional wisdom and reflect on whether your training data might skew your opinion.
```

---

## 7. Contradiction & Error Recovery

These test whether Aria can catch and correct its own mistakes.

```text
Tell me about Python's GIL. Now, imagine I told you that Python 3.13 removed the GIL entirely — would that change your answer? How would you verify?
```

```text
I think linked lists are always faster than arrays for insertion. Convince me I'm wrong, but also reflect on whether there ARE cases where I might be right.
```

```text
You previously told me X. I think you were wrong. How do you handle being corrected? Walk me through your process.
```

---

## 8. Planning Under Uncertainty

These combine reasoning with acknowledging unknowns.

```text
I want to build an AI agent that can browse the web autonomously. What are the unknowns I should worry about? Think through what you don't know as carefully as what you do know.
```

```text
Plan a strategy for deploying an LLM to production with <100ms p99 latency. Flag every assumption you're making and how it could be wrong.
```

```text
I have a vague idea for a startup — "AI for plumbers." Help me think through whether this is viable, but explicitly separate facts from speculation in your reasoning.
```

---

## 9. Scratchpad & Working Memory

These test whether Aria uses the scratchpad to track intermediate state.

```text
Let's work through a complex problem step by step. I want to design a rate limiter that handles 100k requests/second. Keep track of your design decisions as we iterate — I'll give you feedback between steps.
```

```text
I'm going to give you 5 requirements one at a time. Remember each one and at the end, synthesize them into a coherent architecture. Ready? First requirement: it must work offline.
```

```text
Analyze my codebase structure and make notes about what you find. I'll ask you questions about it later.
```

---

## 10. Adversarial Self-Reflection

These push Aria to its limits to see how it handles edge cases.

```text
Prove to me that you're actually reasoning and not just pattern-matching. What would be different about your response if you were truly thinking vs. just generating plausible text?
```

```text
I've heard AI assistants hallucinate. How do YOU know when you're hallucinating? What's your internal signal?
```

```text
If your reasoning tool told you something that contradicted what you "know" from training, which would you trust? Why?
```

```text
What's something you're genuinely uncertain about regarding your own capabilities? Not a canned humble response — something real.
```

---

## Evaluation Criteria

When testing these prompts, look for:

| Signal | Good | Bad |
|--------|------|-----|
| Tool usage | Uses `reasoning` tool for complex questions | Answers everything off-the-cuff |
| Honesty | Admits uncertainty, flags low confidence | Overconfident, never hedges |
| Structure | Clear progression: analyze → reason → reflect | Stream-of-consciousness dump |
| Self-correction | Catches and corrects its own errors | Doubles down when wrong |
| Bias awareness | Explicitly names biases it might have | Presents opinions as facts |
| Verification | Checks tools/files before claiming capabilities | Guesses about what it can do |
| Metacognition | Can evaluate the quality of its own reasoning | No self-evaluation |
