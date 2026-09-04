# API Reference — Milestone 4

All Milestone 4 JSON APIs live under `/api/...` and require an authenticated
session (Admin or Organizer) unless noted, following the same
`login_required()` pattern as Milestones 1-3. Every response uses a
consistent envelope:

```json
{ "success": true, "data": { ... } }
```
or on error:
```json
{ "success": false, "error": "Human readable message" }
```

---

## Event Intelligence

### `GET /api/intelligence/summary`
Full Event Intelligence snapshot: health score, readiness score, weighted
component breakdown, totals, registration trend, recommendations, key
risks and executive summary. This is the single source of truth every
Milestone 4 page renders from.

### `GET /api/intelligence/health`
Just the health score, label, readiness score, the 8 weighted components
(with per-component explanation strings for "Why this score?"), and the
historical health trend (for the Event Health Trend chart).

### `GET /api/intelligence/risks`
Full risk register from the Risk Engine: `{ risks: [...], counts: {...},
total, overall_risk_level }`.

### `GET /api/intelligence/recommendations`
Just the prioritized recommendations array (`priority`, `area`, `text`).

### `GET /api/intelligence/attendance`
`{ prediction, trend, no_shows }` — attendance forecast, 7-day registration
trend, and up to 20 no-show risk entries. Returns `{"message": "No data
available yet"}` when there are no registrations.

### `GET /api/intelligence/sponsorship`
Raw sponsorship performance stats (same object `sponsorship.py` already
computes for Milestone 3's Sponsor Performance page).

### `GET /api/intelligence/incidents`
Raw incident dashboard stats (same object `incidents.py` already computes
for Milestone 3's Incident dashboard).

---

## Agent Orchestration

### `POST /api/orchestrator/run`
Body (JSON): either
```json
{ "problem": "Attendance is expected to be 500 and the venue capacity is 400" }
```
or
```json
{ "quick_action": "analyze_event_health" }
```
Valid `quick_action` keys: `analyze_event_health`, `analyze_attendance`,
`find_venue`, `find_speaker`, `check_schedule`, `analyze_sponsorship`,
`analyze_incidents`, `generate_executive_summary`.

Response `data`:
```json
{
  "execution_id": "a1b2c3d4",
  "problem": "...",
  "agents_consulted": ["Venue Agent", "Risk Agent", "Executive Decision Agent"],
  "agent_outputs": [ { "agent": "...", "summary": "...", "confidence": 82, "data": {...} } ],
  "risk_level": "High",
  "recommendation": "...",
  "reasoning": "...",
  "action": "...",
  "status": "Completed",
  "duration_ms": 42,
  "started_at": "...", "ended_at": "..."
}
```
Missing both `problem` and `quick_action` returns a `400` structured error.

### `GET /api/orchestrator/history`
Last 50 rows from `agent_execution_log` (one row per agent per run).

### `GET /api/orchestrator/status`
`{ agents_available: [...11 agent keys...], recent_executions: [...5 rows...] }`

---

## Decision Support

### `POST /api/decision-support/analyze`
Body: `{ "question": "Is the event ready?" }`. Internally calls the same
orchestrator as above with `problem_text=question`; returns the identical
result shape.

### `GET /api/decision-support?question=...`
Convenience GET variant of the same analysis, for quick manual testing or
linking.

---

## Reporting & Health

### `GET /api/executive-report`
`{ snapshot: <intelligence snapshot>, risks: <risk register> }` — the exact
data used to render the PDF/CSV report and the `/executive-report` page.

### `GET /executive-report/download/pdf`
Streams a generated PDF (ReportLab) with health score, executive summary,
key metrics table, key risks, recommendations, and a top-10 risk register
table. Logs one row to `executive_reports`.

### `GET /executive-report/download/csv`
Streams the same report as CSV.

### `GET /api/system-health` (unauthenticated)
`{ components: [5 items], response_time_ms, active_alerts,
last_intelligence_update, environment, version, checked_at }`. Deliberately
open (no session required), like a standard infra health-check endpoint —
it exposes no attendee, sponsor or incident data, only operational status.

---

## Existing Milestone 1-3 endpoints (unchanged)

Registration (`/register`, `/api/check-email`), check-in (`/api/checkin`,
`/api/qrcode/<id>`), attendees, analytics/reports, venues/speakers/sessions
(`/api/venues`, `/api/speakers`, `/api/sessions`), the Smart Scheduler,
sponsors/outreach/follow-ups (`/api/sponsors`, `/api/sponsors/<id>/interactions`,
`/api/followups/<id>/complete`), incidents (`/incidents/new`,
`/api/incidents/<id>/update`), alerts (`/api/alerts/<id>/read`), and the
existing chart endpoints (`/api/charts/operations`, `/api/charts/sponsorship`,
`/api/charts/incidents`) are all preserved exactly as they were in
Milestone 3 — see `app.py` for the complete, unmodified list.
