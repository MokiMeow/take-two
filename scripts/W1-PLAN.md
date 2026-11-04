# W1 implementation plan

The supplied README, architecture, flow, agent, Switch and UI docs are the approved design.
Only the W1 writable paths are used; Switch stays read-only; no git commands.

1. Check Docker and record permission/startup blockers immediately. Attempt Console fallback.
2. Write the six UI State fixtures and film YAML, validating against typed contract models.
3. Implement and test typed constraints/checker, including all FLOW feasibility and unknown cases.
4. Implement and test Switch identity, durable connection, operation, question and upload contracts from source.
5. Implement SQLite transactions, inbox/outcome dedupe, persistent revisions, jobs/questions/outbox.
6. Implement serialized changes, sequential delegation, checked decisions, safe release and acknowledgments.
7. Wire API, bounded rendering and process startup. Verify state, SSE and traversal protection.
8. Attempt real-server smoke if runtime access becomes available; report measured evidence and missing user setup.

Review focus: stale approval while rendering; unauthorized answer; duplicate outcome after restart;
unknown permissions or travel; ambiguous remote send after timeout.

Verification: uv run pytest; fixture validation; local API smoke; real Switch health and five-minute
connection only if Docker/Console can be reached. No simulated integration counts as real runtime proof.
