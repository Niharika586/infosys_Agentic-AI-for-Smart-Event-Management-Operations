"""
risk_engine.py
---------------
MILESTONE 4 — Risk Engine.

Scans the real state of the existing database (venues, sessions, speakers,
sponsors, incidents, alerts) and produces a structured, explainable risk
register. Every risk carries a severity, probability/impact estimate, a
risk score and a recommended action so it can be shown directly in the
Risk Center UI and consumed by the Agent Orchestrator / Decision Support.

Deterministic and rule-based — no external services required.
"""

from datetime import datetime, date

import database as db
import operations as ops
import sponsorship as spx
import incidents as inc
import alerts

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _risk(risk_key, module, severity, title, description, probability, impact, recommended_action, status="Open"):
    risk_score = round((probability * impact) / 10)  # 0-100 scale (probability/impact both 0-10)
    return {
        "risk_key": risk_key,
        "module": module,
        "severity": severity,
        "title": title,
        "description": description,
        "probability": probability,
        "impact": impact,
        "risk_score": risk_score,
        "recommended_action": recommended_action,
        "status": status,
        "created_time": datetime.now().isoformat(timespec="seconds"),
    }


def detect_venue_risks():
    risks = []
    venues = db.query_all("SELECT * FROM venues")
    sessions = db.query_all("SELECT * FROM sessions WHERE status != 'Cancelled'")
    venue_by_id = {v["id"]: v for v in venues}

    for s in sessions:
        v = venue_by_id.get(s["venue_id"])
        if v and s.get("expected_attendees") and v["capacity"] < s["expected_attendees"]:
            over = s["expected_attendees"] - v["capacity"]
            risks.append(_risk(
                f"venue_capacity_{s['id']}", "Venue", "High" if over > 20 else "Medium",
                f"Capacity risk: '{s['title']}'",
                f"Session '{s['title']}' expects {s['expected_attendees']} attendees but "
                f"'{v['name']}' only holds {v['capacity']} ({over} over capacity).",
                probability=8, impact=8,
                recommended_action=f"Reassign to a venue with capacity ≥ {s['expected_attendees']}, "
                                    f"or split into multiple sessions.",
            ))
        if v and v["status"] == "Maintenance" and s["venue_id"] == v["id"]:
            risks.append(_risk(
                f"venue_maintenance_{s['id']}", "Venue", "Critical",
                f"Session booked in a venue under maintenance",
                f"'{s['title']}' is scheduled in '{v['name']}', which is currently marked under maintenance.",
                probability=9, impact=9,
                recommended_action="Reassign the session to an available venue immediately.",
            ))

    conflicts = db.query_all("SELECT * FROM conflict_log WHERE conflict_type = 'venue' ORDER BY created_at DESC LIMIT 5")
    for c in conflicts:
        risks.append(_risk(
            f"venue_conflict_{c['id']}", "Venue", "Medium",
            "Venue scheduling conflict logged",
            c["message"], probability=6, impact=6,
            recommended_action="Review the Smart Scheduler to confirm the conflict was resolved.",
        ))

    maintenance = [v for v in venues if v["status"] == "Maintenance"]
    total = len(venues)
    if total and len(maintenance) / total >= 0.3:
        risks.append(_risk(
            "venue_maintenance_load", "Venue", "Medium",
            "High proportion of venues under maintenance",
            f"{len(maintenance)} of {total} venues are currently under maintenance, reducing available capacity.",
            probability=6, impact=5,
            recommended_action="Prioritize maintenance completion or arrange temporary alternate venues.",
        ))

    return risks


def detect_speaker_risks():
    risks = []
    sessions = db.query_all(
        "SELECT * FROM sessions WHERE status != 'Cancelled' AND speaker_id IS NULL"
    )
    for s in sessions:
        risks.append(_risk(
            f"speaker_unassigned_{s['id']}", "Speaker", "Medium",
            f"No speaker assigned: '{s['title']}'",
            f"Session '{s['title']}' on {s['session_date']} has no speaker assigned yet.",
            probability=6, impact=6,
            recommended_action="Use the Speaker Agent to find a matching available speaker.",
        ))

    conflicts = db.query_all("SELECT * FROM conflict_log WHERE conflict_type = 'speaker' ORDER BY created_at DESC LIMIT 5")
    for c in conflicts:
        risks.append(_risk(
            f"speaker_conflict_{c['id']}", "Speaker", "Medium",
            "Speaker scheduling conflict logged",
            c["message"], probability=6, impact=6,
            recommended_action="Confirm the speaker's final assigned slot in the Smart Scheduler.",
        ))
    return risks


def detect_registration_risks():
    risks = []
    users = db.query_all("SELECT * FROM users")
    if not users:
        return risks
    import ai_model
    pred = ai_model.predict_attendance_percentage(users)
    if pred["predicted_percentage"] < 55:
        risks.append(_risk(
            "low_attendance_forecast", "Registration", "Medium",
            "Low attendance forecast",
            f"AI-predicted attendance is only {pred['predicted_percentage']}% "
            f"({pred['confidence']} confidence).",
            probability=6, impact=6,
            recommended_action="Send reminder communications and confirm attendance with registrants.",
        ))
    no_shows = ai_model.predict_no_shows(users)
    high_risk = [n for n in no_shows if n["risk_level"] == "High"]
    if len(high_risk) >= max(3, round(len(users) * 0.2)):
        risks.append(_risk(
            "high_no_show_risk", "Registration", "Medium",
            "High no-show risk detected",
            f"{len(high_risk)} of {len(users)} registrants ({round(len(high_risk)/len(users)*100)}%) "
            f"are flagged High no-show risk.",
            probability=6, impact=5,
            recommended_action="Target high no-show-risk registrants with reminder outreach.",
        ))
    return risks


def detect_sponsorship_risks():
    risks = []
    perf = spx.get_performance_stats()
    if perf["total_sponsors"] and perf["amount_requested"]:
        shortfall_ratio = 1 - (perf["amount_committed"] / perf["amount_requested"])
        if shortfall_ratio > 0.4:
            risks.append(_risk(
                "sponsorship_shortfall", "Sponsorship", "Medium",
                "Sponsorship shortfall risk",
                f"Only ₹{perf['amount_committed']:,.0f} committed against ₹{perf['amount_requested']:,.0f} "
                f"requested ({round(shortfall_ratio*100)}% shortfall).",
                probability=6, impact=7,
                recommended_action="Accelerate outreach to shortlisted/high-scoring sponsors to close the gap.",
            ))

    overdue = spx.get_followup_buckets()["overdue"]
    for f in overdue:
        risks.append(_risk(
            f"sponsor_followup_overdue_{f['id']}", "Sponsorship", "Low",
            f"Overdue follow-up: {f['company_name']}",
            f"Follow-up for {f['company_name']} was due {f['due_date']} and is still pending.",
            probability=5, impact=4,
            recommended_action="Contact the sponsor directly; consider phone if email gets no response.",
        ))
    return risks


def detect_incident_risks():
    risks = []
    incidents = db.query_all(
        "SELECT * FROM incidents WHERE status IN ('Reported','Assigned','In Progress')"
    )
    today = date.today().isoformat()
    for i in incidents:
        if i["priority"] == "Critical":
            risks.append(_risk(
                f"incident_critical_{i['id']}", "Incident", "Critical",
                f"Critical incident open: {i['title']}",
                i["description"] or i["title"], probability=9, impact=9,
                recommended_action=i["recommendation"] or "Escalate immediately to the responsible team.",
            ))
        elif i["priority"] == "High":
            risks.append(_risk(
                f"incident_high_{i['id']}", "Incident", "High",
                f"High-priority incident open: {i['title']}",
                i["description"] or i["title"], probability=7, impact=7,
                recommended_action=i["recommendation"] or "Assign an owner and resolve promptly.",
            ))
        if i["due_date"] and i["due_date"] < today:
            risks.append(_risk(
                f"incident_overdue_{i['id']}", "Incident", "High",
                f"Incident overdue: {i['title']}",
                f"Due date {i['due_date']} has passed and the incident is still open.",
                probability=7, impact=6,
                recommended_action="Escalate to the assigned owner or reassign.",
            ))

    stats = inc.get_dashboard_stats()
    if stats["total_incidents"] and stats["open_incidents"] >= 3:
        risks.append(_risk(
            "high_open_incident_count", "Incident", "Medium",
            "Elevated number of unresolved incidents",
            f"{stats['open_incidents']} incidents are currently open/in progress.",
            probability=6, impact=5,
            recommended_action="Review the Incident Management board and reassign stalled incidents.",
        ))
    return risks


def detect_alert_risks():
    risks = []
    counts = alerts.get_alert_counts()
    if counts.get("total", 0) >= 8:
        risks.append(_risk(
            "excessive_alerts", "Operations", "Medium",
            "High volume of active operational alerts",
            f"{counts['total']} active alerts ({counts.get('Critical',0)} critical, "
            f"{counts.get('High',0)} high) may indicate systemic operational strain.",
            probability=5, impact=5,
            recommended_action="Triage the Alerts Center and resolve or dismiss stale alerts.",
        ))
    return risks


def get_all_risks(refresh_db_log=True):
    """Run every detector and return a combined, sorted risk register."""
    risks = (
        detect_venue_risks() + detect_speaker_risks() + detect_registration_risks() +
        detect_sponsorship_risks() + detect_incident_risks() + detect_alert_risks()
    )
    risks.sort(key=lambda r: (SEVERITY_ORDER.get(r["severity"], 4), -r["risk_score"]))

    if refresh_db_log:
        _log_risks(risks)

    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for r in risks:
        counts[r["severity"]] = counts.get(r["severity"], 0) + 1

    overall = "Low"
    if counts["Critical"]:
        overall = "Critical"
    elif counts["High"]:
        overall = "High"
    elif counts["Medium"]:
        overall = "Medium"

    return {
        "risks": risks,
        "counts": counts,
        "total": len(risks),
        "overall_risk_level": overall,
    }


def _log_risks(risks):
    """Best-effort persistence of the latest risk scan for auditability."""
    try:
        for r in risks[:25]:
            existing = db.query_one(
                "SELECT id FROM risk_register WHERE risk_key = ? AND status = 'Open' ORDER BY id DESC LIMIT 1",
                (r["risk_key"],),
            )
            if existing:
                continue
            db.execute(
                """INSERT INTO risk_register
                   (risk_key, module, severity, title, description, probability, impact,
                    risk_score, recommended_action, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (r["risk_key"], r["module"], r["severity"], r["title"], r["description"],
                 r["probability"], r["impact"], r["risk_score"], r["recommended_action"], "Open"),
            )
    except Exception as e:
        print("[risk_engine.py] Risk log skipped:", e)
