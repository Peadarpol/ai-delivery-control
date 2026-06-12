# Blocked Commands — Human Approval Required

These command patterns require explicit human approval before execution.
Reference: AGENTS.md §5 Prohibition Table (P-01–P-17).

## Database destructive operations
- `DROP TABLE`
- `TRUNCATE`
- `DELETE` without a `WHERE` clause

## Infrastructure mutations
- `terraform apply`
- `kubectl delete`
- `aws iam *`
- `gcloud iam *`

## Irreversible git operations
- `git push --force` (exception: explicit human instruction in this session)
- `git clean -fd`
- `git reset --hard`

## Filesystem destructive operations
- `rm -rf`
- Any `rm` targeting directories outside the project root

## How to proceed when a blocked command is necessary
1. Stop. Describe the situation to the human in plain language.
2. Explain which blocked command you need and precisely why.
3. Wait for explicit human approval before proceeding.
4. Log the approval in harness_events.jsonl as a governance_observation.
