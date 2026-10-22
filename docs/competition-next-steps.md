# Prioritized next steps

1. **Review the patch and branch setup.** Confirm the remote main SHA, apply only to
   `phase-2-competition` based on `competition-2026`, and review the bundle comparison.
   Obtain explicit publication approval before pushing development code or opening a
   review PR. Any Phase 2 PR must target `competition-2026`; do not merge/deploy it.
2. **Run hosted CI and live/browser verification.** The new workflow is configured
   for Python 3.11/3.12 but has not run on GitHub. Rehearse in an isolated local browser,
   including upload/download transport. With separately authorized existing Sandbox
   credentials, verify OAuth, $1 order creation, lookup, error behavior and redaction.
   Keep the current deployment and Devpost submission unchanged.
3. **Validate against independent labels.** Obtain an authorized, appropriately
   de-identified labeled evaluation dataset. Record source/label methodology, class
   balance, limitations and subgroup performance. Do not tune on the holdout set or
   describe synthetic metrics as real fraud accuracy. Establish acceptable error
   tradeoffs before proposing scoring changes.
4. **Specify safe persistence.** Decide authenticated users/tenants, retention and
   deletion, backups, storage encryption, durable hosting and audit trust requirements.
   Add storage only after these requirements are approved; a local database would not
   solve authenticated audit history or ephemeral hosting.
5. **Finalize competition assets separately.** Rehearse the proposed judge script,
   collect verified screenshots and results, then request explicit approval for any
   new Devpost text/video, published competition update, deployment or merge.
