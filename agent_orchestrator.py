"""
agent_orchestrator.py
-----------------------
MILESTONE 4 — Agent Orchestration Layer.

Wraps every existing Milestone 1-3 "agent" (Venue Agent, Speaker Agent,
Sponsorship Agent, Incident Agent, Registration Intelligence) plus the new
Milestone 4 agents (Event Intelligence Agent, Risk Agent, Executive
Decision Agent) behind one orchestrator that:

  1. Receives a request/problem (free text or a quick-action key)
  2. Classifies which agents are relevant
  3. Actually invokes those agents against the REAL database
  4. Collects + combines their outputs
  5. Flags conflicts/risks
  6. Produces a final recommendation with reasoning
  7. Logs the full execution (agent_execution_log / decision_log)

All logic is deterministic/rule-based. No external LLM/API calls are made
even if the request looks conversational — this is documented, not hidden,
per the project's Milestone 4 requirements.
"""

import re
import time
import uuid
import json
from datetime import datetime

import database as db
import ai_model
import operations as ops
import sponsorship as spx
import incidents as inc
import alerts
import event_intelligence as ei
import risk_engine as risk


# =================================================================
# INDIVIDUAL AGENT WRAPPERS
# Each wrapper: (agent_name, purpose, run(context) -> dict)
# =================================================================
class Agent:
    def __init__(self, name, purpose):
        self.name = name
        self.purpose = purpose

    def run(self, context):
        raise NotImplementedError


class RegistrationIntelligenceAgent(Agent):
    def __init__(self):
        super().__init__("Registration Intelligence Agent",
                          "Analyzes registration volume, categories and demographic mix.")

    def run(self, context):
        users = db.query_all("SELECT * FROM users")
        if not users:
            return _agent_result(self.name, "No registration data available yet.", confidence=0, data={})
        insights = ai_model.generate_organizer_insights(users)
        summary = f"{len(users)} registrations tracked. Top category: {insights['top_categories'][0][0] if insights['top_categories'] else 'N/A'}."
        return _agent_result(self.name, summary, confidence=90 if len(users) >= 15 else 60, data=insights)


class AttendancePredictionAgent(Agent):
    def __init__(self):
        super().__init__("Attendance Prediction Agent",
                          "Forecasts expected attendance % and identifies no-show risk.")

    def run(self, context):
        users = db.query_all("SELECT * FROM users")
        if not users:
            return _agent_result(self.name, "No registrations yet — cannot forecast attendance.", confidence=0, data={})
        pred = ai_model.predict_attendance_percentage(users)
        no_shows = ai_model.predict_no_shows(users)
        high_risk = sum(1 for n in no_shows if n["risk_level"] == "High")
        summary = f"Predicted attendance: {pred['predicted_percentage']}% ({pred['confidence']} confidence). {high_risk} high no-show-risk registrant(s)."
        return _agent_result(self.name, summary, confidence=pred["predicted_percentage"], data={"prediction": pred, "high_risk_no_shows": high_risk})


class VenueAgent(Agent):
    def __init__(self):
        super().__init__("Venue Agent", "Recommends venues based on capacity, facilities and availability.")

    def run(self, context):
        requirements = context.get("venue_requirements") or {}
        attendees = requirements.get("attendees")
        if not attendees:
            # Fall back to expected attendance from the intelligence snapshot if available
            attendees = context.get("expected_attendance", 0)
        results = ops.recommend_venues({
            "attendees": attendees,
            "facilities": requirements.get("facilities", []),
            "session_date": requirements.get("session_date", ""),
            "start_time": requirements.get("start_time", ""),
            "end_time": requirements.get("end_time", ""),
        })
        qualified = [r for r in results if not r["disqualified"]]
        if not results:
            return _agent_result(self.name, "No venues configured yet.", confidence=0, data={})
        if qualified:
            best = qualified[0]
            summary = f"Best match: '{best['venue']['name']}' (capacity {best['venue']['capacity']}, score {best['score']}/100)."
            return _agent_result(self.name, summary, confidence=min(95, best["score"]),
                                  data={"recommended_venue": best["venue"]["name"], "score": best["score"],
                                        "reasons": best["reasons_pass"]})
        else:
            top = results[0]
            summary = f"No fully qualified venue found. Closest option '{top['venue']['name']}' has issues: {'; '.join(top['reasons_fail'])}"
            return _agent_result(self.name, summary, confidence=20, data={"issues": top["reasons_fail"]})


class SpeakerAgent(Agent):
    def __init__(self):
        super().__init__("Speaker Agent", "Recommends speakers based on expertise match and availability.")

    def run(self, context):
        requirements = context.get("speaker_requirements") or {}
        results = ops.recommend_speakers({
            "topic": requirements.get("topic", ""),
            "session_type": requirements.get("session_type", ""),
            "session_date": requirements.get("session_date", ""),
            "start_time": requirements.get("start_time", ""),
            "end_time": requirements.get("end_time", ""),
        })
        if not results:
            return _agent_result(self.name, "No speakers configured yet.", confidence=0, data={})
        qualified = [r for r in results if not r.get("disqualified")]
        if qualified:
            best = qualified[0]
            summary = f"Best match: '{best['speaker']['name']}' (score {best['score']}/100)."
            return _agent_result(self.name, summary, confidence=min(95, best["score"]),
                                  data={"recommended_speaker": best["speaker"]["name"], "score": best["score"]})
        summary = "No fully available speaker found for the given constraints."
        return _agent_result(self.name, summary, confidence=20, data={})


class SchedulingAgent(Agent):
    def __init__(self):
        super().__init__("Scheduling Agent", "Checks for venue/speaker scheduling conflicts and session allocation gaps.")

    def run(self, context):
        analytics = ops.generate_operations_analytics()
        gap = analytics["total_sessions"] - analytics["successful_allocations"]
        summary = (f"{analytics['total_sessions']} session(s) total, {gap} missing a venue/speaker. "
                    f"{analytics['total_conflicts_prevented']} conflict(s) logged historically.")
        confidence = 90 if gap == 0 else max(30, 90 - gap * 15)
        return _agent_result(self.name, summary, confidence=confidence, data=analytics)


class SponsorshipAgent(Agent):
    def __init__(self):
        super().__init__("Sponsorship Agent", "Tracks sponsor pipeline health, conversion and follow-ups.")

    def run(self, context):
        perf = spx.get_performance_stats()
        if not perf["total_sponsors"]:
            return _agent_result(self.name, "No sponsors in the pipeline yet.", confidence=0, data={})
        overdue = len(spx.get_followup_buckets()["overdue"])
        summary = (f"{perf['confirmed']}/{perf['total_sponsors']} confirmed ({perf['conversion_rate']}% conversion). "
                    f"{overdue} follow-up(s) overdue. ₹{perf['amount_committed']:,.0f} committed.")
        return _agent_result(self.name, summary, confidence=perf["conversion_rate"], data=perf)


class IncidentAgent(Agent):
    def __init__(self):
        super().__init__("Incident Agent", "Assesses open incidents, severity and recommended actions.")

    def run(self, context):
        stats = inc.get_dashboard_stats()
        summary = (f"{stats['open_incidents']} open incident(s), {stats['critical']} critical, "
                    f"{stats['overdue']} overdue.")
        confidence = 90 if stats["critical"] == 0 and stats["overdue"] == 0 else max(20, 90 - (stats["critical"] * 25 + stats["overdue"] * 10))
        return _agent_result(self.name, summary, confidence=max(0, confidence), data=stats)


class AlertAgent(Agent):
    def __init__(self):
        super().__init__("Alert Agent", "Summarizes active operational alerts by severity.")

    def run(self, context):
        counts = alerts.get_alert_counts()
        summary = f"{counts.get('total', 0)} active alert(s): {counts.get('Critical', 0)} critical, {counts.get('High', 0)} high."
        confidence = 90 if counts.get("total", 0) == 0 else max(20, 90 - counts.get("total", 0) * 8)
        return _agent_result(self.name, summary, confidence=max(0, confidence), data=counts)


class EventIntelligenceAgent(Agent):
    def __init__(self):
        super().__init__("Event Intelligence Agent", "Calculates the overall Event Health & Readiness scores.")

    def run(self, context):
        snapshot = context.get("intelligence_snapshot") or ei.analyze_event()
        summary = (f"Event Health {snapshot['health_score']}/100 ({snapshot['health_label']}), "
                    f"Readiness {snapshot['readiness_score']}/100.")
        return _agent_result(self.name, summary, confidence=snapshot["health_score"], data=snapshot["totals"])


class RiskAgent(Agent):
    def __init__(self):
        super().__init__("Risk Agent", "Scans all modules for operational, scheduling, sponsorship and incident risks.")

    def run(self, context):
        register = risk.get_all_risks()
        summary = f"{register['total']} risk(s) detected. Overall risk level: {register['overall_risk_level']}."
        confidence = {"Low": 90, "Medium": 65, "High": 35, "Critical": 15}.get(register["overall_risk_level"], 50)
        return _agent_result(self.name, summary, confidence=confidence, data={"overall_risk_level": register["overall_risk_level"],
                                                                                 "counts": register["counts"],
                                                                                 "top_risks": register["risks"][:5]})


class ExecutiveDecisionAgent(Agent):
    def __init__(self):
        super().__init__("Executive Decision Agent", "Synthesizes all agent outputs into one final recommendation.")

    def run(self, context):
        agent_outputs = context.get("agent_outputs", [])
        risk_output = next((a for a in agent_outputs if a["agent"] == "Risk Agent"), None)
        overall_risk = risk_output["data"].get("overall_risk_level", "Low") if risk_output else "Low"
        confidences = [a["confidence"] for a in agent_outputs if a["agent"] != self.name]
        avg_confidence = round(sum(confidences) / len(confidences)) if confidences else 50
        summary = (f"Based on {len(agent_outputs)} agent(s) consulted, overall risk level is "
                    f"{overall_risk} with an average agent confidence of {avg_confidence}%.")
        return _agent_result(self.name, summary, confidence=avg_confidence, data={"overall_risk_level": overall_risk})


def _agent_result(agent_name, summary, confidence, data):
    return {"agent": agent_name, "summary": summary, "confidence": max(0, min(100, round(confidence))), "data": data}


# =================================================================
# AGENT REGISTRY
# =================================================================
AGENTS = {
    "registration": RegistrationIntelligenceAgent(),
    "attendance": AttendancePredictionAgent(),
    "venue": VenueAgent(),
    "speaker": SpeakerAgent(),
    "scheduling": SchedulingAgent(),
    "sponsorship": SponsorshipAgent(),
    "incident": IncidentAgent(),
    "alert": AlertAgent(),
    "intelligence": EventIntelligenceAgent(),
    "risk": RiskAgent(),
    "decision": ExecutiveDecisionAgent(),
}

ALL_AGENT_KEYS = list(AGENTS.keys())


# =================================================================
# PROBLEM CLASSIFICATION (keyword-based routing — deterministic)
# =================================================================
def classify_problem(problem_text):
    """Determine which agents are relevant to a free-text problem/question.
    Simple deterministic keyword routing — documented as rule-based, not an
    external LLM classifier."""
    text = (problem_text or "").lower()
    selected = set()

    keyword_map = {
        "registration": ["registration", "register", "attendee count", "sign up"],
        "attendance": ["attendance", "no-show", "no show", "turnout", "forecast"],
        "venue": ["venue", "room", "hall", "capacity", "auditorium", "location"],
        "speaker": ["speaker", "presenter", "keynote", "expert"],
        "scheduling": ["schedule", "conflict", "overlap", "session", "slot", "time"],
        "sponsorship": ["sponsor", "sponsorship", "funding", "budget", "revenue"],
        "incident": ["incident", "issue", "problem", "disruption", "malfunction"],
        "alert": ["alert", "notification", "warning"],
        "risk": ["risk", "danger", "concern", "threat"],
        "intelligence": ["health", "ready", "readiness", "overall", "summary", "status"],
    }

    for key, words in keyword_map.items():
        if any(w in text for w in words):
            selected.add(key)

    # If nothing matched, run a broad default set so the orchestrator is
    # always useful even for vague questions.
    if not selected:
        selected = {"intelligence", "risk", "attendance", "venue", "incident"}

    # Decision agent always synthesizes at the end.
    selected.add("decision")
    return selected


QUICK_ACTIONS = {
    "analyze_event_health": {"agents": {"intelligence", "risk", "decision"}, "label": "Analyze Event Health"},
    "analyze_attendance": {"agents": {"registration", "attendance", "decision"}, "label": "Analyze Attendance"},
    "find_venue": {"agents": {"venue", "scheduling", "decision"}, "label": "Find Venue"},
    "find_speaker": {"agents": {"speaker", "scheduling", "decision"}, "label": "Find Speaker"},
    "check_schedule": {"agents": {"scheduling", "venue", "speaker", "decision"}, "label": "Check Schedule"},
    "analyze_sponsorship": {"agents": {"sponsorship", "risk", "decision"}, "label": "Analyze Sponsorship"},
    "analyze_incidents": {"agents": {"incident", "alert", "risk", "decision"}, "label": "Analyze Incidents"},
    "generate_executive_summary": {"agents": {"intelligence", "risk", "sponsorship", "incident", "decision"},
                                    "label": "Generate Executive Summary"},
}


# =================================================================
# ORCHESTRATION CORE
# =================================================================
def run_orchestration(problem_text=None, quick_action=None, context_extra=None, user="System"):
    """
    Real orchestration: classify -> invoke agents -> combine -> risk-check ->
    synthesize a final recommendation -> log the execution.
    """
    execution_id = str(uuid.uuid4())[:8]
    start = time.time()
    started_at = datetime.now()

    if quick_action and quick_action in QUICK_ACTIONS:
        agent_keys = set(QUICK_ACTIONS[quick_action]["agents"])
        problem_text = problem_text or QUICK_ACTIONS[quick_action]["label"]
    else:
        agent_keys = classify_problem(problem_text)

    context = dict(context_extra or {})
    context["intelligence_snapshot"] = ei.analyze_event()
    context["expected_attendance"] = context["intelligence_snapshot"]["totals"]["expected_attendance_count"]

    # Lightweight extraction: if the free-text problem mentions an explicit
    # attendee number (e.g. "expected to be 500"), prefer that over the
    # intelligence snapshot's forecast when running the Venue Agent.
    if problem_text:
        numbers = re.findall(r"\b(\d{2,5})\b", problem_text)
        if numbers and "venue" in agent_keys:
            context.setdefault("venue_requirements", {})
            context["venue_requirements"]["attendees"] = int(numbers[0])

    agent_outputs = []
    error = None
    try:
        # Run every agent except the decision agent first, then synthesize.
        for key in agent_keys:
            if key == "decision":
                continue
            agent = AGENTS.get(key)
            if not agent:
                continue
            result = agent.run(context)
            agent_outputs.append(result)

        context["agent_outputs"] = agent_outputs
        decision_result = AGENTS["decision"].run(context)
        agent_outputs.append(decision_result)
        status = "Completed"
    except Exception as e:
        error = str(e)
        status = "Failed"

    duration_ms = round((time.time() - start) * 1000)
    ended_at = datetime.now()

    # Determine risk level + recommendation + reasoning from collected outputs
    risk_output = next((a for a in agent_outputs if a["agent"] == "Risk Agent"), None)
    risk_level = risk_output["data"].get("overall_risk_level", "Low") if risk_output else "Low"

    recommendation, reasoning, action = _build_recommendation(problem_text, agent_outputs, risk_level, context)

    result_payload = {
        "execution_id": execution_id,
        "problem": problem_text,
        "agents_consulted": [a["agent"] for a in agent_outputs],
        "agent_outputs": agent_outputs,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "action": action,
        "status": status,
        "error": error,
        "duration_ms": duration_ms,
        "started_at": started_at.isoformat(timespec="seconds"),
        "ended_at": ended_at.isoformat(timespec="seconds"),
    }

    _log_execution(execution_id, problem_text, agent_outputs, status, duration_ms, error, started_at, ended_at)
    _log_decision(execution_id, problem_text, agent_outputs, risk_level, recommendation, reasoning, action, user)

    return result_payload


def _build_recommendation(problem_text, agent_outputs, risk_level, context):
    """Synthesize a final human-readable recommendation from every agent's
    output — this is the 'Executive Decision Agent' logic surfaced for the UI."""
    reasons = [f"{a['agent']}: {a['summary']}" for a in agent_outputs if a["agent"] != "Executive Decision Agent"]

    venue_out = next((a for a in agent_outputs if a["agent"] == "Venue Agent"), None)
    incident_out = next((a for a in agent_outputs if a["agent"] == "Incident Agent"), None)
    risk_out = next((a for a in agent_outputs if a["agent"] == "Risk Agent"), None)
    sponsor_out = next((a for a in agent_outputs if a["agent"] == "Sponsorship Agent"), None)
    intel_out = next((a for a in agent_outputs if a["agent"] == "Event Intelligence Agent"), None)

    if venue_out and venue_out["data"].get("recommended_venue"):
        recommendation = f"Proceed with venue '{venue_out['data']['recommended_venue']}'."
    elif venue_out and venue_out["data"].get("issues"):
        recommendation = "Do not use the top-scoring venue as-is — resolve the flagged capacity/availability issue first."
    elif incident_out and incident_out["data"].get("critical"):
        recommendation = "Resolve all critical incidents before proceeding — they pose the highest risk to the event."
    elif risk_level == "Critical":
        recommendation = "Immediate action required — one or more critical risks were detected across the event."
    elif risk_level == "High":
        recommendation = "Address the highest-severity risks this week to avoid event disruption."
    elif intel_out:
        recommendation = f"Event is on track (Health {intel_out['data'].get('expected_attendance_pct', 'N/A')}%). Continue monitoring."
    else:
        recommendation = "No immediate action required based on current data."

    reasoning = " ".join(reasons) if reasons else "No agent data was available for this request."

    action_map = {
        "Critical": "Escalate to the event organizer immediately.",
        "High": "Assign an owner and resolve within 24 hours.",
        "Medium": "Schedule a review within the next planning cycle.",
        "Low": "No action required — continue routine monitoring.",
    }
    action = action_map.get(risk_level, "Review the details and decide next steps.")

    return recommendation, reasoning, action


def _log_execution(execution_id, request_text, agent_outputs, status, duration_ms, error, started_at, ended_at):
    try:
        avg_conf = round(sum(a["confidence"] for a in agent_outputs) / len(agent_outputs)) if agent_outputs else None
        for a in agent_outputs:
            db.execute(
                """INSERT INTO agent_execution_log
                   (execution_id, agent_name, request_text, started_at, ended_at, duration_ms,
                    status, result_summary, confidence, error)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (execution_id, a["agent"], request_text, started_at.isoformat(timespec="seconds"),
                 ended_at.isoformat(timespec="seconds"), duration_ms, status, a["summary"],
                 a["confidence"], error),
            )
    except Exception as e:
        print("[agent_orchestrator.py] Execution log skipped:", e)


def _log_decision(execution_id, question, agent_outputs, risk_level, recommendation, reasoning, action, user):
    try:
        db.execute(
            """INSERT INTO decision_log
               (execution_id, question, agents_consulted, risk_level, recommendation, reasoning, action, created_by)
               VALUES (?,?,?,?,?,?,?,?)""",
            (execution_id, question, json.dumps([a["agent"] for a in agent_outputs]),
             risk_level, recommendation, reasoning, action, user),
        )
    except Exception as e:
        print("[agent_orchestrator.py] Decision log skipped:", e)


def get_execution_history(limit=30):
    rows = db.query_all(
        "SELECT * FROM agent_execution_log ORDER BY id DESC LIMIT ?", (limit,)
    )
    return rows


def get_decision_history(limit=20):
    rows = db.query_all(
        "SELECT * FROM decision_log ORDER BY id DESC LIMIT ?", (limit,)
    )
    return rows
