# Enterprise candidate validation

Tested source commit `0de5fe67bb72840cf76270a5bc71fbfb7d22c127`. Base commit `2506773`. Execution was local, with synthetic inputs and no hosted CI run.

| Check | Observed result |
| --- | --- |
| Python 3.11, locked dependencies, full unittest discovery | 152 passed, zero skipped, including real PostgreSQL 16 row-level security tests with a non-owner role. |
| Auth0 API SDK | Offline OIDC discovery and local RSA-signed JWTs exercised through FastAPI. Invalid audience, issuer, expiry and organization denied. |
| Concurrent evidence upload | Twelve submissions from four workers returned the same receipt. PostgreSQL stored one preservation event. |
| Risk policy | 216 synthetic combinations covered currency, amount boundaries and missing indicator states. No labeled fraud dataset was used. |
| Database recovery | Restored a custom-format pg_dump to a separate database. Counted 100 evidence rows, verified a sampled original file byte-for-byte and checked its custody events as the runtime role. |
| Synthetic timing | 100 serial case-and-evidence commits in a local database, p95 5.7 ms. Covers database service work only. |
| Forge | Clean npm install, three Node contract tests, manifest validation with a fixture app ID, and successful browser bundles for both UI entry points. |
| Dependency advisories | pip-audit on the enterprise Python lock and npm audit on the Forge production dependency tree reported zero known findings at check time. |

## Repeat the automated checks

Install the Python lock in a clean Python 3.11 environment. For PostgreSQL tests supply a disposable database named `fraudshield_test` and the test admin/runtime URLs documented in the workflow. The PostgreSQL fixture truncates test tables. Run `python -m unittest discover -s tests -v`. In `forge/` run `npm ci --ignore-scripts`, `npm test` and `npm audit --omit=dev`.

## External acceptance

Pending: live Auth0 browser login and logout on the intended domain, Jira and Confluence install/upgrade/uninstall on a real developer site, independent security review and a buyer pilot with measured review time and labeled data. SDK and integration tests use controlled fixtures. Dependency scans cover known advisories. The commercial pilot criteria are in [PILOT.md](PILOT.md).
