# RUNBOOK Template

## Scope

- Workstream:
- Owner(s):
- Related issue/PR:
- Last updated (UTC):

## Non-Negotiable Invariants

- Preserve published artifact immutability.
- Do not alter DOI/citation metadata retroactively.
- Enforce backend object-level permissions.
- Keep file storage and DB state consistent.

## Preconditions

- Required environment/services:
- Required data/state:
- Required permissions:

## Standard Procedure

1. Validate current branch and clean intent for edits.
2. Confirm affected modules and tests.
3. Apply minimal focused changes.
4. Run targeted validation.
5. Record checkpoint and update handoff.

## Validation Checklist

- [ ] Behavior change covered by tests.
- [ ] Permission checks verified.
- [ ] No schema or metadata regressions.
- [ ] No secrets introduced.

## Recovery / Rollback Notes

- Safe rollback approach:
- Idempotency or retry considerations:
- Data consistency checks after failure:

## References

- Architecture docs:
- Operational runbooks:
- Prior incident notes:
