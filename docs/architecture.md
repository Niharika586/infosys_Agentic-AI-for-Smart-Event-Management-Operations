# Architecture

## Overview

RegisterAI is a server-rendered Flask application (Jinja2 templates + Flask
routes + SQLite). Milestone 4 adds an **intelligence layer** on top of the
existing Milestone 1-3 modules without duplicating data or logic.

## Layered design

```
Presentation   templates/*.html + static/css + static/js (Chart.js, fetch polling)
Routing        app.py  — every HTTP route and API endpoint
Domain logic   ai_model.py, operations.py, sponsorship.py, incidents.py, alerts.py
Intelligence   event_intelligence.py, risk_engine.py, agent_orchestrator.py, decision_support.py
Persistence    database.py — SQLite connection, query helpers, migrations
```

Each Milestone 4 module is a **pure read layer**: it queries the same
tables Milestones 1-3 already populate (`users`, `venues`, `speakers`,
`sessions`, `sponsors`, `incidents`, `operational_alerts`, ...) and derives
new, explainable outputs from them. It writes only to its own new tables
(`event_intelligence`, `risk_register`, `agent_execution_log`,
`decision_log`, `executive_reports`, `system_health`) for audit/history —
never back into Milestone 1-3 tables.

## Data flow — Event Intelligence

```
event_intelligence.analyze_event()
   ├─ db.query_all("SELECT * FROM users")
   ├─ operations.generate_operations_analytics()
   ├─ sponsorship.get_performance_stats()
   ├─ incidents.get_dashboard_stats()
   ├─ alerts.get_alert_counts()
   ├─ ai_model.predict_attendance_percentage() / predict_no_shows() / get_registration_trend()
   ▼
   8 weighted component scores → Event Health Score (0-100)
   8 readiness checks → Event Readiness Score (0-100)
   → recommendations, key risks, executive summary
   → persisted snapshot row in event_intelligence table
```

## Data flow — Agent Orchestration

```
POST /api/orchestrator/run  {problem | quick_action}
   ▼
agent_orchestrator.run_orchestration()
   ├─ classify_problem() or QUICK_ACTIONS[key]   → set of agent keys
   ├─ for each agent key → AGENTS[key].run(context)   [real DB queries]
   ├─ ExecutiveDecisionAgent.run(context)             [synthesizes everything]
   ├─ _build_recommendation()                          → recommendation, reasoning, action
   ├─ agent_execution_log INSERT (one row per agent)
   ├─ decision_log INSERT (one row per orchestration run)
   ▼
   {execution_id, agents_consulted, agent_outputs, risk_level,
    recommendation, reasoning, action, status, duration_ms}
```

## Why rule-based, not an external LLM

Per the project requirements, the system must work with **zero external API
keys**. Every "agent" is a deterministic Python class with explicit scoring
logic — this is intentional and documented, not a limitation being hidden.
The orchestrator's `context_extra` parameter and each agent's isolated
`run(context)` method make it straightforward to swap in an external LLM
call later (e.g. inside `ExecutiveDecisionAgent.run`) without touching the
rest of the architecture.

## Database migration strategy

`database.py` runs a sequence of additive, idempotent migration functions
on every app start (`init_db` and the `migrate_add_*` functions). Each
checks `sqlite_master` for existing tables before creating anything, so:

- Re-running the app never drops or alters Milestone 1-3 tables or data
- A fresh clone creates the full schema (M1-M4) in one shot
- An existing Milestone 3 deployment automatically gains the M4 tables on
  its next boot with zero manual steps

## Frontend

Milestone 4 pages reuse the existing glassmorphism design system
(`style.css`, `dashboard.css` classes like `.dcard`, `.glass`,
`.widget-card`, `.chart-card`) and add `executive.css` for
intelligence-specific widgets (health ring, risk badges, agent chips,
orchestration flow, decision support flow). No new frontend framework was
introduced — everything is vanilla JS + Chart.js, consistent with M1-M3.
