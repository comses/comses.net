# Agent Work Artifacts

This directory stores durable, version-controlled artifacts used to continue work across coding-agent sessions.

Template files:

- `templates/RUNBOOK.md`: stable procedures, invariants, and safety constraints.
- `templates/PLAN.md`: implementation plan and decisions.
- `templates/CHECKPOINT.md`: append-only progress log.
- `templates/HANDOFF.md`: current state for the next person or agent.

Shared command index:

- `commands.md`: minimal list of commonly used operational commands for humans and agents.

Recommended usage:

1. Copy these templates into a workstream folder (for example, `docs/agents/feature-xyz/`).
2. Keep checkpoint entries short and factual.
3. Update handoff at each stop point.
4. Link the workstream folder from the related issue or PR.
5. Do not store secrets, tokens, or credentials in these files.
