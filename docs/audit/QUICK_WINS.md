# Quick wins

Audit date: 29 October 2026. **Recommendations only; none implemented.** These are narrow, reviewable changes with strong value. Some are high-impact security fixes, so “small” does not mean “skip regression checks.”

See [docs/audit/ISSUE_REGISTER.md](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docs/audit/ISSUE_REGISTER.md) for evidence and [docs/audit/DEVELOPMENT_ROADMAP.md](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docs/audit/DEVELOPMENT_ROADMAP.md) for dependencies. No migration, seed or reset should run on an unknown database.

| Order | Improvement | Issue IDs / location | Relative effort | Dependency / caution | Verify |
|---:|---|---|---|---|---|
| 1 | Remove password-free account switcher from real-data runtime | AUD-001; [auth.py:110](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:110) | Small | Retain a tested ordinary login/recovery path | Employee cannot switch to admin without real authentication |
| 2 | Remove login credential autofill and retire demo defaults | AUD-002; [auth.py:54](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/auth.py:54) | Small code change; Medium controlled rotation | Provision the first real admin before account changes; do not delete historical actors | No credentials offered anonymously; bundled passwords fail; real admin can recover |
| 3 | Prefill interview status/notes from selected record | AUD-017; [app.py:525](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:525) | Small | Key drafts by record and refresh after selection; add a preservation fixture | No-change save leaves notes/status unchanged |
| 4 | Escape all dynamic values in raw HTML panels | AUD-020; [app.py:212](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:212), [app.py:497](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:497) | Small | Keep trusted wrapper HTML separate from content; retain escaped diff helper | HTML payload displays literally in both role views/history |
| 5 | Enable CORS protection and verify deployment origins | AUD-021; [.streamlit/config.toml:10](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/.streamlit/config.toml:10) | Small | Match actual proxy/origin/host; retain XSRF | Expected origin/upload works, hostile origin fails |
| 6 | Show missing information and draft status truthfully | AUD-032; [docx_parser.py:181](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:181), [docx_parser.py:294](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/docx_parser.py:294) | Small | Do not allocate identifiers or invent safety content in presentation code | No draft carries an approved headline; missing hazards remain unknown |
| 7 | Normalize observed legacy status labels through one compatibility map | AUD-019; [app.py:745](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:745) | Small for compatibility reads | Preserve legacy data; canonical migration comes later | Existing Accepted state displays accepted; counts/filters agree |
| 8 | Add explicit empty/unassigned/missing-card states | AUD-018; [app.py:545](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:545) | Small | Never fall back to an arbitrary first card; keep assignment policy explicit | Empty/stale assignment fixtures render guidance without exception |
| 9 | Reject unsupported/missing targets and already-finalized decisions | AUD-006/009; [database.py:497](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:497) | Small initial guard | Full conflict/concurrency fix still requires one atomic conditional transaction | No-op target or replay never writes a new acceptance event |
| 10 | Display imported meeting time | AUD-034; [app.py:513](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:513) | Small | Format missing values honestly | Synthetic time appears; blank is explicitly unspecified |
| 11 | Use JD IDs as selector values, with disambiguated labels | AUD-013; [app.py:357](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:357), [app.py:561](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/app.py:561) | Small | Does not itself solve duplicate imports | Two same-label JDs are both selectable |
| 12 | Start a synthetic regression suite with reproduced defects | AUD-025; [database.py:493](D:/hazem/projects/3S%20Security%20-%20job_describation%20-%202027/database.py:493) | Small first slice; Medium full baseline | Use in-memory DBs and supported runtimes, never live startup/seed | First tests reproduce replay, stale update and cross-target behavior, then pass after fixes |

## Changes that should not be disguised as quick wins

Password hashing/identity migration, revision-bound approval, actor-ID backfill, domain constraints, complete history reconstruction and durable backup/restore require planning and rehearsal. They are essential but cannot be safely reduced to a blind one-line patch.

Enabling foreign keys is simple at connection creation, but first check existing data and missing relationships. The present declared-FK check is clean; that does not validate undeclared actor/assignment relations or every future migration.

Adding indexes is likely straightforward, but the measured catalog query is already 0.705 ms median at current volume. Correctness and exposure take priority. Cache only after document revision invalidation is sound.

## Recommended first reviewable increment

Create the synthetic security/integrity fixtures, remove the two demo access paths with a safe initial-admin plan, fix interview prefill and truthful draft/missing-field labels, and verify CORS/HTML boundaries in staging. Review each increment independently, keep the existing architecture, and preserve every current record.

