"""
database.py
------------
Handles SQLite database connection, initialization and low-level
CRUD helper functions for the AI-Powered Registration Intelligence
& Attendee Management System.
"""

import sqlite3
import os
from datetime import datetime as _dt
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Allows tests / alternate deployments to point at a different SQLite file
# via the DATABASE_PATH environment variable without touching the real DB.
DB_PATH = os.environ.get("DATABASE_PATH") or os.path.join(BASE_DIR, "database.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_connection():
    """Return a sqlite3 connection with row factory set to dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(force: bool = False):
    """
    Initialize the database using schema.sql.
    If force=True, existing database.db is rebuilt from scratch.
    """
    fresh = force or not os.path.exists(DB_PATH)

    if fresh:
        conn = get_connection()
        with open(SCHEMA_PATH, "r") as f:
            conn.executescript(f.read())
        conn.commit()

        # Seed default admin + organizer accounts
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO admins (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("System Admin", "admin@springboard.ai", generate_password_hash("admin123"), "admin"),
        )
        cur.execute(
            "INSERT OR IGNORE INTO admins (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Event Organizer", "organizer@springboard.ai", generate_password_hash("organizer123"), "organizer"),
        )
        conn.commit()
        conn.close()
        migrate_add_milestone4_tables()
        print("[database.py] Fresh database created at", DB_PATH)
    else:
        print("[database.py] Using existing database at", DB_PATH)
        migrate_drop_year_column()
        migrate_participant_category()
        migrate_add_operations_tables()
        migrate_add_milestone3_tables()
        migrate_add_milestone4_tables()


def migrate_drop_year_column():
    """
    Safety net for databases deployed before the 'Year of Study' field was
    removed. If a legacy NOT NULL 'year' column is still present on the
    users table, rebuild the table without it so existing data and new
    inserts keep working without manual intervention.
    """
    conn = get_connection()
    try:
        cols = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "year" not in cols:
            return

        keep_cols = [c for c in cols if c != "year"]
        col_list = ", ".join(keep_cols)

        conn.execute("ALTER TABLE users RENAME TO users_old")
        conn.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                college TEXT NOT NULL,
                department TEXT NOT NULL,
                gender TEXT NOT NULL,
                city TEXT NOT NULL,
                event TEXT NOT NULL,
                food TEXT NOT NULL,
                attendance_mode TEXT NOT NULL,
                checked_in INTEGER DEFAULT 0,
                qr_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute(f"INSERT INTO users ({col_list}) SELECT {col_list} FROM users_old")
        conn.execute("DROP TABLE users_old")
        conn.commit()
        print("[database.py] Migrated legacy 'year' column out of users table")
    except sqlite3.Error as e:
        conn.rollback()
        print("[database.py] Migration skipped/failed:", e)
    finally:
        conn.close()


def migrate_participant_category():
    """
    Safety net for databases deployed before 'foodPreference' / 'eventCategory'
    were replaced with the single 'participantCategory' field. If the legacy
    'food' / 'event' columns are still present, rebuild the users table with
    'participant_category' + 'registration_id' instead, preserving all other
    existing data. Legacy rows are backfilled with a default category and a
    generated Registration ID so old records keep working.
    """
    conn = get_connection()
    try:
        cols = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "food" not in cols and "event" not in cols and "participant_category" in cols and "registration_id" in cols:
            return

        conn.execute("ALTER TABLE users RENAME TO users_old")
        conn.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                college TEXT NOT NULL,
                department TEXT NOT NULL,
                gender TEXT NOT NULL,
                city TEXT NOT NULL,
                participant_category TEXT NOT NULL,
                attendance_mode TEXT NOT NULL,
                registration_id TEXT UNIQUE,
                checked_in INTEGER DEFAULT 0,
                qr_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        old_rows = conn.execute("SELECT * FROM users_old ORDER BY id ASC").fetchall()
        for row in old_rows:
            r = dict(row)
            category = r.get("participant_category") or "Student"
            created_at = r.get("created_at") or ""
            year = created_at[:4] if created_at and created_at[:4].isdigit() else str(_dt.now().year)
            reg_id = r.get("registration_id") or f"REG-{year}-{int(r['id']):04d}"
            conn.execute(
                """INSERT INTO users (id, name, email, phone, college, department, gender, city,
                   participant_category, attendance_mode, registration_id, checked_in, qr_code, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (r["id"], r["name"], r["email"], r["phone"], r["college"], r["department"],
                 r["gender"], r["city"], category, r.get("attendance_mode") or "Offline",
                 reg_id, r.get("checked_in") or 0, r.get("qr_code"), r.get("created_at")),
            )
        conn.execute("DROP TABLE users_old")
        conn.commit()
        print("[database.py] Migrated 'food'/'event' columns to 'participant_category' + 'registration_id'")
    except sqlite3.Error as e:
        conn.rollback()
        print("[database.py] Migration skipped/failed:", e)
    finally:
        conn.close()


def migrate_add_operations_tables():
    """
    Safety net for databases deployed before Milestone 2 (Venue & Speaker
    Operations) was added. Creates the venues / speakers / sessions /
    conflict_log tables if they don't already exist on an existing deployed
    database, and seeds them with demo data so the new modules are usable
    immediately without wiping any Milestone 1 data.
    """
    conn = get_connection()
    try:
        existing = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}

        created_any = False

        if "venues" not in existing:
            conn.executescript("""
                CREATE TABLE venues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    location TEXT,
                    capacity INTEGER NOT NULL DEFAULT 0,
                    room_type TEXT,
                    facilities TEXT,
                    status TEXT NOT NULL DEFAULT 'Available',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            created_any = True

        if "speakers" not in existing:
            conn.executescript("""
                CREATE TABLE speakers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    organization TEXT,
                    designation TEXT,
                    expertise TEXT,
                    bio TEXT,
                    preferred_session_type TEXT,
                    available_dates TEXT,
                    available_slots TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            created_any = True

        if "sessions" not in existing:
            conn.executescript("""
                CREATE TABLE sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    session_type TEXT,
                    session_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    expected_attendees INTEGER DEFAULT 0,
                    required_facilities TEXT,
                    venue_id INTEGER,
                    speaker_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'Scheduled',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE SET NULL,
                    FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE SET NULL
                );
            """)
            created_any = True

        if "conflict_log" not in existing:
            conn.executescript("""
                CREATE TABLE conflict_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conflict_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            created_any = True

        conn.commit()

        # Seed demo data only if the venues table was just created and is empty
        venue_count = conn.execute("SELECT COUNT(*) as c FROM venues").fetchone()["c"]
        if venue_count == 0:
            conn.executescript("""
                INSERT INTO venues (name, location, capacity, room_type, facilities, status) VALUES
                ('Main Auditorium', 'Block A, Ground Floor', 300, 'Auditorium', 'Projector,Microphone,Speakers,Stage,Air Conditioning,Recording Equipment,Wi-Fi', 'Available'),
                ('Seminar Hall 1', 'Block B, 1st Floor', 120, 'Seminar Hall', 'Projector,Microphone,Speakers,Wi-Fi,Air Conditioning', 'Available'),
                ('Computer Lab 3', 'Block C, 2nd Floor', 60, 'Computer Lab', 'Projector,Wi-Fi,Air Conditioning,Video Conferencing', 'Available'),
                ('Conference Room A', 'Block A, 3rd Floor', 40, 'Conference Room', 'Smart Board,Microphone,Wi-Fi,Video Conferencing,Air Conditioning', 'Available'),
                ('Workshop Hall', 'Block D, Ground Floor', 150, 'Workshop Hall', 'Projector,Smart Board,Microphone,Speakers,Wi-Fi', 'Available'),
                ('Open Air Arena', 'Central Lawn', 500, 'Outdoor Arena', 'Stage,Speakers,Microphone', 'Maintenance');
            """)
            conn.commit()

        speaker_count = conn.execute("SELECT COUNT(*) as c FROM speakers").fetchone()["c"]
        if speaker_count == 0:
            conn.executescript("""
                INSERT INTO speakers (name, email, phone, organization, designation, expertise, bio, preferred_session_type, available_dates, available_slots) VALUES
                ('Dr. Ananya Rao', 'ananya.rao@example.com', '9876543210', 'Infosys', 'Principal AI Architect', 'Artificial Intelligence, Machine Learning, Deep Learning', 'Dr. Rao leads applied AI research and has delivered keynotes at major technical summits.', 'Keynote', '2026-09-12,2026-09-20', '09:00-18:00'),
                ('Rahul Mehta', 'rahul.mehta@example.com', '9876543211', 'TechNova Solutions', 'Senior Software Engineer', 'Cloud Computing, DevOps, Kubernetes', 'Rahul specializes in scalable cloud-native systems and enjoys mentoring hackathon teams.', 'Workshop', '2026-09-20,2026-09-14', '10:00-17:00'),
                ('Priya Sundaram', 'priya.sundaram@example.com', '9876543212', 'DataWorks Analytics', 'Data Science Lead', 'Data Science, Analytics, Python, Machine Learning', 'Priya has 10+ years of experience building data-driven products and loves hands-on workshops.', 'Technical Session', '2026-09-12,2026-09-18', '09:00-16:00'),
                ('Karan Verma', 'karan.verma@example.com', '9876543213', 'StartUp Hub', 'Founder & CEO', 'Entrepreneurship, Business Strategy, Startups', 'Karan has founded two startups and regularly mentors early-stage founders on pitching.', 'Panel Discussion', '2026-09-14', '11:00-18:00'),
                ('Sneha Iyer', 'sneha.iyer@example.com', '9876543214', 'CyberSafe Labs', 'Cybersecurity Consultant', 'Cybersecurity, Ethical Hacking, Network Security', 'Sneha trains organizations on security best practices and has spoken at multiple tech conferences.', 'Training', '2026-09-20,2026-09-22', '09:00-15:00');
            """)
            conn.commit()

        session_count = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
        if session_count == 0:
            conn.executescript("""
                INSERT INTO sessions (title, description, session_type, session_date, start_time, end_time, expected_attendees, required_facilities, venue_id, speaker_id, status) VALUES
                ('Opening Keynote: The Future of AI', 'A keynote on where artificial intelligence is headed over the next decade.', 'Keynote', '2026-09-12', '09:30', '10:30', 280, 'Projector,Microphone,Speakers,Stage', 1, 1, 'Scheduled'),
                ('Hands-on Kubernetes Workshop', 'A practical workshop on deploying containerized applications with Kubernetes.', 'Workshop', '2026-09-20', '10:00', '12:30', 55, 'Projector,Wi-Fi', 3, 2, 'Scheduled'),
                ('Data Science in Practice', 'A technical session covering real-world data science pipelines.', 'Technical Session', '2026-09-12', '11:00', '12:30', 110, 'Projector,Microphone,Wi-Fi', 2, 3, 'Scheduled'),
                ('Founders Panel: Building a Startup', 'A panel discussion with founders sharing lessons from building companies.', 'Panel Discussion', '2026-09-14', '14:00', '15:30', 130, 'Smart Board,Microphone,Wi-Fi', 5, 4, 'Upcoming');
            """)
            conn.commit()

        if created_any:
            print("[database.py] Migrated: added Milestone 2 Venue/Speaker/Session/Conflict tables + demo data")
    except sqlite3.Error as e:
        conn.rollback()
        print("[database.py] Operations migration skipped/failed:", e)
    finally:
        conn.close()


def migrate_add_milestone3_tables():
    """
    Safety net for databases deployed before Milestone 3 (Sponsorship &
    Incident Management) was added. Creates the sponsors / sponsor_contacts /
    sponsor_interactions / sponsor_followups / sponsorship_opportunities /
    incidents / incident_updates / operational_alerts tables if they don't
    already exist, and seeds a small demo dataset so the new modules are
    usable immediately without wiping any Milestone 1/2 data.
    """
    conn = get_connection()
    try:
        existing = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}

        table_ddl = {
            "sponsors": """
                CREATE TABLE sponsors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    industry TEXT,
                    website TEXT,
                    location TEXT,
                    target_audience TEXT,
                    keywords TEXT,
                    sponsorship_category TEXT,
                    budget_potential TEXT,
                    estimated_budget INTEGER DEFAULT 0,
                    contact_person TEXT,
                    contact_email TEXT,
                    contact_phone TEXT,
                    suitability_score INTEGER DEFAULT 0,
                    match_category TEXT,
                    score_explanation TEXT,
                    status TEXT NOT NULL DEFAULT 'Discovered',
                    source TEXT DEFAULT 'Manual Entry',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
            "sponsor_contacts": """
                CREATE TABLE sponsor_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sponsor_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    designation TEXT,
                    email TEXT,
                    phone TEXT,
                    is_primary INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
                );
            """,
            "sponsor_interactions": """
                CREATE TABLE sponsor_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sponsor_id INTEGER NOT NULL,
                    interaction_type TEXT NOT NULL,
                    communication_method TEXT,
                    subject TEXT,
                    message TEXT,
                    sponsor_response TEXT,
                    next_action TEXT,
                    follow_up_date TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
                );
            """,
            "sponsor_followups": """
                CREATE TABLE sponsor_followups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sponsor_id INTEGER NOT NULL,
                    due_date TEXT NOT NULL,
                    reason TEXT,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
                );
            """,
            "sponsorship_opportunities": """
                CREATE TABLE sponsorship_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sponsor_id INTEGER NOT NULL,
                    package TEXT,
                    benefits TEXT,
                    amount_requested REAL DEFAULT 0,
                    amount_committed REAL DEFAULT 0,
                    amount_received REAL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'Proposed',
                    confirmed_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
                );
            """,
            "incidents": """
                CREATE TABLE incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'Medium',
                    status TEXT NOT NULL DEFAULT 'Reported',
                    related_venue_id INTEGER,
                    related_session_id INTEGER,
                    related_speaker_id INTEGER,
                    related_sponsor_id INTEGER,
                    reported_by TEXT,
                    assigned_to TEXT,
                    due_date TEXT,
                    recommendation TEXT,
                    resolution TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY (related_venue_id) REFERENCES venues(id) ON DELETE SET NULL,
                    FOREIGN KEY (related_session_id) REFERENCES sessions(id) ON DELETE SET NULL,
                    FOREIGN KEY (related_speaker_id) REFERENCES speakers(id) ON DELETE SET NULL,
                    FOREIGN KEY (related_sponsor_id) REFERENCES sponsors(id) ON DELETE SET NULL
                );
            """,
            "incident_updates": """
                CREATE TABLE incident_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id INTEGER NOT NULL,
                    update_text TEXT NOT NULL,
                    status_change TEXT,
                    updated_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
                );
            """,
            "operational_alerts": """
                CREATE TABLE operational_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT NOT NULL DEFAULT 'Info',
                    module TEXT NOT NULL,
                    related_entity_type TEXT,
                    related_entity_id INTEGER,
                    is_read INTEGER DEFAULT 0,
                    is_resolved INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
        }

        created_any = False
        for name, ddl in table_ddl.items():
            if name not in existing:
                conn.executescript(ddl)
                created_any = True

        conn.commit()

        # Seed a small demo dataset only if sponsors was just created and is empty
        sponsor_count = conn.execute("SELECT COUNT(*) as c FROM sponsors").fetchone()["c"]
        if sponsor_count == 0:
            conn.executescript("""
                INSERT INTO sponsors (company_name, industry, website, location, target_audience, keywords,
                    sponsorship_category, budget_potential, estimated_budget, contact_person, contact_email,
                    contact_phone, suitability_score, match_category, score_explanation, status, source, notes, created_at) VALUES
                ('NexaCloud Technologies', 'Technology', 'https://nexacloud.example.com', 'Bengaluru',
                 'Students, Developers, AI Professionals', 'AI, cloud, machine learning, developers', 'Gold Sponsor',
                 'High', 300000, 'Meera Krishnan', 'meera.k@nexacloud.example.com', '9845012345', 92, 'Excellent Match',
                 'Recommended because the technology industry directly matches the AI/ML Summit and the audience aligns closely with expected attendees.',
                 'Confirmed', 'Directory', 'Confirmed as Gold Sponsor after two rounds of negotiation.', datetime('now','-21 days')),
                ('BrightPath EduTech', 'Education', 'https://brightpathedu.example.com', 'Bengaluru',
                 'Students, College Faculty', 'edtech, learning, student outreach, colleges', 'Silver Sponsor', 'Medium',
                 120000, 'Arvind Nair', 'arvind@brightpathedu.example.com', '9845012346', 78, 'Good Match',
                 'Recommended because the education industry aligns with the student-heavy audience.',
                 'Negotiating', 'Directory', 'Awaiting final sign-off from their marketing head.', datetime('now','-18 days')),
                ('FinEdge Capital', 'Finance', 'https://finedgecapital.example.com', 'Mumbai', 'Professionals, Startups',
                 'fintech, investment, startups, finance', 'Bronze Sponsor', 'Medium', 90000, 'Rohit Sharma',
                 'rohit.sharma@finedge.example.com', '9845012347', 61, 'Moderate Match',
                 'Moderate relevance; overlap exists mainly through the startup and professional segments.',
                 'Follow-up Required', 'Manual Entry', 'Responded with interest but needs a formal proposal.', datetime('now','-14 days')),
                ('ConnectTel Communications', 'Telecommunications', 'https://connecttel.example.com', 'Hyderabad',
                 'Students, Professionals, Developers', 'telecom, 5G, connectivity, networking', 'Silver Sponsor', 'High',
                 200000, 'Anil Kapoor', 'anil.kapoor@connecttel.example.com', '9845012352', 84, 'Excellent Match',
                 'Recommended because telecom infrastructure is highly relevant and budget potential is high.',
                 'Proposal Sent', 'Directory', 'Formal proposal sent; awaiting response by follow-up date.', datetime('now','-5 days')),
                ('LaunchPad Ventures', 'Startups', 'https://launchpadventures.example.com', 'Bengaluru',
                 'Students, Founders, Investors', 'startups, venture capital, incubation, entrepreneurship', 'Gold Sponsor',
                 'High', 250000, 'Neha Gupta', 'neha.gupta@launchpad.example.com', '9845012353', 88, 'Excellent Match',
                 'Recommended because the startup ecosystem focus matches the event themes closely.',
                 'Shortlisted', 'Directory', 'Shortlisted after evaluation; outreach message drafted, not yet sent.', datetime('now','-4 days'));

                INSERT INTO sponsor_interactions (sponsor_id, interaction_type, communication_method, subject, message, sponsor_response, next_action, follow_up_date, created_by, created_at) VALUES
                (1, 'Discovery', 'System', 'Sponsor discovered via directory search', 'Added to sponsor directory after matching "technology, AI" keyword search.', NULL, 'Run suitability evaluation', NULL, 'System Admin', datetime('now','-21 days')),
                (1, 'Evaluation', 'System', 'Suitability score generated', 'Sponsorship Agent scored this sponsor 92% — Excellent Match.', NULL, 'Shortlist sponsor', NULL, 'System Admin', datetime('now','-20 days')),
                (1, 'Outreach', 'Email', 'Sponsorship Proposal — AI & ML Summit 2026', 'Sent outreach email introducing the event and requesting Gold Sponsor participation.', NULL, 'Await response', datetime('now','-16 days'), 'Event Organizer', datetime('now','-19 days')),
                (1, 'Response', 'Email', 'Re: Sponsorship Proposal', 'Sponsor replied expressing strong interest.', 'Interested — requested a call.', 'Schedule call', datetime('now','-15 days'), 'Event Organizer', datetime('now','-17 days')),
                (1, 'Confirmation', 'Email', 'Sponsorship Confirmed', 'Sponsor confirmed participation as Gold Sponsor.', 'Confirmed — payment to follow.', 'Track payment receipt', NULL, 'Event Organizer', datetime('now','-21 days')),
                (3, 'Discovery', 'System', 'Sponsor discovered via manual entry', 'Organizer manually recorded this sponsor after a networking event.', NULL, 'Run suitability evaluation', NULL, 'Event Organizer', datetime('now','-14 days')),
                (3, 'Response', 'LinkedIn', 'Re: Sponsorship Introduction', 'Contact responded showing interest.', 'Interested — requested a formal written proposal.', 'Send formal proposal and follow up', datetime('now','+1 days'), 'Event Organizer', datetime('now','-7 days'));

                INSERT INTO sponsor_followups (sponsor_id, due_date, reason, status, created_at) VALUES
                (3, date('now'), 'Follow up after internal budget approval for Bronze Sponsor package.', 'Pending', datetime('now','-9 days')),
                (4, date('now','+1 days'), 'Check for response to the Silver Sponsor proposal.', 'Pending', datetime('now','-3 days'));

                INSERT INTO sponsorship_opportunities (sponsor_id, package, benefits, amount_requested, amount_committed, amount_received, status, confirmed_date, created_at) VALUES
                (1, 'Gold Sponsor', 'Logo on main stage backdrop, address slot, branded booth, social media mentions', 300000, 300000, 150000, 'Confirmed', date('now','-2 days'), datetime('now','-14 days')),
                (4, 'Silver Sponsor', 'Logo on website and banners, booth space, session sponsorship', 200000, 0, 0, 'Proposed', NULL, datetime('now','-3 days'));

                INSERT INTO incidents (title, description, category, priority, status, related_venue_id, related_speaker_id, reported_by, assigned_to, due_date, recommendation, resolution, created_at, resolved_at) VALUES
                ('Projector malfunction in Main Auditorium', 'The main projector shut off twice during setup before the opening keynote.', 'Venue', 'Critical', 'Closed', 1, NULL, 'Event Organizer', 'Facilities Team', date('now','-11 days'),
                 'Immediately notify the event organizer and venue manager. Reassign the affected session to an available suitable venue if possible.',
                 'Backup projector installed within 20 minutes; keynote started on time.', datetime('now','-12 days'), datetime('now','-12 days')),
                ('Wi-Fi congestion in Workshop Hall', 'Attendees reported slow or dropped Wi-Fi during the hands-on workshop session.', 'Technical', 'High', 'Reported', 5, NULL, 'Volunteer Coordinator', NULL, date('now','+1 days'),
                 'Notify the venue manager and IT support to check access point load.', NULL, datetime('now'), NULL);

                INSERT INTO incident_updates (incident_id, update_text, status_change, updated_by, created_at) VALUES
                (1, 'Incident reported by the organizer during pre-keynote setup checks.', 'Reported', 'Event Organizer', datetime('now','-12 days')),
                (1, 'Backup projector installed; keynote proceeded on schedule.', 'Resolved', 'Facilities Team', datetime('now','-12 days')),
                (1, 'Verified with organizer that the keynote ran without further issues.', 'Closed', 'Event Organizer', datetime('now','-11 days')),
                (2, 'Incident reported by volunteer coordinator during the workshop session.', 'Reported', 'Volunteer Coordinator', datetime('now'));

                INSERT INTO operational_alerts (title, description, severity, module, related_entity_type, related_entity_id, is_read, is_resolved, created_at) VALUES
                ('Critical incident reported: Projector malfunction', 'A critical-priority incident was reported in Main Auditorium.', 'Critical', 'Incident', 'incident', 1, 1, 1, datetime('now','-12 days')),
                ('High-priority incident open: Wi-Fi congestion', 'Wi-Fi congestion reported in Workshop Hall is still open and unassigned.', 'High', 'Incident', 'incident', 2, 0, 0, datetime('now')),
                ('Sponsor awaiting response', 'ConnectTel Communications has not responded to the Silver Sponsor proposal.', 'Info', 'Sponsorship', 'sponsor', 4, 0, 0, datetime('now','-3 days'));
            """)
            conn.commit()

        if created_any:
            print("[database.py] Migrated: added Milestone 3 Sponsorship/Incident/Alerts tables + demo data")
    except sqlite3.Error as e:
        conn.rollback()
        print("[database.py] Milestone 3 migration skipped/failed:", e)
    finally:
        conn.close()


def migrate_add_milestone4_tables():
    """
    Safety net for databases deployed before Milestone 4 (Event Intelligence
    & Enterprise Deployment) was added. Creates the event_intelligence /
    risk_register / agent_execution_log / decision_log / executive_reports /
    system_health tables if they don't already exist. Never touches or
    deletes any Milestone 1-3 table or data.
    """
    conn = get_connection()
    try:
        existing = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}

        table_ddl = {
            "event_intelligence": """
                CREATE TABLE event_intelligence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    health_score INTEGER,
                    health_label TEXT,
                    readiness_score INTEGER,
                    snapshot_json TEXT NOT NULL,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
            "risk_register": """
                CREATE TABLE risk_register (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    risk_key TEXT NOT NULL,
                    module TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    probability INTEGER,
                    impact INTEGER,
                    risk_score INTEGER,
                    recommended_action TEXT,
                    status TEXT NOT NULL DEFAULT 'Open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
            "agent_execution_log": """
                CREATE TABLE agent_execution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    request_text TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    duration_ms INTEGER,
                    status TEXT NOT NULL DEFAULT 'Completed',
                    result_summary TEXT,
                    confidence INTEGER,
                    error TEXT
                );
            """,
            "decision_log": """
                CREATE TABLE decision_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    agents_consulted TEXT,
                    risk_level TEXT,
                    recommendation TEXT,
                    reasoning TEXT,
                    action TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
            "executive_reports": """
                CREATE TABLE executive_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    format TEXT NOT NULL,
                    health_score INTEGER,
                    generated_by TEXT,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
            "system_health": """
                CREATE TABLE system_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time_ms INTEGER,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
        }

        created_any = False
        for name, ddl in table_ddl.items():
            if name not in existing:
                conn.executescript(ddl)
                created_any = True

        conn.commit()
        if created_any:
            print("[database.py] Migrated: added Milestone 4 Intelligence/Risk/Orchestration tables")
    except sqlite3.Error as e:
        conn.rollback()
        print("[database.py] Milestone 4 migration skipped/failed:", e)
    finally:
        conn.close()


# ---------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------
def query_all(sql, params=()):
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_one(sql, params=()):
    conn = get_connection()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return dict(row) if row else None


def execute(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


if __name__ == "__main__":
    init_db(force=True)
