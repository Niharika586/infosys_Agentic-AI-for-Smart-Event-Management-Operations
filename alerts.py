"""
alerts.py
----------
Operational Alerts engine for Milestone 3.

A small, dependency-free module that centralizes how alerts get raised,
de-duplicated and queried. Both sponsorship.py and incidents.py (and
operations.py, if desired) call raise_alert() to surface meaningful
conditions; this module never imports them back, avoiding circular imports.

Severity levels: Info / Warning / High / Critical.
"""

import database as db

SEVERITIES = ["Info", "Warning", "High", "Critical"]


def raise_alert(title, description, severity, module, related_entity_type=None, related_entity_id=None):
    """
    Insert a new operational alert unless an unresolved alert with the same
    title + related entity already exists (keeps refresh calls idempotent
    so re-visiting a dashboard doesn't spam duplicate alerts).
    """
    existing = db.query_one(
        """SELECT id FROM operational_alerts
           WHERE title = ? AND related_entity_type IS ? AND related_entity_id IS ? AND is_resolved = 0""",
        (title, related_entity_type, related_entity_id),
    )
    if existing:
        return existing["id"]

    return db.execute(
        """INSERT INTO operational_alerts
           (title, description, severity, module, related_entity_type, related_entity_id)
           VALUES (?,?,?,?,?,?)""",
        (title, description, severity, module, related_entity_type, related_entity_id),
    )


def get_alerts(module=None, severity=None, unread_only=False, unresolved_only=True):
    sql = "SELECT * FROM operational_alerts WHERE 1=1"
    params = []
    if module:
        sql += " AND module = ?"
        params.append(module)
    if severity:
        sql += " AND severity = ?"
        params.append(severity)
    if unread_only:
        sql += " AND is_read = 0"
    if unresolved_only:
        sql += " AND is_resolved = 0"
    sql += " ORDER BY CASE severity WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Warning' THEN 2 ELSE 3 END, created_at DESC"
    return db.query_all(sql, params)


def get_alert_counts():
    rows = db.query_all("SELECT severity, COUNT(*) as c FROM operational_alerts WHERE is_resolved = 0 GROUP BY severity")
    counts = {sev: 0 for sev in SEVERITIES}
    for r in rows:
        counts[r["severity"]] = r["c"]
    counts["total"] = sum(counts.values())
    counts["unread"] = db.query_one(
        "SELECT COUNT(*) as c FROM operational_alerts WHERE is_read = 0 AND is_resolved = 0"
    )["c"]
    return counts


def mark_read(alert_id):
    db.execute("UPDATE operational_alerts SET is_read = 1 WHERE id = ?", (alert_id,))


def mark_all_read():
    db.execute("UPDATE operational_alerts SET is_read = 1 WHERE is_resolved = 0")


def dismiss_alert(alert_id):
    db.execute("UPDATE operational_alerts SET is_resolved = 1, is_read = 1 WHERE id = ?", (alert_id,))
