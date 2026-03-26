REASONING_TYPES = [
    "deductive",
    "inductive",
    "abductive",
    "causal",
    "probabilistic",
    "analogical",
]
COGNITIVE_MODES = [
    "analysis",
    "synthesis",
    "evaluation",
    "planning",
    "creative",
    "reflection",
]

BIAS_PATTERNS = {
    "confirmation_bias": [
        "confirms",
        "supports",
        "validates",
        "proves",
        "obviously",
        "clearly",
    ],
    "anchoring_bias": [
        "first",
        "initial",
        "starting",
        "baseline",
        "reference",
    ],
    "availability_heuristic": [
        "recent",
        "memorable",
        "vivid",
        "comes to mind",
        "recall",
    ],
    "overconfidence_bias": [
        "definitely",
        "certainly",
        "absolutely",
        "guaranteed",
        "impossible",
    ],
}

COGNITIVE_SCAFFOLDING = {
    "analysis": "Identify key components and relations.",
    "synthesis": "Combine pieces into a coherent view.",
    "evaluation": "Check weaknesses, gaps, and counterpoints.",
    "planning": "Outline steps, risks, and contingencies.",
    "creative": "Generate alternatives and reframes.",
    "reflection": "Surface assumptions and possible bias.",
}

COGNITIVE_MODE_TRIGGERS = {
    "planning": "Use when outlining steps, constraints, or contingencies",
    "analysis": "Use when examining evidence, data, or tool results",
    "evaluation": "Use when assessing quality, failures, or comparing options",
    "synthesis": "Use when combining findings into a conclusion",
    "creative": "Use when generating alternatives or reframing the problem",
    "reflection": "Use when checking for bias, gaps, or assumptions",
}

ERROR_PATTERNS = {
    "TOOL_NOT_FOUND": ["tool.*not found", "avail.*tool"],
    "PERMISSION_DENIED": ["permission denied", "access denied"],
    "TIMEOUT": ["timeout", "timed out", "took too long"],
    "INVALID_INPUT": ["invalid.*input", "cannot.*parse", "invalid.*argument"],
    "RATE_LIMIT": ["rate limit", "too many requests", "quota exceeded"],
    "NETWORK": ["connection.*error", "network.*error", "unreachable"],
}
