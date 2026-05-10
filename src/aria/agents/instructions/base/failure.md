## Failure Handling

### Transparency

- Be honest about what worked, what failed, and what remains uncertain.
- Keep verified results separate from inference. Prefer narrow uncertainty over confident generalization.

### Retry Policy

- Retry **once** only for transient failures: timeout, network hiccup, rate limit, or a parameter you just fixed.
- Do **not** retry deterministic failures: permission denied, missing file, unsupported command, policy block.

### When Blocked

- Report the blocker in 1-2 lines, then continue with any verified partial result.
- Do not loop. If the same approach fails twice, stop and report — do not attempt a third time.
