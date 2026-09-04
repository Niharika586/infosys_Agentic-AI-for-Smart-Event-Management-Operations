"""
sponsorship.py
----------------
Sponsorship Agent engine for Milestone 3
(AI-Powered Event Management System — Sponsorship & Incident Management).

This module implements:
  1. Sponsor Discovery / Search   — searchable, filterable sponsor directory
  2. The Sponsorship Agent        — rule-based suitability scoring & recommendation
  3. Outreach message generation  — professional, ready-to-copy proposal drafts
  4. Communication / follow-up tracking helpers
  5. Sponsor performance analytics

Exactly like ai_model.py (Milestone 1) and operations.py (Milestone 2), no
external ML frameworks are used. Every recommendation is produced by
transparent, explainable scoring logic so the reasoning behind each
suggestion can be shown to the user.
"""

from collections import Counter
from datetime import datetime, date

import database as db
import alerts

# =================================================================
# CONSTANTS
# =================================================================
INDUSTRIES = [
    "Technology", "Education", "Finance", "Healthcare", "Food & Beverage",
    "Retail", "Automotive", "Media", "Telecommunications", "Startups", "Other",
]

SPONSORSHIP_CATEGORIES = [
    "Title Sponsor", "Platinum Sponsor", "Gold Sponsor", "Silver Sponsor",
    "Bronze Sponsor", "In-Kind Sponsor", "Media Partner",
]

BUDGET_LEVELS = ["Low", "Medium", "High", "Very High"]

SPONSOR_STATUSES = [
    "Discovered", "Potential", "Shortlisted", "Ready to Contact", "Contacted",
    "Proposal Sent", "Awaiting Response", "Interested", "Follow-up Required",
    "Negotiating", "Confirmed", "Rejected", "Inactive",
]

COMMUNICATION_METHODS = ["Email", "Phone", "LinkedIn", "Meeting", "Website Contact Form", "Other"]

INTERACTION_TYPES = [
    "Discovery", "Evaluation", "Outreach", "Response", "Follow-Up",
    "Negotiation", "Confirmation", "Rejection", "Note",
]

OPPORTUNITY_STATUSES = ["Proposed", "Negotiating", "Confirmed", "Rejected"]

# Rule-based industry relevance weighting for a technology/AI-focused
# event audience (students, developers, AI professionals). Used only for
# transparent scoring — organizers can still approach any sponsor.
INDUSTRY_RELEVANCE = {
    "technology": 35, "telecommunications": 30, "startups": 33, "education": 26,
    "media": 22, "finance": 18, "food & beverage": 16, "retail": 14,
    "automotive": 14, "healthcare": 12, "other": 10,
}

# Default event profile used for outreach message generation and scoring
# context. Reuses the flagship Milestone 1 event as the reference event.
EVENT_PROFILE = {
    "name": "AI & ML Summit 2026",
    "description": "A technology summit bringing together students, developers and "
                    "industry professionals for a deep dive into modern AI and Machine Learning practices.",
    "target_audience": "students, developers, AI/ML professionals and startup founders",
    "expected_participants": 300,
}


# =================================================================
# SMALL HELPERS
# =================================================================
def parse_csv_field(value):
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _budget_score(level):
    return {"Low": 5, "Medium": 12, "High": 20, "Very High": 25}.get(level, 8)


def _match_category_for_score(score):
    if score >= 80:
        return "Excellent Match"
    if score >= 60:
        return "Good Match"
    if score >= 40:
        return "Moderate Match"
    return "Low Match"


# =================================================================
# SPONSORSHIP AGENT — SUITABILITY SCORING
# =================================================================
def score_sponsor(sponsor):
    """
    Sponsorship Agent: analyzes a sponsor record against the event profile
    using transparent, explainable rule-based scoring.

    Factors considered:
      - Industry relevance to the event         (up to 35 pts)
      - Audience compatibility (keyword overlap) (up to 20 pts)
      - Budget potential                         (up to 25 pts)
      - Previous sponsorship history             (up to 10 pts)
      - Strategic relevance (sponsorship category)(up to 10 pts)

    Returns (score:int 0-100, match_category:str, explanation:str, reasons:list[str])
    """
    reasons = []
    score = 0

    industry = (sponsor.get("industry") or "").strip().lower()
    industry_pts = INDUSTRY_RELEVANCE.get(industry, INDUSTRY_RELEVANCE["other"])
    score += industry_pts
    if industry_pts >= 26:
        reasons.append(f"{sponsor.get('industry') or 'Industry'} is highly relevant to an AI/technology event")
    elif industry_pts >= 16:
        reasons.append(f"{sponsor.get('industry') or 'Industry'} has moderate relevance to the event theme")
    else:
        reasons.append(f"{sponsor.get('industry') or 'Industry'} has limited direct relevance to the event theme")

    # Audience compatibility — keyword overlap between sponsor's target
    # audience/keywords and the event's target audience description.
    audience_text = f"{sponsor.get('target_audience') or ''} {sponsor.get('keywords') or ''}".lower()
    event_words = set(w.strip(",.") for w in EVENT_PROFILE["target_audience"].lower().split())
    sponsor_words = set(w.strip(",.") for w in audience_text.replace(",", " ").split())
    overlap = event_words & sponsor_words
    audience_pts = min(20, len(overlap) * 7)
    score += audience_pts
    if overlap:
        reasons.append(f"Target audience overlaps on: {', '.join(sorted(overlap))}")
    else:
        reasons.append("Limited overlap between sponsor's stated audience and the event audience")

    # Budget potential
    budget_pts = _budget_score(sponsor.get("budget_potential"))
    score += budget_pts
    reasons.append(f"Budget potential rated {sponsor.get('budget_potential') or 'unspecified'}")

    # Previous sponsorship history — bonus if a prior confirmed opportunity exists
    prior_confirmed = db.query_one(
        "SELECT COUNT(*) as c FROM sponsorship_opportunities WHERE sponsor_id = ? AND status = 'Confirmed'",
        (sponsor["id"],),
    )
    history_pts = 10 if prior_confirmed and prior_confirmed["c"] > 0 else 0
    score += history_pts
    if history_pts:
        reasons.append("Has a confirmed sponsorship history with this event")

    # Strategic relevance — higher-tier sponsorship categories score slightly higher
    category = (sponsor.get("sponsorship_category") or "").strip()
    tier_pts = {"Title Sponsor": 10, "Platinum Sponsor": 9, "Gold Sponsor": 7,
                "Silver Sponsor": 5, "Bronze Sponsor": 3, "Media Partner": 6,
                "In-Kind Sponsor": 2}.get(category, 3)
    score += tier_pts

    score = max(0, min(100, score))
    match_category = _match_category_for_score(score)

    explanation = (
        f"Recommended because {(sponsor.get('industry') or 'this company').lower()}'s industry "
        f"{'closely matches' if industry_pts >= 26 else ('has some relevance to' if industry_pts >= 16 else 'has limited relevance to')} "
        f"the {EVENT_PROFILE['name']}, "
        f"{'its target audience aligns with expected attendees' if overlap else 'its target audience shows limited overlap with expected attendees'}, "
        f"and it has {(sponsor.get('budget_potential') or 'unspecified').lower()} sponsorship budget potential."
    )

    return score, match_category, explanation, reasons


def evaluate_and_save_score(sponsor_id):
    """Run the Sponsorship Agent on one sponsor and persist the result."""
    sponsor = db.query_one("SELECT * FROM sponsors WHERE id = ?", (sponsor_id,))
    if not sponsor:
        return None
    score, match_category, explanation, reasons = score_sponsor(sponsor)
    db.execute(
        "UPDATE sponsors SET suitability_score = ?, match_category = ?, score_explanation = ? WHERE id = ?",
        (score, match_category, explanation, sponsor_id),
    )
    log_interaction(sponsor_id, "Evaluation", "System", "Suitability score generated",
                     f"Sponsorship Agent scored this sponsor {score}% — {match_category}.")
    return {"score": score, "match_category": match_category, "explanation": explanation, "reasons": reasons}


# =================================================================
# SPONSOR DISCOVERY / SEARCH
# =================================================================
def search_sponsors(filters):
    """
    Powers the Find Sponsors / Sponsor Management pages: full-text search,
    multi-criteria filtering (industry/location/category/budget/status/
    keyword), and sorting including suitability score.

    filters = { q, industry, location, category, budget, status, sort }
    """
    q = (filters.get("q") or "").strip().lower()
    industry = (filters.get("industry") or "").strip()
    location = (filters.get("location") or "").strip()
    category = (filters.get("category") or "").strip()
    budget = (filters.get("budget") or "").strip()
    status = (filters.get("status") or "").strip()
    sort = (filters.get("sort") or "score_desc").strip()

    sponsors = db.query_all("SELECT * FROM sponsors ORDER BY company_name ASC")
    results = []
    for s in sponsors:
        haystack = f"{s['company_name']} {s['industry']} {s['location']} {s['keywords']} {s['target_audience']}".lower()
        if q and q not in haystack:
            continue
        if industry and industry.lower() != (s["industry"] or "").lower():
            continue
        if location and location.lower() != (s["location"] or "").lower():
            continue
        if category and category.lower() != (s["sponsorship_category"] or "").lower():
            continue
        if budget and budget.lower() != (s["budget_potential"] or "").lower():
            continue
        if status and status.lower() != (s["status"] or "").lower():
            continue
        results.append(s)

    if sort == "score_desc":
        results.sort(key=lambda r: -(r["suitability_score"] or 0))
    elif sort == "score_asc":
        results.sort(key=lambda r: (r["suitability_score"] or 0))
    elif sort == "name":
        results.sort(key=lambda r: r["company_name"].lower())
    elif sort == "budget_desc":
        results.sort(key=lambda r: -(r["estimated_budget"] or 0))
    elif sort == "recent":
        results.sort(key=lambda r: r["created_at"], reverse=True)

    return results


# =================================================================
# COMMUNICATION / INTERACTION TRACKING
# =================================================================
def log_interaction(sponsor_id, interaction_type, communication_method, subject,
                     message="", sponsor_response=None, next_action=None,
                     follow_up_date=None, created_by="Event Organizer"):
    db.execute(
        """INSERT INTO sponsor_interactions
           (sponsor_id, interaction_type, communication_method, subject, message,
            sponsor_response, next_action, follow_up_date, created_by)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (sponsor_id, interaction_type, communication_method, subject, message,
         sponsor_response, next_action, follow_up_date, created_by),
    )


def get_sponsor_timeline(sponsor_id):
    return db.query_all(
        "SELECT * FROM sponsor_interactions WHERE sponsor_id = ? ORDER BY created_at ASC",
        (sponsor_id,),
    )


def generate_outreach_message(sponsor, contact_person=None, package=None,
                               amount=None, benefits=None, event_profile=None):
    """
    Sponsorship Proposal / Outreach Message Generator. Produces a
    professional, ready-to-copy message the organizer can send through
    their own preferred communication channel (email/LinkedIn/etc).
    No message is actually sent by the system — this is intentional and
    matches the documented workflow: Generate -> Copy -> Organizer Sends
    -> Record Communication.
    """
    ep = event_profile or EVENT_PROFILE
    contact = contact_person or sponsor.get("contact_person") or "Hiring/Partnerships Team"
    package = package or sponsor.get("sponsorship_category") or "Sponsorship Package"
    benefits = benefits or "brand visibility across event materials, a booth at the venue, and mentions across our promotional channels"
    amount_line = f" with a proposed contribution of ₹{int(amount):,}" if amount else ""

    message = f"""Subject: Sponsorship Opportunity — {ep['name']}

Dear {contact},

I hope this message finds you well. I'm reaching out on behalf of the organizing committee of {ep['name']}, {ep['description']}

We expect around {ep['expected_participants']} attendees, primarily {ep['target_audience']}, and we believe {sponsor.get('company_name', 'your organization')}'s work in {sponsor.get('industry', 'your industry')} would resonate strongly with this audience.

We would love to invite {sponsor.get('company_name', 'your organization')} to join us as a {package}{amount_line}. This package includes {benefits}.

Would you be available for a short call this week to discuss how we can tailor this partnership to your goals? I'm happy to share a detailed sponsorship deck as well.

Looking forward to hearing from you.

Warm regards,
Event Organizer
{ep['name']} Organizing Committee"""
    return message


# =================================================================
# FOLLOW-UP MANAGEMENT
# =================================================================
def schedule_followup(sponsor_id, due_date, reason):
    return db.execute(
        "INSERT INTO sponsor_followups (sponsor_id, due_date, reason) VALUES (?,?,?)",
        (sponsor_id, due_date, reason),
    )


def get_followup_buckets():
    """Return follow-ups grouped into Due Today / Overdue / Upcoming, plus
    a list of sponsors currently marked 'Awaiting Response'."""
    today = date.today().isoformat()
    rows = db.query_all(
        """SELECT f.*, s.company_name, s.contact_person, s.contact_email, s.status as sponsor_status
           FROM sponsor_followups f JOIN sponsors s ON f.sponsor_id = s.id
           WHERE f.status = 'Pending' ORDER BY f.due_date ASC"""
    )
    due_today, overdue, upcoming = [], [], []
    for r in rows:
        if r["due_date"] < today:
            overdue.append(r)
        elif r["due_date"] == today:
            due_today.append(r)
        else:
            upcoming.append(r)

    awaiting_response = db.query_all(
        "SELECT * FROM sponsors WHERE status IN ('Awaiting Response','Proposal Sent') ORDER BY created_at DESC"
    )
    return {
        "due_today": due_today, "overdue": overdue, "upcoming": upcoming,
        "awaiting_response": awaiting_response,
    }


def complete_followup(followup_id):
    db.execute(
        "UPDATE sponsor_followups SET status = 'Completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (followup_id,),
    )


# =================================================================
# PERFORMANCE TRACKING
# =================================================================
def get_performance_stats():
    sponsors = db.query_all("SELECT * FROM sponsors")
    opportunities = db.query_all("SELECT * FROM sponsorship_opportunities")
    followups = db.query_all("SELECT * FROM sponsor_followups WHERE status = 'Pending'")
    interactions = db.query_all("SELECT * FROM sponsor_interactions")

    status_counter = Counter(s["status"] for s in sponsors)
    total = len(sponsors)

    discovered = sum(status_counter.get(s, 0) for s in ["Discovered", "Potential"])
    shortlisted = status_counter.get("Shortlisted", 0) + status_counter.get("Ready to Contact", 0)
    contacted = sum(status_counter.get(s, 0) for s in
                     ["Contacted", "Proposal Sent", "Awaiting Response", "Interested",
                      "Follow-up Required", "Negotiating", "Confirmed", "Rejected"])
    awaiting_response = status_counter.get("Awaiting Response", 0) + status_counter.get("Proposal Sent", 0)
    interested = status_counter.get("Interested", 0)
    confirmed = status_counter.get("Confirmed", 0)
    rejected = status_counter.get("Rejected", 0)

    outreach_sent = sum(1 for i in interactions if i["interaction_type"] == "Outreach")
    responses_received = sum(1 for i in interactions if i["interaction_type"] == "Response")
    response_rate = round((responses_received / outreach_sent) * 100, 1) if outreach_sent else 0.0
    conversion_rate = round((confirmed / total) * 100, 1) if total else 0.0

    amount_requested = sum(o["amount_requested"] or 0 for o in opportunities)
    amount_committed = sum(o["amount_committed"] or 0 for o in opportunities)
    amount_received = sum(o["amount_received"] or 0 for o in opportunities)
    amount_pending = max(0, amount_committed - amount_received)

    by_industry = Counter(s["industry"] for s in sponsors if s["industry"])
    by_status = {st: status_counter.get(st, 0) for st in SPONSOR_STATUSES if status_counter.get(st, 0)}

    amount_by_status = Counter()
    for o in opportunities:
        amount_by_status[o["status"]] += (o["amount_committed"] or o["amount_requested"] or 0)

    return {
        "total_sponsors": total,
        "discovered": discovered,
        "shortlisted": shortlisted,
        "contacted": contacted,
        "awaiting_response": awaiting_response,
        "interested": interested,
        "confirmed": confirmed,
        "rejected": rejected,
        "followups_due": len(followups),
        "response_rate": response_rate,
        "conversion_rate": conversion_rate,
        "amount_requested": amount_requested,
        "amount_committed": amount_committed,
        "amount_received": amount_received,
        "amount_pending": amount_pending,
        "charts": {
            "status_distribution": {"labels": list(by_status.keys()), "data": list(by_status.values())},
            "by_industry": {"labels": list(by_industry.keys()), "data": list(by_industry.values())},
            "response_rate": {"labels": ["Responded", "No Response Yet"],
                               "data": [responses_received, max(0, outreach_sent - responses_received)]},
            "amount_by_status": {"labels": list(amount_by_status.keys()), "data": list(amount_by_status.values())},
        },
    }


# =================================================================
# OPERATIONAL ALERTS — SPONSORSHIP
# =================================================================
def refresh_sponsorship_alerts():
    """Scan sponsor/follow-up state and raise operational alerts for
    meaningful conditions. Idempotent — will not duplicate an unresolved
    alert already raised for the same sponsor + title."""
    today = date.today().isoformat()

    overdue = db.query_all(
        """SELECT f.*, s.company_name FROM sponsor_followups f JOIN sponsors s ON f.sponsor_id = s.id
           WHERE f.status = 'Pending' AND f.due_date < ?""", (today,)
    )
    for f in overdue:
        alerts.raise_alert(
            title="Sponsor follow-up overdue",
            description=f"Follow-up for {f['company_name']} was due on {f['due_date']} and has not been completed.",
            severity="Warning", module="Sponsorship",
            related_entity_type="sponsor", related_entity_id=f["sponsor_id"],
        )

    due_today = db.query_all(
        """SELECT f.*, s.company_name FROM sponsor_followups f JOIN sponsors s ON f.sponsor_id = s.id
           WHERE f.status = 'Pending' AND f.due_date = ?""", (today,)
    )
    for f in due_today:
        alerts.raise_alert(
            title="Follow-up due today",
            description=f"A scheduled follow-up with {f['company_name']} is due today.",
            severity="Info", module="Sponsorship",
            related_entity_type="sponsor", related_entity_id=f["sponsor_id"],
        )

    awaiting = db.query_all("SELECT * FROM sponsors WHERE status IN ('Proposal Sent','Awaiting Response')")
    for s in awaiting:
        alerts.raise_alert(
            title="Sponsor awaiting response",
            description=f"{s['company_name']} has not yet responded to outreach.",
            severity="Info", module="Sponsorship",
            related_entity_type="sponsor", related_entity_id=s["id"],
        )

    confirmed_needing_action = db.query_all(
        """SELECT o.*, s.company_name FROM sponsorship_opportunities o JOIN sponsors s ON o.sponsor_id = s.id
           WHERE o.status = 'Confirmed' AND (o.amount_committed - o.amount_received) > 0"""
    )
    for o in confirmed_needing_action:
        pending_amt = (o["amount_committed"] or 0) - (o["amount_received"] or 0)
        alerts.raise_alert(
            title="Confirmed sponsor requires action",
            description=f"{o['company_name']} has ₹{pending_amt:,.0f} of committed sponsorship still pending receipt.",
            severity="Warning", module="Sponsorship",
            related_entity_type="sponsor", related_entity_id=o["sponsor_id"],
        )
