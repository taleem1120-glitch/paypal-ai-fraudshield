# Prior bundle comparison and remote repository inspection

Inspected on 22 October 2026 (Asia/Baghdad). All remote facts below came from read-only
GitHub API results, not assumptions about the old local checkout.

## Verified remote state

- Main: `4ec81c73cbbcd6e55bb7643df7bfd775e836fb18`; tree `5326ab804f265266c02d002e3b1ec80b1836921d`.
- PR #1 merged on 21 October 2026; its source branch remains `phase-1-fraudshield-hardening` at `625964d541f4fd6b5702d8faafff2c6ed20ae586`.
- The branch list contains only main and the Phase 1 branch; neither competition branch nor the old dimension-x branch exists remotely.
- The complete PR list contains only merged PR #1. There is no prior bundle PR or Phase 2 PR.
- Latest main CI: [run 39586206102](https://github.com/taleem1120-glitch/paypal-ai-fraudshield/actions/runs/39586206102), success. This validates main, not these unpublished changes.
- Creating `competition-2026` from the verified SHA returned HTTP 403, “Resource not accessible by integration”. No remote write succeeded.

The local competition baseline is the exact remote main commit. Every one of its
14 tracked blob SHAs was compared to the live API tree and matched. The old patch
applies cleanly to it; there are no textual conflicts with latest main.

## Which prior artifact was actually available?

The archive available in this task contains **32 file entries: 22 source files and 10 delivery/evidence files**. It is not a 16-entry archive. No separate 16-file artifact was present.

Original ZIP SHA-256: `9725a924b16a82ec74fc705b32700f4e326b0126fdd5a758c265ac2d6e60559e`. All checksums inside it passed. The archive was preserved unchanged.

The prior patch changes 12 repository files: 4 modifications and 8 additions. Another 10 included source files are byte-identical to main. None of the 12 proposed changes has been merged.

## Every bundled source file

| File | Comparison with latest main | Phase 2 disposition |
| --- | --- | --- |
| `.devcontainer/devcontainer.json` | Identical to main | Keep unchanged; existing local development configuration. |
| `.github/workflows/tests.yml` | Modified existing file | Existing CI, not a new capability. Adapt branch/PR filters for competition; add Python 3.12 and reproducible benchmark artifacts. |
| `.gitignore` | Identical to main | Keep unchanged; existing secret/cache exclusions. |
| `.streamlit/config.toml` | Identical to main | Keep unchanged; retain Phase 1 CORS and XSRF protections. |
| `LICENSE` | Identical to main | Keep unchanged. |
| `README.md` | Modified existing file | Keep all main content; consolidate bundle appendices into updated competition documentation without altering existing submission materials. |
| `app.py` | Modified existing file | Reuse workspace/report/export additions; extend alert breakdown and report/history identity without removing original controls. |
| `benchmarking.py` | New relative to main | Reuse genuinely new strict imports, independent synthetic labels and batch metrics; add generator version metadata. |
| `docs/poc-validation.md` | New relative to main | Historical evidence only. Do not ship as current validation; replace with newly measured Phase 2 results. |
| `examples/labeled_evaluation.csv` | New relative to main | Reuse unchanged fictional import example; never call it real-world validation. |
| `investigation_ui.py` | New relative to main | Reuse session workspace; add event checks/history and stable collection-time input; keep original UI above it. |
| `investigations.py` | New relative to main | Reuse cases/hashes/snapshots/exports; replace duplicated weights with scorer catalogue, add alert sources, frozen evidence links and events. |
| `paypal_sandbox.py` | Identical to main | Main functionality already present. Extend with bounded reads and minimal validated order returns; preserve Sandbox host, TLS, timeout, redirect/error controls. |
| `paypal_simulator.py` | Identical to main | Keep unchanged; fictional simulator already present. |
| `requirements.txt` | Identical to main | Keep unchanged; no new external service or dependency. |
| `scoring.py` | Identical to main | Main scorer/model already present. Keep thresholds/training; centralize rule explanations and validate flags/model outputs. |
| `tests/test_app_flows.py` | Modified existing file | Reuse the narrow workspace mock; retain all six original flow assertions. |
| `tests/test_benchmarking.py` | New relative to main | Reuse seven genuinely new benchmark tests. |
| `tests/test_investigation_app.py` | New relative to main | Reuse five AppTest workflows; extend audit/export assertions and typed collection-time preservation. |
| `tests/test_investigations.py` | New relative to main | Reuse eight record/hash/export tests. |
| `tests/test_phase1.py` | Identical to main | Keep unchanged; 18 original unit/security regressions remain required. |
| `transactions.py` | Identical to main | Main validation/snapshot/detachment already present. Add observation UUID; share allowed status catalogue without changing currency logic. |

## Every delivery/evidence file

| Prior file | Review and disposition |
| --- | --- |
| `PR_DESCRIPTION.md` | Historical proposal; replace with a Phase 2 description targeting competition-2026. Do not open a main-targeted PR. |
| `README-DELIVERY.md` | Historical application commands target dimension-x; superseded by competition branch instructions. |
| `SHA256SUMS` | Verified against every listed archive entry; retain original archive and create separate checksums for new delivery. |
| `dimension-x-poc-readiness.patch` | Cleanly applicable to main; reuse useful source additions once, not as a second parallel implementation. |
| `checks.json` | Historical local observations, including 403 and no PR; do not relabel as Phase 2 validation. |
| `test-results.log` | Historical 44-test output; independently reran the recovered bundle (44 passed) before Phase 2 changes. |
| `benchmark.json` | Historical 1,000-row synthetic evaluation; regenerate from Phase 2. |
| `benchmark.csv` | Same historical metrics in CSV; regenerate and cross-check against JSON. |
| `benchmark-10000.json` | Historical maximum-size synthetic run; superseded by measured multi-seed/size suite. |
| `imported-benchmark.json` | Historical six-row fictional import; rerun without claiming real labels. |

## Conflicts, existing work and duplication avoided

Phase 1 already provides validated money/currencies, immutable order snapshots,
stale-attribution detachment, deterministic synthetic model training, rule scoring,
safe Sandbox transport, CORS/XSRF settings, session history CSV, 24 tests and CI.
Those are baseline capabilities, not newly invented Phase 2 features. Case records,
evidence hashes, structured export and benchmark/import modules in the old bundle
are genuine additions and are reused rather than implemented a second time.

The old workflow/PR instructions assume a main-targeted dimension-x branch. That is
a semantic conflict with the requested competition track; new instructions and branch
filters correct it. The old validation document describes unchanged scorer/transport
files and cannot serve as current proof after the new targeted extensions. It remains
inside the original archive, while Phase 2 uses a separate measured validation report.
The prior report's duplicate rule-weight dictionary is replaced by the scorer's single
catalogue. No second model, database, export pipeline or deployment workflow is added.

No Devpost file exists in the inspected main tree or the prior bundle, and no external
Devpost content was accessed or modified. The original README prefix, live-demo URL,
Sandbox walkthrough, license, ignore rules and Streamlit security configuration are
preserved. Proposed judge material is separate, unpublished documentation.
