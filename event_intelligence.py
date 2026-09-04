"""
event_intelligence.py
----------------------
MILESTONE 4 — Event Intelligence Engine.

Centralized intelligence layer that combines REAL data already produced by
the existing Milestone 1-3 modules (ai_model, operations, sponsorship,
incidents, alerts) into a single, explainable picture of overall event
health, readiness and risk.

No external ML frameworks or LLM APIs are required. Every number here is
either pulled directly from the database or derived through transparent,
documented arithmetic so the scoring can be shown to a reviewer/mentor.

If there isn't enough data yet for a given calculation, the engine returns
"No data available yet" / None instead of inventing numbers.
"""

from datetime import datetime, date
from collections import Counter

import database as db
import ai_model
import operations as ops
import sponsorship as spx
import incidents as inc
import alerts

# =================================================================
# SCORING WEIGHTS (must sum to 100) — shown to users via "Why this score?"
# =================================================================
HEALTH_WEIGHTS = {
    "attendance": 20,
    "registration": 15,
    "venue_readiness": 15,
    "speaker_readiness": 10,
    "schedule_health": 10,
    "sponsorship": 10,
    "incident_status": 10,
    "operational_alerts": 10,
}


def _label_for_score(score):
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Healthy"
    if score >= 50:
        return "Attention Required"
    return "Critical"


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


# =================================================================
# COMPONENT SCORES — each returns (score 0-100, explanation string)
# =================================================================
def _score_attendance(users):
    if not users:
        return 0, "No registrations yet — attendance cannot be forecast."
    pred = ai_model.predict_attendance_percentage(users)
    pct = pred["predicted_percentage"]
    return round(pct), f"AI-predicted attendance of {pct}% ({pred['confidence']} confidence)."


def _score_registration(users, events):
    if not users:
        return 0, "No registrations recorded yet."
    trend = ai_model.get_registration_trend(users, days=7)
    data = trend["data"]
    total = len(users)
    # Capacity utilization across configured events (Milestone 1 'events' table)
    total_capacity = sum(e.get("capacity") or 0 for e in events) or 0
    capacity_score = _clamp(round((total / total_capacity) * 100)) if total_capacity else 50

    # Momentum: are the last 3 days >= the previous 4 days on average?
    if len(data) >= 7:
        recent = sum(data[-3:])
        earlier = sum(data[:4]) or 1
        momentum_ratio = recent / earlier if earlier else 1
        momentum_score = _clamp(round(50 + (momentum_ratio - 1) * 50))
    else:
        momentum_score = 50

    score = round((capacity_score * 0.6) + (momentum_score * 0.4))
    explanation = (
        f"{total} total registrations against ~{total_capacity or 'unspecified'} combined event capacity; "
        f"recent 3-day registration momentum factored in."
    )
    return _clamp(score), explanation


def _score_venue_readiness(ops_analytics):
    total_venues = ops_analytics["total_venues"]
    if not total_venues:
        return 0, "No venues configured yet."
    maintenance_ratio = ops_analytics["maintenance_venues"] / total_venues
    util = ops_analytics["venue_utilization_pct"]
    # Reward healthy utilization (neither idle nor overbooked), penalize maintenance load
    util_score = 100 - abs(util - 60)  # 60% utilization treated as the sweet spot
    score = _clamp(round((util_score * 0.7) + ((1 - maintenance_ratio) * 100 * 0.3)))
    explanation = (
        f"{ops_analytics['available_venues']}/{total_venues} venues available, "
        f"{util}% venue utilization, {ops_analytics['maintenance_venues']} under maintenance."
    )
    return score, explanation


def _score_speaker_readiness(ops_analytics):
    total_speakers = ops_analytics["total_speakers"]
    if not total_speakers:
        return 0, "No speakers onboarded yet."
    util = ops_analytics["speaker_utilization_pct"]
    score = _clamp(round(util))
    explanation = (
        f"{ops_analytics['assigned_speakers']}/{total_speakers} speakers assigned to sessions "
        f"({util}% speaker utilization)."
    )
    return score, explanation


def _score_schedule_health(ops_analytics):
    total_sessions = ops_analytics["total_sessions"]
    if not total_sessions:
        return 0, "No sessions scheduled yet."
    conflicts = ops_analytics["total_conflicts_prevented"]
    allocation_ratio = ops_analytics["successful_allocations"] / total_sessions
    conflict_penalty = min(40, conflicts * 5)
    score = _clamp(round(allocation_ratio * 100 - conflict_penalty))
    explanation = (
        f"{ops_analytics['successful_allocations']}/{total_sessions} sessions fully allocated "
        f"(venue + speaker); {conflicts} conflicts logged historically."
    )
    return score, explanation


def _score_sponsorship(perf):
    if not perf["total_sponsors"]:
        return 0, "No sponsors in the pipeline yet."
    conv = perf["conversion_rate"]
    resp = perf["response_rate"]
    committed_ratio = 0
    if perf["amount_requested"]:
        committed_ratio = _clamp(round((perf["amount_committed"] / perf["amount_requested"]) * 100))
    score = _clamp(round((conv * 0.4) + (resp * 0.3) + (committed_ratio * 0.3)))
    explanation = (
        f"{perf['confirmed']}/{perf['total_sponsors']} sponsors confirmed "
        f"({conv}% conversion), {resp}% outreach response rate, "
        f"₹{perf['amount_committed']:,.0f} committed of ₹{perf['amount_requested']:,.0f} requested."
    )
    return score, explanation


def _score_incident_status(inc_stats):
    if inc_stats["total_incidents"] == 0:
        return 100, "No incidents reported — nothing negatively impacting event health."
    critical_penalty = inc_stats["critical"] * 25
    high_penalty = inc_stats["high_priority"] * 10
    overdue_penalty = inc_stats["overdue"] * 15
    resolved_ratio = inc_stats["resolved"] / inc_stats["total_incidents"]
    score = _clamp(round((resolved_ratio * 100) - critical_penalty - high_penalty - overdue_penalty))
    explanation = (
        f"{inc_stats['open_incidents']} open incident(s), {inc_stats['critical']} critical, "
        f"{inc_stats['overdue']} overdue, {inc_stats['resolved']} resolved of {inc_stats['total_incidents']} total."
    )
    return score, explanation


def _score_operational_alerts(alert_counts):
    total = alert_counts.get("total", 0)
    if total == 0:
        return 100, "No active operational alerts."
    penalty = (alert_counts.get("Critical", 0) * 30 + alert_counts.get("High", 0) * 15 +
               alert_counts.get("Warning", 0) * 7 + alert_counts.get("Info", 0) * 2)
    score = _clamp(100 - penalty)
    explanation = (
        f"{total} active alert(s): {alert_counts.get('Critical', 0)} critical, "
        f"{alert_counts.get('High', 0)} high, {alert_counts.get('Warning', 0)} warning, "
        f"{alert_counts.get('Info', 0)} info."
    )
    return score, explanation


# =================================================================
# MAIN ENGINE ENTRY POINT
# =================================================================
def analyze_event():
    """
    Runs the full Event Intelligence analysis against REAL current database
    state and returns one structured payload used by every Milestone 4
    surface (Executive Dashboard, Event Intelligence page, APIs, PDF/CSV
    reports, Decision Support, Agent Orchestration).
    """
    users = db.query_all("SELECT * FROM users")
    events = db.query_all("SELECT * FROM events")
    ops_analytics = ops.generate_operations_analytics()
    perf = spx.get_performance_stats()
    inc_stats = inc.get_dashboard_stats()
    alert_counts = alerts.get_alert_counts()

    components = {}
    for key, fn, args in [
        ("attendance", _score_attendance, (users,)),
        ("registration", _score_registration, (users, events)),
        ("venue_readiness", _score_venue_readiness, (ops_analytics,)),
        ("speaker_readiness", _score_speaker_readiness, (ops_analytics,)),
        ("schedule_health", _score_schedule_health, (ops_analytics,)),
        ("sponsorship", _score_sponsorship, (perf,)),
        ("incident_status", _score_incident_status, (inc_stats,)),
        ("operational_alerts", _score_operational_alerts, (alert_counts,)),
    ]:
        score, explanation = fn(*args)
        components[key] = {
            "score": score,
            "weight": HEALTH_WEIGHTS[key],
            "weighted_contribution": round(score * HEALTH_WEIGHTS[key] / 100, 1),
            "explanation": explanation,
        }

    health_score = round(sum(c["weighted_contribution"] for c in components.values()))
    health_score = _clamp(health_score)
    health_label = _label_for_score(health_score)

    readiness_score = _compute_readiness(users, ops_analytics, perf, inc_stats)

    no_shows = ai_model.predict_no_shows(users) if users else []
    high_risk_no_shows = sum(1 for n in no_shows if n["risk_level"] == "High")

    attendance_pred = ai_model.predict_attendance_percentage(users)
    trend = ai_model.get_registration_trend(users, days=7)

    recommendations = generate_recommendations(
        users, events, ops_analytics, perf, inc_stats, alert_counts, components
    )

    key_risks = _extract_key_risks(ops_analytics, perf, inc_stats, alert_counts)

    executive_summary = _build_executive_summary(
        users, health_score, health_label, readiness_score, attendance_pred,
        ops_analytics, perf, inc_stats, alert_counts,
    )

    snapshot = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "health_score": health_score,
        "health_label": health_label,
        "readiness_score": readiness_score,
        "components": components,
        "totals": {
            "total_registrations": len(users),
            "total_events": len(events),
            "expected_attendance_pct": attendance_pred["predicted_percentage"],
            "expected_attendance_count": round(len(users) * attendance_pred["predicted_percentage"] / 100) if users else 0,
            "checked_in": db.query_one("SELECT COUNT(*) as c FROM users WHERE checked_in = 1")["c"],
            "checkin_pct": round((db.query_one("SELECT COUNT(*) as c FROM users WHERE checked_in = 1")["c"] / len(users)) * 100, 1) if users else 0,
            "no_show_high_risk": high_risk_no_shows,
            "venue_utilization_pct": ops_analytics["venue_utilization_pct"],
            "speaker_utilization_pct": ops_analytics["speaker_utilization_pct"],
            "sponsorship_confirmed": perf["confirmed"],
            "sponsorship_amount_committed": perf["amount_committed"],
            "open_incidents": inc_stats["open_incidents"],
            "critical_incidents": inc_stats["critical"],
            "active_alerts": alert_counts.get("total", 0),
        },
        "registration_trend": trend,
        "recommendations": recommendations,
        "key_risks": key_risks,
        "executive_summary": executive_summary,
        "has_data": bool(users) or bool(ops_analytics["total_venues"]) or bool(perf["total_sponsors"]),
    }

    # Persist a snapshot for the Event Health Trend chart / audit trail
    _save_snapshot(snapshot)

    return snapshot


def _compute_readiness(users, ops_analytics, perf, inc_stats):
    """Event Readiness Score: are the operational building blocks in place
    (regardless of how 'healthy' current numbers look)?"""
    checks = []
    checks.append(1 if users else 0)
    checks.append(1 if ops_analytics["total_venues"] else 0)
    checks.append(1 if ops_analytics["total_speakers"] else 0)
    checks.append(1 if ops_analytics["total_sessions"] else 0)
    checks.append(1 if ops_analytics["successful_allocations"] == ops_analytics["total_sessions"] and ops_analytics["total_sessions"] else 0)
    checks.append(1 if perf["total_sponsors"] else 0)
    checks.append(1 if inc_stats["critical"] == 0 else 0)
    checks.append(1 if inc_stats["overdue"] == 0 else 0)
    return round(sum(checks) / len(checks) * 100)


def generate_recommendations(users, events, ops_analytics, perf, inc_stats, alert_counts, components):
    """Data-driven, prioritized recommendations. Every recommendation cites
    the real numbers that triggered it — never hard-coded/fake content."""
    recs = []

    # Attendance vs capacity
    if users and ops_analytics["total_venues"]:
        attendance_pred = ai_model.predict_attendance_percentage(users)
        expected = round(len(users) * attendance_pred["predicted_percentage"] / 100)
        largest_venue = db.query_one("SELECT MAX(capacity) as c FROM venues")
        max_cap = (largest_venue or {}).get("c") or 0
        if max_cap and expected > max_cap:
            over_pct = round(((expected - max_cap) / max_cap) * 100, 1)
            recs.append({
                "priority": "High",
                "area": "Venue",
                "text": (f"Expected attendance ({expected}) is {over_pct}% higher than your largest venue's "
                         f"capacity ({max_cap}). Consider reallocating high-demand sessions to a larger venue."),
            })

    # Sponsor follow-ups overdue
    overdue_followups = len(spx.get_followup_buckets()["overdue"])
    if overdue_followups:
        recs.append({
            "priority": "High" if overdue_followups >= 3 else "Medium",
            "area": "Sponsorship",
            "text": (f"{overdue_followups} sponsor follow-up(s) are overdue. Prioritize the highest-scoring "
                     f"sponsors first to protect the sponsorship pipeline."),
        })

    # Critical incidents
    if inc_stats["critical"]:
        recs.append({
            "priority": "Critical",
            "area": "Incidents",
            "text": (f"{inc_stats['critical']} critical incident(s) remain in the system. "
                     f"Immediate action is recommended to prevent event disruption."),
        })

    # Speaker utilization
    if ops_analytics["total_speakers"] and ops_analytics["speaker_utilization_pct"] < 50:
        recs.append({
            "priority": "Medium",
            "area": "Speakers",
            "text": (f"Speaker utilization is {ops_analytics['speaker_utilization_pct']}% "
                     f"({ops_analytics['assigned_speakers']}/{ops_analytics['total_speakers']} assigned). "
                     f"Consider reallocating available speakers to unfilled session slots."),
        })

    # Registration momentum
    if users:
        trend = ai_model.get_registration_trend(users, days=7)
        data = trend["data"]
        if len(data) >= 7 and sum(data[-3:]) < sum(data[:3]):
            recs.append({
                "priority": "Medium",
                "area": "Registration",
                "text": "Registration growth has slowed over the last 3 days compared to earlier in the week. "
                        "Consider a renewed promotion push.",
            })

    # Venue conflicts
    if ops_analytics["total_conflicts_prevented"] > 0:
        recs.append({
            "priority": "Low",
            "area": "Scheduling",
            "text": (f"{ops_analytics['total_conflicts_prevented']} scheduling conflict(s) have been detected "
                     f"historically ({ops_analytics['venue_conflicts_prevented']} venue, "
                     f"{ops_analytics['speaker_conflicts_prevented']} speaker). Review the Smart Scheduler "
                     f"before finalizing remaining sessions."),
        })

    # Operational alerts
    if alert_counts.get("Critical", 0) or alert_counts.get("High", 0):
        recs.append({
            "priority": "High",
            "area": "Operations",
            "text": (f"{alert_counts.get('Critical', 0) + alert_counts.get('High', 0)} high/critical "
                     f"operational alert(s) are active. Review the Alerts Center to resolve them."),
        })

    if not recs:
        if not users and not ops_analytics["total_venues"] and not perf["total_sponsors"]:
            recs.append({
                "priority": "Info", "area": "General",
                "text": "No data available yet. Recommendations will appear automatically once "
                        "registrations, venues, speakers or sponsors are added.",
            })
        else:
            recs.append({
                "priority": "Info", "area": "General",
                "text": "No urgent issues detected right now. Event indicators are within healthy ranges.",
            })

    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
    recs.sort(key=lambda r: order.get(r["priority"], 5))
    return recs[:8]


def _extract_key_risks(ops_analytics, perf, inc_stats, alert_counts):
    risks = []
    if inc_stats["critical"]:
        risks.append(f"{inc_stats['critical']} critical incident(s) open")
    if inc_stats["overdue"]:
        risks.append(f"{inc_stats['overdue']} incident(s) overdue past their due date")
    if alert_counts.get("Critical", 0):
        risks.append(f"{alert_counts['Critical']} critical operational alert(s) active")
    overdue_followups = len(spx.get_followup_buckets()["overdue"])
    if overdue_followups:
        risks.append(f"{overdue_followups} sponsor follow-up(s) overdue")
    if ops_analytics["maintenance_venues"]:
        risks.append(f"{ops_analytics['maintenance_venues']} venue(s) under maintenance")
    if ops_analytics["total_sessions"] and ops_analytics["successful_allocations"] < ops_analytics["total_sessions"]:
        gap = ops_analytics["total_sessions"] - ops_analytics["successful_allocations"]
        risks.append(f"{gap} session(s) missing a venue or speaker assignment")
    if not risks:
        risks.append("No significant risks detected at this time.")
    return risks[:5]


def _build_executive_summary(users, health_score, health_label, readiness_score,
                              attendance_pred, ops_analytics, perf, inc_stats, alert_counts):
    if not users and not ops_analytics["total_venues"] and not perf["total_sponsors"]:
        return ("No data available yet. Add registrations, venues, speakers or sponsors to generate "
                "an AI-powered executive summary of event health.")

    total = len(users)
    summary = (
        f"Overall Event Health is {health_score}/100 ({health_label}), with an Event Readiness "
        f"Score of {readiness_score}/100. {total} attendee(s) are registered with an AI-predicted "
        f"attendance rate of {attendance_pred['predicted_percentage']}% ({attendance_pred['confidence']} confidence). "
        f"Venue utilization stands at {ops_analytics['venue_utilization_pct']}% and speaker utilization at "
        f"{ops_analytics['speaker_utilization_pct']}%. The sponsorship pipeline has "
        f"{perf['confirmed']} confirmed sponsor(s) out of {perf['total_sponsors']} tracked, with "
        f"₹{perf['amount_committed']:,.0f} committed. There "
        f"{'are ' + str(inc_stats['open_incidents']) + ' open incident(s)' if inc_stats['open_incidents'] else 'are no open incidents'}"
        f"{', including ' + str(inc_stats['critical']) + ' marked Critical' if inc_stats['critical'] else ''}, "
        f"and {alert_counts.get('total', 0)} active operational alert(s) requiring attention."
    )
    return summary


def _save_snapshot(snapshot):
    """Persist a lightweight snapshot row for the Event Health Trend chart.
    Best-effort — failures here must never break the dashboard."""
    try:
        import json
        db.execute(
            "INSERT INTO event_intelligence (health_score, health_label, readiness_score, snapshot_json) "
            "VALUES (?,?,?,?)",
            (snapshot["health_score"], snapshot["health_label"], snapshot["readiness_score"],
             json.dumps({"totals": snapshot["totals"]})),
        )
    except Exception as e:
        print("[event_intelligence.py] Snapshot save skipped:", e)


def get_health_trend(limit=20):
    """Historical Event Health Score points for the 'Event Health Trend' chart."""
    rows = db.query_all(
        "SELECT health_score, generated_at FROM event_intelligence ORDER BY id DESC LIMIT ?", (limit,)
    )
    rows.reverse()
    if not rows:
        return {"labels": [], "data": []}
    return {
        "labels": [r["generated_at"][11:16] if len(r["generated_at"]) > 11 else r["generated_at"] for r in rows],
        "data": [r["health_score"] for r in rows],
    }
