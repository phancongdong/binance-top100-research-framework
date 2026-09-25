# Local goal tracking example

The `operations_demo` CLI keeps one active goal in `active-goal.json` and a separate goal record under `goals/`. Each record has a goal ID, objective, state, owner, blocker, next action and SHA-256 evidence references. The human owner decides the objective, reviews evidence and owns the handover. This is an offline example, not a shared task system.

| Current | Allowed next | Required condition |
| --- | --- | --- |
| PENDING | IN_PROGRESS | Named next action |
| IN_PROGRESS | BLOCKED | Blocker and next action |
| BLOCKED | IN_PROGRESS | Recovery next action |
| IN_PROGRESS | DONE_VERIFIED | At least one existing, matching local evidence file |

Other transitions fail. A new goal cannot replace a PENDING, IN_PROGRESS or BLOCKED active goal. Repeated `demo` against a completed output verifies it without rewriting files. A paused or blocked local goal keeps its ID and saved worker progress. The sample [goal template](../examples/goal-template.json) is illustrative; edit a copy for a separate exercise, not the bundled CLI goal.

Example delivery record: objective “prepare a weekly service handover”; owner “delivery lead”; action “check the offline status summary”; blocker “summary missing”; next action “regenerate the local synthetic summary”; evidence `evidence/worker-summary.json` with its recorded SHA-256; handover “share the verified status, outstanding blockers and next owner action.” This models BAU ownership and delivery follow-up without claiming integration with a ticket or documentation platform. The demo's `DONE_VERIFIED` checks local bytes only; it is not approval of a real deployment or externally attested evidence.

Run from the repository root:

```sh
python -B -m operations_demo demo --output operations-output
python -B -m operations_demo verify --output operations-output
python -B -m operations_demo demo --output operations-output
```

Use a new empty directory for a separate run. `verify` exits 2 for missing, altered or incomplete evidence. The output is local synthetic data; do not place private data in the output directory. One trusted local writer is assumed. There is no file lock, cross-process transaction, hostile-writer protection, signature, access control or remote authority. Keep independent backups and human review for any real process.
