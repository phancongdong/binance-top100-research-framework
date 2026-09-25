# Offline operations and service example

The synthetic worker validates its step count, retry budget and duration before starting. It writes each completed health record to an atomic local JSON checkpoint; a failed or interrupted step stays incomplete and can be retried on the next invocation. Failures are injected only by local tests. `demo` runs three bounded steps, binds the worker-state checksum into a summary, and completes the local goal after checking the summary. `verify` rechecks goal evidence, worker sequence and summary binding. Atomic replacement limits partial-file damage from a process interruption, but the example has no concurrent-writer coordination or durable directory-fsync guarantee.

The [sample unit](../deploy/workflow-demo.service) is an **illustration**, not an installed service. It invokes only `operations_demo demo`; it does not connect to any host or make deployment changes. A human operator adapting it to a separate, authorized environment would:

1. Review the exact source, Python version, permissions, local output location and a dedicated unprivileged service identity. Replace example paths and names deliberately.
2. Run unit tests and `demo`/`verify` in an isolated local directory. Check expected output labels and repeat-run byte stability.
3. Copy the reviewed code and unit through an independently approved change process. Inspect the rendered unit and output access before enabling it. Commands such as `systemctl daemon-reload`, `systemctl start workflow-demo` and `systemctl status workflow-demo` are **operator examples only**, not commands run by this repository.
4. Save the exact revision, checklist outcome, operator, service state, observed local output and unresolved blockers in the handover. Never infer external health from this synthetic output.

For a failed example run, inspect the local checkpoint and error, leave the failed step incomplete, correct the local problem, then rerun the same output path. If a production adaptation fails, the operator decides whether to stop the unit, restore the last reviewed code/unit, and preserve the existing output for diagnosis; the sample does not perform rollback or touch another machine. Report incident time, affected example revision, observed state, blocker, responsible owner and next action. Do not edit JSON to force `DONE_VERIFIED` or call `verify` on altered evidence as if it were independent attestation.

Handover example: “Weekly sample status summary, owner delivery lead; the synthetic checkpoint completed three steps; local SHA-256 evidence verified; blocker none; next action human review of the report and any environment-specific deployment plan.” This documents a delivery/BAU pattern, not a real service run.
