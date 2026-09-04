# Deployment — Milestone 4

RegisterAI remains a standard Gunicorn-served Flask app; Milestone 4 adds
no infrastructure that complicates the existing Render deployment.

## Local run

```bash
cd project
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

`app.py`'s entry point calls `db.init_db(force=False)` on startup, which is
safe to run every time: it creates `database.db` (with seed data) if it
doesn't exist, and otherwise runs the additive Milestone 2/3/4 migrations
against the existing file without touching existing rows.

Visit `http://localhost:5000`.

## Gunicorn (production-style local test)

```bash
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:5000
```

## Render deployment

1. **Push to GitHub** (`database.db` is git-ignored — see `.gitignore`;
   Render creates/migrates it automatically on first boot).
2. **New Web Service** on [render.com](https://render.com), connect the repo.
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app` (already in `Procfile`)
3. **Environment variables** (Render dashboard → Environment):
   - `SECRET_KEY` — a long random string (never commit this to source)
   - `APP_ENV=production`
   - `FORCE_HTTPS=1` (Render serves HTTPS by default; this makes session
     cookies `Secure`)
4. Deploy. Flask reads `PORT` from the environment (`os.environ.get("PORT",
   5000)`), which Gunicorn/Render set automatically — no manual port
   configuration needed.

### Persisting the database across deploys

Render's filesystem is ephemeral between deploys by default. For a demo or
short-lived evaluation this is usually fine (the app reseeds automatically
via `init_db`). For anything longer-lived:
- Attach a **Render Disk** mounted at the project directory (or set
  `DATABASE_PATH` to a path on that disk), or
- Migrate to managed Postgres for real production use (out of scope for
  this milestone, but `database.py`'s query helpers are isolated enough to
  make that swap straightforward later).

## Production configuration

`config.py` exposes `DevelopmentConfig` / `ProductionConfig` /
`TestingConfig`, selected via `APP_ENV` (falls back to `FLASK_ENV`, then
`production`). All secrets come from environment variables — nothing
sensitive is hard-coded in source, satisfying Rule 12/22 of the project spec.

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing key | dev fallback (⚠️ change in production) |
| `APP_ENV` / `FLASK_ENV` | `development` \| `production` \| `testing` | `production` |
| `DATABASE_PATH` | Override the SQLite file location | `<project>/database.db` |
| `FORCE_HTTPS` | Set to `1` to force `Secure` session cookies | unset |
| `PORT` | Port Gunicorn/Flask binds to (set by Render) | `5000` |

## Troubleshooting

- **App won't start on Render** — confirm the Start Command is exactly
  `gunicorn app:app` and that `requirements.txt` installed cleanly (check
  the build logs for a missing system library needed by Pillow/reportlab —
  Render's default Python image includes what's needed for the pinned
  versions in this project).
- **Sessions don't persist / login loops** — make sure `SECRET_KEY` is set
  as an environment variable (a value that changes on every restart will
  invalidate all sessions).
- **"No data available yet" everywhere after deploy** — expected on a
  fresh database; register a few attendees or use the existing seed data
  path in `database.py` to see real Event Intelligence numbers.
- **Static files not loading** — Flask's default `static/` folder handling
  is used as-is (`url_for('static', filename=...)` throughout every
  template); no custom static file server was introduced.
