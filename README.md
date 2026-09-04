# 🤖 RegisterAI — AI-Powered Event Management & Intelligence Platform

**Infosys Springboard Virtual Internship — Milestone 1, 2, 3 & 4**

RegisterAI is a full-stack, production-style event management platform that
has grown across four milestones into an enterprise AI-powered event
**intelligence** platform:

- **Milestone 1** — Registration & Attendee Intelligence
- **Milestone 2** — Venue & Speaker Operations
- **Milestone 3** — Sponsorship & Incident Operations
- **Milestone 4** — Event Intelligence & Enterprise Deployment (this release)

Milestone 4 does **not** replace or rebuild the previous milestones — it
**extends** them with a centralized Event Intelligence Engine, a real
multi-agent orchestration layer, a Decision Support Center, a Risk Engine,
an Executive Dashboard, production hardening, automated tests, and complete
documentation.

---

## 📚 Table of Contents

1. [Feature Overview by Milestone](#-feature-overview-by-milestone)
2. [Milestone 4 — Event Intelligence & Enterprise Deployment](#-milestone-4--event-intelligence--enterprise-deployment)
3. [Architecture](#-architecture)
4. [Technology Stack](#-technology-stack)
5. [Folder Structure](#-folder-structure)
6. [Database Schema](#-database-schema)
7. [API Endpoints](#-api-endpoints)
8. [Authentication & Security](#-authentication--security)
9. [Testing](#-testing)
10. [Performance](#-performance)
11. [Local Setup](#-local-setup)
12. [Render Deployment](#-render-deployment)
13. [Environment Variables](#-environment-variables)
14. [Mentor Demonstration Workflow](#-mentor-demonstration-workflow)
15. [Troubleshooting](#-troubleshooting)

---

## ✨ Feature Overview by Milestone

### Milestone 1 — Registration & Attendee Intelligence

| Module | Description |
|---|---|
| **Home / About** | Animated hero, live stats, feature grid, AI banner, architecture overview |
| **Registration** | Validated form (email, phone, duplicate detection), Participant Category, QR Registration ID |
| **Login** | Admin & Organizer role-based authentication |
| **Admin Dashboard** | KPI cards, bar/pie/line charts, AI insight banner |
| **Attendee Management** | Search, filter, sort, inline edit, delete, CSV/PDF export, print |
| **QR Check-In** | Camera-based QR check-in with duplicate prevention |
| **AI Analytics** | Attendance prediction, no-show risk, recommendations, trends (`ai_model.py`) |
| **Reports** | One-click PDF & CSV report generation (ReportLab) |

### Milestone 2 — Venue & Speaker Operations

| Module | Description |
|---|---|
| **Venue Management** | Search/filter/sort, conflict-checked booking, detail view with history |
| **Speaker Management** | Profiles, expertise, availability |
| **Session Management** | Create sessions linking a venue + speaker; automatic conflict validation |
| **Venue Agent** | Rule-based agent scoring venues against attendee count/facilities/date-time |
| **Speaker Agent** | Rule-based agent matching speaker expertise to session topics |
| **Smart Scheduler** | Day-by-day venue/session schedule |
| **Operations Analytics** | Venue/speaker utilization %, conflict-prevention stats |
| **Public Schedule** | Attendee-facing `/schedule` page, no login required |

### Milestone 3 — Sponsorship & Incident Operations

| Module | Description |
|---|---|
| **Sponsorship Agent** | Discovers & scores potential sponsors against event fit |
| **Sponsor Outreach** | Logs interactions/communications per sponsor |
| **Sponsor Follow-Ups** | Due-today / overdue follow-up buckets |
| **Sponsor Performance** | Conversion rate, response rate, amounts requested vs. committed |
| **Incident Management** | Log, update, assign and resolve operational incidents |
| **Incident Agent** | Priority/category recommendation for new incidents |
| **Operational Alerts** | Auto-generated alerts from incidents/venues/sponsorship state |

### Milestone 4 — Event Intelligence & Enterprise Deployment

See the dedicated section below — this is the newest layer, built entirely
on top of the real data produced by Milestones 1–3.

---

## 🧠 Milestone 4 — Event Intelligence & Enterprise Deployment

Milestone 4 adds a centralized **Intelligence** section to the app,
accessible from the navbar, containing six new surfaces:

```
INTELLIGENCE
├── Event Intelligence     /event-intelligence
├── Executive Dashboard    /executive-dashboard
├── Decision Support       /decision-support
├── Agent Orchestration    /agent-orchestration
├── Risk Center            /risk-center
└── System Health          /system-health
```

### 1. Event Intelligence Engine (`event_intelligence.py`)

A centralized engine that combines **real** data already produced by the
existing modules (`ai_model`, `operations`, `sponsorship`, `incidents`,
`alerts`) — never hard-coded or fake — into:

- **Event Health Score** (0-100) — a transparent, weighted score:

  | Dimension | Weight |
  |---|---|
  | Attendance | 20% |
  | Registration | 15% |
  | Venue readiness | 15% |
  | Speaker readiness | 10% |
  | Schedule health | 10% |
  | Sponsorship | 10% |
  | Incident status | 10% |
  | Operational alerts | 10% |

  Scored as: **90-100 Excellent · 75-89 Healthy · 50-74 Attention Required · 0-49 Critical.**
  Every component ships with a plain-English explanation shown under
  **"Why this score?"** on the Event Intelligence page.

- **Event Readiness Score** — are the operational building blocks in place
  (registrations, venues, speakers, sessions fully allocated, sponsors,
  zero critical/overdue incidents)?
- **Attendance Forecast**, **Registration Trend**, **No-show Risk Summary**
- **Venue/Speaker Utilization**, **Sponsorship Health**, **Incident/Operational Risk**
- **Priority Recommendations** and an **AI Executive Summary** — both generated
  from live numbers (e.g. *"Expected attendance (520) is 18% higher than
  your largest venue's capacity (440)..."*)

If there isn't enough data yet, the engine returns **"No data available
yet"** rather than inventing numbers.

### 2. Risk Engine (`risk_engine.py`)

Scans venues, sessions/speakers, registrations, sponsorship and incidents
for concrete, explainable risks. Each risk carries: `risk_key`, `module`,
`severity` (Low/Medium/High/Critical), `title`, `description`,
`probability`, `impact`, `risk_score`, `recommended_action`, `status`,
`created_time`. Detected risks are logged to the `risk_register` table.

### 3. Agent Orchestration (`agent_orchestrator.py`)

Wraps **every** existing "agent" plus new Milestone 4 agents behind one
orchestrator:

| Agent | Purpose |
|---|---|
| Registration Intelligence Agent | Registration volume/category mix |
| Attendance Prediction Agent | Attendance forecast + no-show risk |
| Venue Agent | Best-fit venue recommendation |
| Speaker Agent | Best-fit speaker recommendation |
| Scheduling Agent | Conflict/allocation gap detection |
| Sponsorship Agent | Pipeline health, conversion, follow-ups |
| Incident Agent | Open/critical/overdue incident assessment |
| Alert Agent | Active alert severity summary |
| Event Intelligence Agent | Health & readiness scores |
| Risk Agent | Full risk register + overall risk level |
| Executive Decision Agent | Synthesizes every agent's output into one final call |

**Real orchestration flow:** the orchestrator (a) classifies a free-text
problem or quick action into the relevant agent set via deterministic
keyword routing, (b) actually invokes those agents against the live
database, (c) collects their outputs, (d) determines an overall risk level,
(e) synthesizes one recommendation + reasoning + action, and (f) logs the
full run to `agent_execution_log` and `decision_log` — visible on the
**Agent Orchestration** page's execution log table.

> No external LLM/API is used or claimed. Every agent is deterministic,
> rule-based Python. The architecture (`context_extra` on
> `run_orchestration`) is designed so an external LLM call could be added
> later without breaking anything — but the app is fully functional today
> with zero API keys.

### 4. Decision Support Center (`decision_support.py` + `/decision-support`)

A conversational-style UI: type a question (or pick a quick action /
sample question) and see:

```
QUESTION → ANALYZING → AGENTS INVOKED → ANALYSIS →
RISK LEVEL → RECOMMENDATION → REASONING → ACTION
```

Sample questions: *"Is the event ready?"*, *"What are the biggest risks?"*,
*"Which venue should be selected?"*, *"Are there scheduling conflicts?"*,
etc. — all routed through the same real orchestrator.

### 5. Executive Dashboard (`/executive-dashboard`)

A senior-management view, distinct from the operational `/dashboard`:
Health Score ring, Readiness, Registrations, Expected Attendance,
Check-ins, No-show Risk, Venue/Speaker Utilization, Sponsorship Secured,
Critical Incidents, Active Alerts, Overall Risk — plus Registration Trend,
Event Health Trend, Venue/Speaker Utilization, Sponsorship Pipeline and
Incident Severity charts, an AI Executive Summary, Top Risks/Recommendations,
Upcoming Sessions, Pending Follow-ups and Critical Incidents. KPIs refresh
automatically every 30 seconds via lightweight polling
(`/api/intelligence/summary`) — no page reload, no WebSockets needed.

### 6. Executive Report (`/executive-report`)

One-click **PDF** (ReportLab, reusing the existing report infrastructure)
and **CSV** downloads containing the full health score, readiness,
registration/attendance/venue/speaker/sponsorship/incident statistics,
risk register and AI recommendations, with a timestamp.

### 7. System Health (`/system-health`, `GET /api/system-health`)

Live status of Application / Database / Intelligence Engine / Agent
Orchestrator / APIs, response time, active alert count, last intelligence
update, environment and version — useful to demonstrate production
readiness.

### Real-Time Intelligence (polling, not WebSockets)

Per the spec, the app uses **simple fetch-based polling** (every 30s on
the Executive Dashboard) rather than WebSockets, keeping Render deployment
simple.

---

## 🏗 Architecture

```
                     ┌─────────────────────────┐
                     │   Flask app.py (routes)  │
                     └────────────┬─────────────┘
        ┌───────────────┬─────────┼─────────────┬───────────────┐
        ▼               ▼         ▼              ▼               ▼
   ai_model.py    operations.py sponsorship.py incidents.py   alerts.py
   (M1 engine)    (M2 engine)   (M3 engine)    (M3 engine)    (M3 engine)
        │               │         │              │               │
        └───────────────┴────┬────┴──────────────┴───────────────┘
                              ▼
                    event_intelligence.py   (M4 — combines all of the above)
                              │
                 ┌────────────┼─────────────┐
                 ▼            ▼              ▼
          risk_engine.py  agent_orchestrator.py  decision_support.py
                              │
                              ▼
                    database.py → SQLite (single source of truth)
```

Every Milestone 4 module is a thin, additive layer that **reads** the same
tables Milestones 1-3 already write to — no duplicate data stores, no fake
dashboards.

---

## 🛠 Technology Stack

**Frontend:** HTML5, CSS3 (glassmorphism design system), JavaScript (ES6), Font Awesome, Chart.js, AOS
**Backend:** Python 3, Flask, Jinja2, Werkzeug (password hashing & sessions)
**Database:** SQLite (safe additive migrations across all 4 milestones)
**AI / Intelligence:** Rule-based, deterministic Python engines — no external ML frameworks or LLM API required
**Reports:** ReportLab (PDF), built-in `csv` module
**QR:** `qrcode` + `Pillow`
**Testing:** `pytest` + Flask test client
**Deployment:** Gunicorn + Render (`Procfile`, `requirements.txt`)

---

## 🗂 Folder Structure

```
project/
├── app.py                    # Main Flask application & all routes (M1-M4)
├── config.py                  # M4 — environment-based Dev/Prod/Testing config
├── database.py                 # SQLite connection, init & all migrations
├── ai_model.py                  # M1 — registration intelligence engine
├── operations.py                 # M2 — venue/speaker operations engine
├── sponsorship.py                 # M3 — sponsorship engine
├── incidents.py                    # M3 — incident engine
├── alerts.py                        # M3 — operational alerts engine
├── event_intelligence.py             # M4 — Event Intelligence Engine
├── risk_engine.py                     # M4 — Risk Engine
├── agent_orchestrator.py               # M4 — Agent Orchestration layer
├── decision_support.py                  # M4 — Decision Support Center logic
├── schema.sql                            # Base schema + seed data
├── requirements.txt
├── requirements-dev.txt                   # M4 — testing-only dependencies
├── Procfile                                # gunicorn app:app
├── pytest.ini
├── README.md
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── agents.md
│   ├── testing.md
│   └── deployment.md
├── tests/
│   ├── conftest.py
│   └── test_app.py
├── templates/
│   ├── base.html                # Shared layout — navbar now has an Intelligence dropdown
│   ├── ... (all M1-M3 templates, unchanged)
│   ├── executive_dashboard.html # M4
│   ├── event_intelligence.html  # M4
│   ├── agent_orchestration.html # M4
│   ├── decision_support.html    # M4
│   ├── risk_center.html         # M4
│   ├── system_health.html       # M4
│   ├── executive_report.html    # M4
│   ├── 403.html                 # M4
│   └── 500.html                 # M4
└── static/
    ├── css/
    │   ├── style.css, dashboard.css, operations.css, milestone3.css (unchanged)
    │   └── executive.css        # M4 — health ring, agent chips, risk badges, orchestration UI
    └── js/
        ├── script.js, dashboard.js, operations.js, milestone3.js (unchanged)
        ├── executive_dashboard.js   # M4
        ├── agent_orchestration.js   # M4
        └── decision_support.js      # M4
```

---

## 🗄 Database Schema

All Milestone 1-3 tables are preserved exactly as-is. Milestone 4 adds six
new tables via a safe, idempotent migration (`migrate_add_milestone4_tables`
in `database.py`, called on every app start — it only creates tables that
don't already exist and never drops or alters existing ones):

| Table | Purpose |
|---|---|
| `event_intelligence` | Historical health/readiness score snapshots (powers the Health Trend chart) |
| `risk_register` | Logged risks from the Risk Engine |
| `agent_execution_log` | Every agent invocation: agent, request, timing, status, result, confidence |
| `decision_log` | Every Decision Support / Orchestrator run: question, agents, risk level, recommendation |
| `executive_reports` | Audit trail of generated PDF/CSV executive reports |
| `system_health` | Historical System Health check-ins |

---

## 🔌 API Endpoints

### Milestone 4 — Intelligence

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/intelligence/summary` | Full Event Intelligence snapshot |
| GET | `/api/intelligence/health` | Health score + components + trend |
| GET | `/api/intelligence/risks` | Full risk register |
| GET | `/api/intelligence/recommendations` | AI recommendations |
| GET | `/api/intelligence/attendance` | Attendance prediction + no-show risk |
| GET | `/api/intelligence/sponsorship` | Sponsorship performance stats |
| GET | `/api/intelligence/incidents` | Incident dashboard stats |

### Milestone 4 — Orchestration & Decision Support

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/orchestrator/run` | Run the orchestrator (`{problem}` or `{quick_action}`) |
| GET | `/api/orchestrator/history` | Recent agent execution log |
| GET | `/api/orchestrator/status` | Available agents + recent executions |
| POST | `/api/decision-support/analyze` | Ask a decision-support question |
| GET | `/api/decision-support?question=...` | GET variant of the above |

### Milestone 4 — Reporting & Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/executive-report` | JSON snapshot + risk register |
| GET | `/executive-report/download/pdf` | Download the Executive PDF report |
| GET | `/executive-report/download/csv` | Download the Executive CSV report |
| GET | `/api/system-health` | System health JSON (unauthenticated status check) |

All Milestone 4 API responses follow a consistent envelope:
`{"success": true, "data": ...}` or `{"success": false, "error": "..."}`.

> Milestones 1-3 expose their own existing endpoints unchanged (registration,
> check-in, venues, speakers, sessions, sponsors, incidents, alerts, charts,
> reports) — see the code for the full list; none were removed or altered.

---

## 🔐 Authentication & Security

- Passwords hashed with Werkzeug (`generate_password_hash` / `check_password_hash`)
- Role-based access (`Admin` / `Organizer`) via `login_required(role=...)`
- `SECRET_KEY`, `DATABASE_PATH` and other sensitive values come from
  environment variables (`config.py`) — never hard-coded in source
- Session cookies: `HttpOnly`, `SameSite=Lax`, and `Secure` when served
  over HTTPS (`FORCE_HTTPS=1` or Production config)
- Baseline security headers on every response: `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `X-XSS-Protection`
- All SQL uses parameterized queries (`database.py` helpers) — no string
  interpolation into SQL anywhere in the codebase
- Structured JSON error responses for every API (`{"success": false,
  "error": "..."}`) — no Python tracebacks are ever shown to users;
  unhandled exceptions are logged server-side via `app.logger.exception`
- Dedicated `403.html` / `500.html` pages (in addition to the existing
  `404.html`)
- Request body size capped at 5 MB (`MAX_CONTENT_LENGTH`)

---

## 🧪 Testing

Milestone 4 ships an automated `pytest` suite (`tests/test_app.py`,
`tests/conftest.py`) covering: app startup & DB init, login, registration +
duplicate prevention, QR generation, check-in, venue creation + conflict
detection, speaker creation + conflict detection, session creation, sponsor
creation + outreach, incident creation, alert generation, event intelligence
calculation, event health calculation, risk detection, agent orchestration,
decision support, executive dashboard API, PDF report generation,
unauthorized access, invalid API input, and 404/error handling.

The suite runs against a fully isolated temporary SQLite database (via the
`DATABASE_PATH` environment variable) — it never touches your real
`database.db`.

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

See `docs/testing.md` for details and the full scenario list.

---

## ⚡ Performance

- The Event Intelligence Engine computes its snapshot from a small, fixed
  number of SQL queries per request (no N+1 loops over the full user table
  beyond what `ai_model.py` already required in Milestone 1)
- Risk detection re-uses the same `generate_operations_analytics()` /
  `get_performance_stats()` / `get_dashboard_stats()` calls the rest of the
  app already uses — no duplicate heavy computation
- The Executive Dashboard polls a single lightweight summary endpoint every
  30s rather than re-rendering the whole page or opening a WebSocket
  connection
- Historical snapshots (`event_intelligence` table) are best-effort inserts
  wrapped in `try/except` so a slow/blocked write never breaks a request
- Existing pagination, indexing and query patterns from Milestones 1-3 are
  untouched

---

## 🚀 Local Setup

```bash
cd project
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The app auto-creates `database.db` (with seed data) on first run and
auto-migrates in Milestone 2/3/4 tables on every subsequent run. Visit
`http://localhost:5000`.

Default seeded logins:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@springboard.ai` | `admin123` |
| Organizer | `organizer@springboard.ai` | `organizer123` |

> Change these before any real deployment — see [Environment Variables](#-environment-variables).

---

## 🌐 Render Deployment

1. **Push to GitHub**
   ```bash
   cd project
   git init
   git add .
   git commit -m "Milestone 4: Event Intelligence & Enterprise Deployment"
   git branch -M main
   git remote add origin https://github.com/<your-username>/register-ai.git
   git push -u origin main
   ```
   `database.db` is git-ignored — Render creates/migrates it automatically
   on first boot.

2. **Create the Web Service on [render.com](https://render.com)**
   - New → Web Service → connect your repo
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app` (from `Procfile`)
   - **Instance Type:** Free or Starter

3. **Environment variables** (Render dashboard → Environment):
   - `SECRET_KEY` = a long random string
   - `APP_ENV` = `production`
   - `FORCE_HTTPS` = `1` (Render serves HTTPS by default)

4. Deploy. `gunicorn app:app` binds `$PORT` automatically via Flask's
   `os.environ.get("PORT", 5000)` fallback in `app.py`. For a persistent
   database across deploys, attach a **Render Disk**, or migrate to managed
   Postgres for heavier production use.

See `docs/deployment.md` for more detail and troubleshooting.

---

## 🔑 Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing key | dev fallback (⚠️ change in production) |
| `APP_ENV` / `FLASK_ENV` | `development` \| `production` \| `testing` | `production` |
| `DATABASE_PATH` | Override the SQLite file location (used by the test suite) | `<project>/database.db` |
| `FORCE_HTTPS` | Set to `1` to force `Secure` session cookies | unset |
| `PORT` | Port Gunicorn/Flask binds to (set automatically by Render) | `5000` |

---

## 🎬 Mentor Demonstration Workflow

1. **Login as Admin** (`admin@springboard.ai` / `admin123`)
2. **Executive Dashboard** — show Health, Readiness, Attendance,
   Registrations, Venue/Speaker Utilization, Sponsorship, Incidents, Risks
3. **Event Intelligence** — click **Analyze Event**, expand *"Why this
   score?"* to show the live component breakdown
4. **Agent Orchestration** — run a quick action (e.g. *Analyze Event
   Health*) and show the agents, their outputs and the final recommendation;
   scroll to the Execution Log table
5. **Decision Support** — ask *"Is the event ready?"* and walk through
   Question → Analyzing → Agents Invoked → Analysis → Risk → Recommendation
6. **Create a venue/session conflict** (e.g. book two sessions in the same
   venue at an overlapping time) — show it logged in `conflict_log` and
   flagged by the Risk Center
7. **Show the orchestrator analyzing the conflict** via Decision Support
   (*"Are there scheduling conflicts?"*)
8. **Create/view a sponsorship risk** (e.g. an overdue follow-up) — show it
   on the Risk Center and in Sponsorship Agent output
9. **Create/view an incident** — show the Incident Agent, Risk Engine and
   Alerts reacting to it
10. **Return to the Executive Dashboard** — show health/risk numbers have
    changed
11. **Generate Executive Report** — download the PDF
12. **System Health** — show all five components green and production-ready

---

## 🛠 Troubleshooting

- **"No data available yet" everywhere** — expected on a fresh database;
  register a few attendees, add a venue/speaker/session, and a sponsor to
  see real scores.
- **PDF download fails** — ensure `reportlab` is installed
  (`pip install reportlab`); it's already in `requirements.txt`.
- **QR code doesn't render** — ensure `qrcode` + `Pillow` are installed.
- **Render deploy fails to start** — check the Start Command is exactly
  `gunicorn app:app` and that `SECRET_KEY` is set as an environment
  variable, not hard-coded.
- **Database looks "reset"** — Milestone 4 migrations never drop tables;
  if data looks missing, confirm `DATABASE_PATH` isn't pointing somewhere
  unexpected (e.g. left over from running the test suite in the same shell
  session — restart your terminal/shell).

---

## 📄 License

Built for educational purposes as part of the Infosys Springboard Virtual
Internship program. Free to use and modify for learning.
