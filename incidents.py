"""
incidents.py
-------------
Incident Agent engine for Milestone 3
(AI-Powered Event Management System — Sponsorship & Incident Management).

This module implements:
  1. Incident logging, categorization and priority workflows
  2. The Incident Agent — rule-based, explainable action recommendations
  3. Incident dashboard statistics
  4. Operational alert generation for critical/overdue incidents

Exactly like operations.py's Venue/Speaker Agents, recommendations are
produced by transparent, category+priority based rules — no external ML
frameworks are used — so the reasoning can always be explained to a reviewer.
"""

from datetime import date, datetime

import database as db
import alerts

# =================================================================
# CONSTANTS
# =================================================================
CATEGORIES = [
    "Technical", "Venue", "Speaker", "Session", "Registration", "Attendance",
    "Sponsorship", "Security", "Operational", "Participant", "Other",
]

PRIORITIES = ["Low", "Medium", "High", "Critical"]

STATUSES = ["Reported", "Assigned", "In Progress", "Resolved", "Verified", "Closed"]

OPEN_STATUSES = ["Reported", "Assigned", "In Progress"]

# Suggested starting priority per category — organizers can always override
# this on the Report Incident form; it's a starting recommendation only.
SUGGESTED_PRIORITY = {
    "Security": "Critical",
    "Technical": "High",
    "Venue": "High",
    "Speaker": "Medium",
    "Session": "Medium",
    "Sponsorship": "Low",
    "Registration": "Medium",
    "Attendance": "Low",
    "Operational": "Medium",
    "Participant": "Medium",
    "Other": "Low",
}


def suggest_priority(category):
    return SUGGESTED_PRIORITY.get(category, "Medium")


# =================================================================
# INCIDENT AGENT — ACTION RECOMMENDATIONS
# =================================================================
def recommend_action(category, priority, description=""):
    """
    Incident Agent: returns an explainable, rule-based recommendation for
    how to respond to an incident, connecting back to existing Milestone 2
    modules (Venue Agent, Speaker Agent, Smart Scheduler) wherever relevant.
    """
    desc = (description or "").lower()
    urgent_prefix = ""
    if priority in ("Critical", "High"):
        urgent_prefix = "Immediately notify the event organizer and relevant team. "

    if category == "Venue":
        return (urgent_prefix +
                "Reassign the affected session to an available suitable venue if possible — "
                "check the Venue Agent for alternatives matching capacity and facility requirements.")
    if category == "Speaker":
        return (urgent_prefix +
                "Check the Speaker Agent for alternative speakers with matching expertise and availability, "
                "or adjust the session schedule to absorb any delay.")
    if category == "Session":
        return (urgent_prefix +
                "Use the existing Smart Scheduler and conflict detection system to identify alternative "
                "time slots or venues for the affected session.")
    if category == "Sponsorship":
        return ("Review the sponsor's communication history and assign a follow-up action to the "
                "sponsorship team; consider an alternate outreach channel if email has had no response.")
    if category == "Technical":
        if "wifi" in desc or "wi-fi" in desc or "network" in desc:
            return (urgent_prefix + "Notify the venue manager and IT support to check network/access point "
                                     "load, and consider capping non-essential device connections in the hall.")
        return (urgent_prefix + "Notify IT support to investigate the technical fault and arrange backup "
                                 "equipment if the issue affects an in-progress or upcoming session.")
    if category == "Registration":
        return ("Open an additional check-in counter and direct volunteers to help attendees pre-load "
                "their Registration ID/QR code to speed up scanning.")
    if category == "Attendance":
        return ("Cross-check with the QR check-in system and AI Analytics attendance prediction to confirm "
                "the scale of the issue before reallocating volunteers.")
    if category == "Security":
        return (urgent_prefix + "Alert on-site security personnel and the venue manager immediately; "
                                 "restrict access to the affected area until the situation is contained.")
    if category == "Participant":
        return ("Have a volunteer coordinator or organizer directly assist the participant and log the "
                "outcome; escalate to the organizer if the issue affects their ability to attend sessions.")
    return (urgent_prefix + "Assign a responsible person to investigate and log updates as the "
                             "situation develops.")


# =================================================================
# INCIDENT WORKFLOW
# =================================================================
def create_incident(data):
    incident_id = db.execute(
        """INSERT INTO incidents
           (title, description, category, priority, status, related_venue_id, related_session_id,
            related_speaker_id, related_sponsor_id, reported_by, assigned_to, due_date, recommendation)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data["title"], data.get("description", ""), data["category"], data["priority"],
         "Assigned" if data.get("assigned_to") else "Reported",
         data.get("related_venue_id"), data.get("related_session_id"),
         data.get("related_speaker_id"), data.get("related_sponsor_id"),
         data.get("reported_by", "Event Organizer"), data.get("assigned_to"),
         data.get("due_date"), data.get("recommendation", "")),
    )
    log_update(incident_id, "Incident reported.", "Reported", data.get("reported_by", "Event Organizer"))
    if data.get("assigned_to"):
        log_update(incident_id, f"Assigned to {data['assigned_to']}.", "Assigned", data.get("reported_by", "Event Organizer"))
    return incident_id


def log_update(incident_id, update_text, status_change=None, updated_by="Event Organizer"):
    db.execute(
        "INSERT INTO incident_updates (incident_id, update_text, status_change, updated_by) VALUES (?,?,?,?)",
        (incident_id, update_text, status_change, updated_by),
    )
    if status_change:
        resolved_at = "CURRENT_TIMESTAMP" if status_change in ("Resolved", "Closed") else None
        if resolved_at:
            db.execute(
                "UPDATE incidents SET status = ?, resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status_change, incident_id),
            )
        else:
            db.execute("UPDATE incidents SET status = ? WHERE id = ?", (status_change, incident_id))


def get_incident_timeline(incident_id):
    return db.query_all(
        "SELECT * FROM incident_updates WHERE incident_id = ? ORDER BY created_at ASC", (incident_id,)
    )


def search_incidents(filters):
    q = (filters.get("q") or "").strip().lower()
    category = (filters.get("category") or "").strip()
    priority = (filters.get("priority") or "").strip()
    status = (filters.get("status") or "").strip()

    incidents = db.query_all("SELECT * FROM incidents ORDER BY created_at DESC")
    results = []
    for i in incidents:
        haystack = f"{i['title']} {i['description'] or ''} {i['category']}".lower()
        if q and q not in haystack:
            continue
        if category and category != i["category"]:
            continue
        if priority and priority != i["priority"]:
            continue
        if status and status != i["status"]:
            continue
        results.append(i)
    return results


def get_dashboard_stats():
    incidents = db.query_all("SELECT * FROM incidents")
    today = date.today().isoformat()

    total = len(incidents)
    open_count = sum(1 for i in incidents if i["status"] in OPEN_STATUSES)
    in_progress = sum(1 for i in incidents if i["status"] == "In Progress")
    high_priority = sum(1 for i in incidents if i["priority"] == "High")
    critical = sum(1 for i in incidents if i["priority"] == "Critical")
    resolved = sum(1 for i in incidents if i["status"] in ("Resolved", "Verified", "Closed"))
    overdue = sum(1 for i in incidents if i["status"] in OPEN_STATUSES and i["due_date"] and i["due_date"] < today)

    by_category = {}
    by_priority = {}
    for i in incidents:
        by_category[i["category"]] = by_category.get(i["category"], 0) + 1
        by_priority[i["priority"]] = by_priority.get(i["priority"], 0) + 1

    return {
        "total_incidents": total,
        "open_incidents": open_count,
        "in_progress": in_progress,
        "high_priority": high_priority,
        "critical": critical,
        "resolved": resolved,
        "overdue": overdue,
        "charts": {
            "by_category": {"labels": list(by_category.keys()), "data": list(by_category.values())},
            "by_priority": {"labels": list(by_priority.keys()), "data": list(by_priority.values())},
        },
    }


# =================================================================
# OPERATIONAL ALERTS — INCIDENTS
# =================================================================
def refresh_incident_alerts():
    """Scan incident state and raise operational alerts for meaningful
    conditions. Idempotent per incident via alerts.raise_alert()."""
    today = date.today().isoformat()
    incidents = db.query_all("SELECT * FROM incidents WHERE status IN ('Reported','Assigned','In Progress')")

    for i in incidents:
        if i["priority"] == "Critical":
            alerts.raise_alert(
                title=f"Critical incident reported: {i['title']}",
                description="A critical-priority incident requires immediate attention.",
                severity="Critical", module="Incident",
                related_entity_type="incident", related_entity_id=i["id"],
            )
        elif i["priority"] == "High":
            alerts.raise_alert(
                title=f"High-priority incident open: {i['title']}",
                description="A high-priority incident is still open.",
                severity="High", module="Incident",
                related_entity_type="incident", related_entity_id=i["id"],
            )

        if not i["assigned_to"]:
            alerts.raise_alert(
                title="Incident not assigned",
                description=f"'{i['title']}' has not been assigned to a responsible person.",
                severity="Warning", module="Incident",
                related_entity_type="incident", related_entity_id=i["id"],
            )

        if i["due_date"] and i["due_date"] < today:
            alerts.raise_alert(
                title="Incident overdue",
                description=f"'{i['title']}' passed its due date of {i['due_date']} and is still open.",
                severity="High", module="Incident",
                related_entity_type="incident", related_entity_id=i["id"],
            )
