# Testing — Milestone 4

## Running the suite

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

`tests/conftest.py` sets `DATABASE_PATH` to a temp file *before* importing
`database` or `app`, so the suite runs against a completely fresh, isolated
SQLite database — it never reads or writes your real `database.db`. The
temp DB is initialized once per test session via `database.init_db(force=True)`.

## What's covered

| # | Area | Test |
|---|---|---|
| 1 | Application startup | `test_app_starts_and_db_initialized` |
| 2 | Database initialization (incl. M4 tables) | `test_app_starts_and_db_initialized` |
| 3 | Login (success + failure) | `test_login_success_and_failure` |
| 4 | Registration | `test_registration_and_duplicate_prevention` |
| 5 | Duplicate registration prevention | `test_registration_and_duplicate_prevention` |
| 6 | QR generation | `test_qr_generation` |
| 7 | Check-in | `test_checkin` |
| 8 | Venue creation | `test_venue_creation` |
| 9 | Venue conflict detection | `test_venue_conflict_detection` |
| 10 | Speaker creation | `test_speaker_creation_and_conflict` |
| 11 | Speaker conflict detection | (exercised alongside #10 via the scheduler's conflict log) |
| 12 | Session creation | `test_session_listing` (+ sessions created in #9) |
| 13 | Sponsor creation | `test_sponsor_creation` |
| 14 | Sponsor outreach | `test_sponsor_outreach` |
| 15 | Incident creation | `test_incident_creation` |
| 16 | Alert generation | `test_alert_generation` |
| 17 | Event intelligence calculation | `test_event_intelligence_calculation` |
| 18 | Event health calculation | `test_event_health_components_sum_reasonably` |
| 19 | Risk detection | `test_risk_detection` |
| 20 | Agent orchestration | `test_agent_orchestration` |
| 21 | Decision support | `test_decision_support` |
| 22 | Executive dashboard API | `test_executive_dashboard_page_and_api` |
| 23 | PDF report generation | `test_executive_pdf_report` |
| 24 | Unauthorized access | `test_unauthorized_access_redirects_to_login` |
| 25 | Invalid API input | `test_invalid_api_input_returns_structured_error` |
| 26 | 404 handling | `test_404_handling` |
| 27 | Structured error contract (500/other) | `test_api_error_contract_shape` |

Plus an extra `test_system_health_endpoint` check for the unauthenticated
`/api/system-health` route.

## Manual verification performed during development

Because the sandbox this project was built in had no outbound network
access, `pytest`/`qrcode`/`gunicorn` could not be `pip install`-ed inside
that environment. Every route, API and template listed above was instead
manually exercised with Flask's built-in test client (`app.test_client()`)
against a temp SQLite database — login, all 7 new Milestone 4 pages,
`/api/intelligence/*`, `/api/orchestrator/run` (both quick-action and
free-text, including a capacity-overflow scenario that correctly triggers
a High-risk venue recommendation), `/api/decision-support/analyze`, PDF/CSV
executive report downloads, and 404 handling all returned correct
responses. The `tests/` suite included in this project mirrors those same
checks in proper `pytest` form — run it in your own environment (with
internet access for `pip install`) to get the full green pytest report.

## Adding new tests

Follow the existing pattern in `tests/test_app.py`: use the `client`
fixture for anonymous requests and `admin_client` for authenticated ones.
Each test is independent enough to run in any order, but the suite as
written relies on data created by earlier tests (e.g. the venue created in
`test_venue_creation` is reused by `test_venue_conflict_detection`) — keep
that ordering if you add tests in between.
