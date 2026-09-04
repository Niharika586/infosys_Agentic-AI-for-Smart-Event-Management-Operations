# AI Agents — Milestone 4

Every agent is a small, deterministic Python class in `agent_orchestrator.py`
with a single `run(context) -> dict` method. None call an external LLM or
API — this is documented intentionally per the project's Rule 10/11 (the
architecture is designed so an external LLM call could later be dropped
into `ExecutiveDecisionAgent.run`, or any other agent, without touching the
orchestrator itself).

Each agent returns:
```json
{ "agent": "Venue Agent", "summary": "...", "confidence": 82, "data": {...} }
```

---

## 1. Registration Intelligence Agent
- **Purpose**: Summarize registration volume, categories and demographic mix.
- **Input**: all rows from `users`.
- **Logic**: reuses `ai_model.generate_organizer_insights()` from Milestone 1.
- **Output**: total registrations + top participant category.
- **Confidence**: 90 if ≥15 registrations, else 60; 0 with no data.

## 2. Attendance Prediction Agent
- **Purpose**: Forecast expected attendance % and flag no-show risk.
- **Input**: all rows from `users`.
- **Logic**: `ai_model.predict_attendance_percentage()` + `predict_no_shows()`.
- **Output**: predicted attendance %, count of High-risk no-shows.
- **Confidence**: the predicted attendance percentage itself.

## 3. Venue Agent
- **Purpose**: Recommend the best venue for a session/requirement.
- **Input**: `venue_requirements` (attendees, facilities, date/time) from
  context, or the attendee count parsed from free-text problems.
- **Logic**: `operations.recommend_venues()` — the same scoring engine
  Milestone 2's Venue Agent page already uses (capacity, facilities,
  availability, conflict-free).
- **Output**: best-scoring qualified venue, or the closest disqualified
  option with the specific reasons it failed (e.g. under maintenance,
  insufficient capacity).
- **Confidence**: the venue's match score (0-100), or 20 if none qualify.

## 4. Speaker Agent
- **Purpose**: Recommend the best speaker for a session.
- **Input**: `speaker_requirements` (topic, session type, date/time).
- **Logic**: `operations.recommend_speakers()` (expertise match, preferred
  session type, availability, conflict-free).
- **Output**: best-scoring qualified speaker.
- **Confidence**: the speaker's match score.

## 5. Scheduling Agent
- **Purpose**: Surface venue/speaker scheduling conflicts and allocation gaps.
- **Input**: all sessions.
- **Logic**: `operations.generate_operations_analytics()`.
- **Output**: sessions missing a venue/speaker, historical conflicts logged.
- **Confidence**: 90 minus a penalty per unfilled session.

## 6. Sponsorship Agent
- **Purpose**: Track sponsor pipeline health, conversion, follow-ups.
- **Input**: all sponsors + interactions + follow-ups.
- **Logic**: `sponsorship.get_performance_stats()` + `get_followup_buckets()`.
- **Output**: confirmed/total, conversion rate, overdue follow-ups, amount committed.
- **Confidence**: the conversion rate.

## 7. Incident Agent
- **Purpose**: Assess open incidents, severity, overdue items.
- **Input**: all incidents.
- **Logic**: `incidents.get_dashboard_stats()`.
- **Output**: open/critical/overdue counts.
- **Confidence**: penalized per critical/overdue incident.

## 8. Alert Agent
- **Purpose**: Summarize active operational alerts by severity.
- **Input**: `operational_alerts` (unresolved).
- **Logic**: `alerts.get_alert_counts()`.
- **Output**: total/critical/high alert counts.
- **Confidence**: penalized per active alert, more so for Critical/High.

## 9. Event Intelligence Agent
- **Purpose**: Surface the overall Event Health & Readiness scores inside
  an orchestration run (without recomputing them — it reuses the snapshot
  already attached to `context`).
- **Input**: `context["intelligence_snapshot"]` (from `event_intelligence.analyze_event()`).
- **Output**: health score, label, readiness score.
- **Confidence**: the health score itself.

## 10. Risk Agent
- **Purpose**: Scan all modules for operational, scheduling, sponsorship
  and incident risks in one pass.
- **Input**: live DB state across venues, speakers, sessions, sponsors, incidents, alerts.
- **Logic**: `risk_engine.get_all_risks()` — six detector functions, each
  producing structured risk entries with severity/probability/impact/score.
- **Output**: risk counts by severity, overall risk level, top 5 risks.
- **Confidence**: inverse of overall risk level (Low→90, Critical→15).

## 11. Executive Decision Agent
- **Purpose**: Synthesize every other agent's output into one final,
  human-readable recommendation, reasoning and action — this is the
  "orchestration" step, not a separate data source.
- **Input**: the full list of prior agent outputs for this run.
- **Logic**: `_build_recommendation()` — rule-based priority chain: venue
  issues → critical incidents → overall risk level → default "on track"
  message. Reasoning is a concatenation of every consulted agent's summary.
- **Output**: `recommendation`, `reasoning`, `action` (mapped from risk level).
- **Confidence**: average confidence across all consulted agents.

---

## Problem classification (routing)

`classify_problem(text)` uses simple, documented keyword matching (e.g.
"venue"/"capacity"/"hall" → Venue Agent; "sponsor"/"funding" → Sponsorship
Agent) to decide which agents a free-text question needs. If nothing
matches, a broad default set runs (`intelligence`, `risk`, `attendance`,
`venue`, `incident`) so the orchestrator is always useful. The Executive
Decision Agent always runs last regardless of routing.

Quick actions (`QUICK_ACTIONS` dict) map a button click directly to a fixed
agent set — used by both the Agent Orchestration page and the Decision
Support Center's quick-action buttons.

## Execution logging

Every agent invocation in every run is written to `agent_execution_log`
(agent name, request text, start/end time, duration, status, result
summary, confidence, error). Every completed run's final recommendation is
written to `decision_log`. Both tables back the "Agent Activity" table on
the Agent Orchestration page and the "Recent Decisions" list.
