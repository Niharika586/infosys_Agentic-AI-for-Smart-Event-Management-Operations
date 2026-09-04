"""
operations.py
--------------
Venue & Speaker Operations engine for Milestone 2
(AI-Powered Event Management System — Venue & Speaker Operations).

This module implements:
  1. Conflict detection (venue double-booking / speaker double-booking)
  2. The Venue Agent  — rule-based recommendation engine for venue allocation
  3. The Speaker Agent — rule-based recommendation engine for speaker assignment
  4. Session Analytics — utilization, conflict and allocation statistics

Exactly like ai_model.py (Milestone 1), no external ML frameworks are used.
Every recommendation is produced by transparent, explainable scoring logic
so the reasoning behind each suggestion can be shown to the user — this is
what is meant by "AI-agent-like behaviour" in the milestone brief.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta

import database as db

# =================================================================
# CONSTANTS
# =================================================================
FACILITIES_LIST = [
    "Projector", "Smart Board", "Microphone", "Speakers", "Wi-Fi",
    "Air Conditioning", "Recording Equipment", "Video Conferencing", "Stage",
]

ROOM_TYPES = [
    "Auditorium", "Seminar Hall", "Conference Room", "Computer Lab",
    "Workshop Hall", "Classroom", "Outdoor Arena",
]

SESSION_TYPES = [
    "Keynote", "Workshop", "Technical Session", "Panel Discussion",
    "Presentation", "Networking", "Training",
]

SESSION_STATUSES = ["Upcoming", "Scheduled", "Completed", "Cancelled"]

VENUE_STATUSES = ["Available", "Maintenance"]


# =================================================================
# TIME HELPERS
# =================================================================
def _to_time(value):
    """Parse an 'HH:MM' string into a comparable datetime.time object."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        return None


def time_ranges_overlap(start_a, end_a, start_b, end_b):
    """True if [start_a, end_a) overlaps [start_b, end_b)."""
    sa, ea, sb, eb = _to_time(start_a), _to_time(end_a), _to_time(start_b), _to_time(end_b)
    if not all([sa, ea, sb, eb]):
        return False
    return sa < eb and sb < ea


def duration_minutes(start_time, end_time):
    sa, ea = _to_time(start_time), _to_time(end_time)
    if not sa or not ea:
        return 0
    today = datetime.today()
    dt_a = datetime.combine(today, sa)
    dt_b = datetime.combine(today, ea)
    return max(0, int((dt_b - dt_a).total_seconds() // 60))


def parse_csv_field(value):
    """Split a comma-separated stored field into a clean list."""
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


# =================================================================
# CONFLICT LOGGING
# =================================================================
def log_conflict(conflict_type, message):
    db.execute(
        "INSERT INTO conflict_log (conflict_type, message) VALUES (?, ?)",
        (conflict_type, message),
    )


# =================================================================
# CONFLICT DETECTION
# =================================================================
def find_venue_conflict(venue_id, session_date, start_time, end_time, exclude_session_id=None):
    """Return the conflicting session row if the venue is already booked
    for an overlapping time window on the given date, else None."""
    if not venue_id:
        return None
    sessions = db.query_all(
        "SELECT * FROM sessions WHERE venue_id = ? AND session_date = ? AND status != 'Cancelled'",
        (venue_id, session_date),
    )
    for s in sessions:
        if exclude_session_id and s["id"] == exclude_session_id:
            continue
        if time_ranges_overlap(start_time, end_time, s["start_time"], s["end_time"]):
            return s
    return None


def find_speaker_conflict(speaker_id, session_date, start_time, end_time, exclude_session_id=None):
    """Return the conflicting session row if the speaker is already assigned
    to an overlapping session on the given date, else None."""
    if not speaker_id:
        return None
    sessions = db.query_all(
        "SELECT * FROM sessions WHERE speaker_id = ? AND session_date = ? AND status != 'Cancelled'",
        (speaker_id, session_date),
    )
    for s in sessions:
        if exclude_session_id and s["id"] == exclude_session_id:
            continue
        if time_ranges_overlap(start_time, end_time, s["start_time"], s["end_time"]):
            return s
    return None


def validate_session_slot(venue_id, speaker_id, session_date, start_time, end_time,
                           expected_attendees=None, required_facilities=None,
                           exclude_session_id=None):
    """
    Full validation pass used before creating/updating/confirming a session.
    Returns a list of human-readable error strings (empty list = valid).
    Also logs any detected conflicts into conflict_log for analytics.
    """
    errors = []

    if _to_time(start_time) is None or _to_time(end_time) is None:
        errors.append("Start time and end time must be valid (HH:MM).")
        return errors

    if _to_time(end_time) <= _to_time(start_time):
        errors.append("End time cannot be before or equal to start time.")
        return errors

    if venue_id:
        venue = db.query_one("SELECT * FROM venues WHERE id = ?", (venue_id,))
        if not venue:
            errors.append("Selected venue does not exist.")
        else:
            if venue["status"] == "Maintenance":
                errors.append(f"Venue '{venue['name']}' is currently under maintenance and unavailable.")

            if expected_attendees and int(expected_attendees) > venue["capacity"]:
                errors.append(
                    f"Expected attendees ({expected_attendees}) exceed the capacity of "
                    f"'{venue['name']}' ({venue['capacity']})."
                )

            if required_facilities:
                have = set(f.lower() for f in parse_csv_field(venue["facilities"]))
                need = set(f.lower() for f in required_facilities if f)
                missing = need - have
                if missing:
                    errors.append(
                        f"Venue '{venue['name']}' is missing required facilities: "
                        f"{', '.join(sorted(missing))}."
                    )

            conflict = find_venue_conflict(venue_id, session_date, start_time, end_time, exclude_session_id)
            if conflict:
                msg = (f"Scheduling Conflict: Venue '{venue['name']}' is already booked for "
                       f"'{conflict['title']}' ({conflict['start_time']}-{conflict['end_time']}) on {session_date}.")
                errors.append(msg)
                log_conflict("venue", msg)

    if speaker_id:
        speaker = db.query_one("SELECT * FROM speakers WHERE id = ?", (speaker_id,))
        if not speaker:
            errors.append("Selected speaker does not exist.")
        else:
            conflict = find_speaker_conflict(speaker_id, session_date, start_time, end_time, exclude_session_id)
            if conflict:
                msg = (f"Scheduling Conflict: Speaker '{speaker['name']}' is already assigned to "
                       f"'{conflict['title']}' ({conflict['start_time']}-{conflict['end_time']}) on {session_date}.")
                errors.append(msg)
                log_conflict("speaker", msg)

            available_dates = parse_csv_field(speaker.get("available_dates"))
            if available_dates and session_date not in available_dates:
                errors.append(
                    f"Speaker '{speaker['name']}' has not marked {session_date} as an available date."
                )

    return errors


# =================================================================
# VENUE AGENT
# =================================================================
def recommend_venues(requirements):
    """
    Venue Agent: scores every venue against the event/session requirements
    and returns a ranked list of recommendations with transparent reasoning.

    requirements = {
        attendees: int, facilities: [str], session_type: str,
        session_date: 'YYYY-MM-DD', start_time: 'HH:MM', end_time: 'HH:MM'
    }
    """
    attendees = int(requirements.get("attendees") or 0)
    needed_facilities = [f for f in (requirements.get("facilities") or []) if f]
    session_date = requirements.get("session_date") or ""
    start_time = requirements.get("start_time") or ""
    end_time = requirements.get("end_time") or ""

    venues = db.query_all("SELECT * FROM venues ORDER BY name ASC")
    results = []

    for v in venues:
        reasons_pass, reasons_fail = [], []
        score = 0
        disqualified = False

        if v["status"] == "Maintenance":
            disqualified = True
            reasons_fail.append("Venue is currently marked under maintenance")

        if v["capacity"] >= attendees:
            score += 35
            reasons_pass.append(f"Capacity matches attendee requirement ({v['capacity']} ≥ {attendees})")
        else:
            disqualified = True
            reasons_fail.append(f"Capacity too low ({v['capacity']} < {attendees} attendees)")

        have = set(f.lower() for f in parse_csv_field(v["facilities"]))
        need = set(f.lower() for f in needed_facilities)
        matched = need & have
        missing = need - have
        if need:
            facility_score = int(30 * (len(matched) / len(need))) if need else 30
            score += facility_score
            for f in needed_facilities:
                if f.lower() in matched:
                    reasons_pass.append(f"Required {f} available")
            if missing:
                reasons_fail.append(f"Missing facilities: {', '.join(sorted(missing))}")
        else:
            score += 10

        conflict = None
        if session_date and start_time and end_time:
            conflict = find_venue_conflict(v["id"], session_date, start_time, end_time)
        if conflict:
            disqualified = True
            reasons_fail.append(
                f"Conflict: already booked for '{conflict['title']}' "
                f"({conflict['start_time']}-{conflict['end_time']})"
            )
        elif session_date and start_time and end_time:
            score += 30
            reasons_pass.append("Venue available during requested date/time")
            reasons_pass.append("No scheduling conflict detected")

        status_label = "Conflict" if (conflict) else ("Maintenance" if v["status"] == "Maintenance" else "Available")

        results.append({
            "venue": v,
            "score": max(0, score),
            "disqualified": disqualified,
            "status_label": status_label,
            "reasons_pass": reasons_pass,
            "reasons_fail": reasons_fail,
        })

    # Rank: qualified venues first (by score desc), then disqualified (by score desc)
    results.sort(key=lambda r: (r["disqualified"], -r["score"]))
    if results:
        results[0]["recommended"] = not results[0]["disqualified"]
    for r in results[1:]:
        r["recommended"] = False

    return results


# =================================================================
# SPEAKER AGENT
# =================================================================
def _keyword_overlap_score(topic, expertise_text):
    if not topic or not expertise_text:
        return 0
    topic_words = set(w.strip(",.").lower() for w in topic.split() if len(w) > 2)
    expertise_words = set(w.strip(",.").lower() for w in expertise_text.replace(",", " ").split() if len(w) > 2)
    if not topic_words or not expertise_words:
        return 0
    overlap = topic_words & expertise_words
    return len(overlap), overlap


def recommend_speakers(requirements):
    """
    Speaker Agent: scores every speaker against session requirements
    (topic/expertise match, availability, conflicts) and returns a
    ranked list of recommendations with transparent reasoning.

    requirements = {
        topic: str, session_type: str,
        session_date: 'YYYY-MM-DD', start_time: 'HH:MM', end_time: 'HH:MM'
    }
    """
    topic = (requirements.get("topic") or "").strip()
    session_type = (requirements.get("session_type") or "").strip()
    session_date = requirements.get("session_date") or ""
    start_time = requirements.get("start_time") or ""
    end_time = requirements.get("end_time") or ""

    speakers = db.query_all("SELECT * FROM speakers ORDER BY name ASC")
    results = []

    for s in speakers:
        reasons_pass, reasons_fail = [], []
        score = 0
        disqualified = False

        overlap_count, overlap_words = _keyword_overlap_score(topic, s.get("expertise") or "")
        if topic:
            if overlap_count:
                score += min(40, overlap_count * 15)
                reasons_pass.append(
                    f"Expertise matches session topic ({', '.join(sorted(overlap_words))})"
                )
            else:
                reasons_fail.append("Expertise does not clearly match the session topic")
        else:
            score += 10

        if session_type and s.get("preferred_session_type"):
            if session_type.lower() == s["preferred_session_type"].lower():
                score += 15
                reasons_pass.append(f"Preferred session type matches ({session_type})")

        available_dates = parse_csv_field(s.get("available_dates"))
        if session_date:
            if available_dates and session_date not in available_dates:
                disqualified = True
                reasons_fail.append(f"Speaker not marked available on {session_date}")
            elif available_dates:
                score += 20
                reasons_pass.append(f"Available on requested date ({session_date})")

        conflict = None
        if session_date and start_time and end_time:
            conflict = find_speaker_conflict(s["id"], session_date, start_time, end_time)
        if conflict:
            disqualified = True
            reasons_fail.append(
                f"Conflict: already assigned to '{conflict['title']}' "
                f"({conflict['start_time']}-{conflict['end_time']})"
            )
        elif session_date and start_time and end_time:
            score += 25
            reasons_pass.append("No scheduling conflict detected")

        status_label = "Conflict" if conflict else ("Unavailable" if disqualified and not conflict else "Available")

        results.append({
            "speaker": s,
            "score": max(0, score),
            "disqualified": disqualified,
            "status_label": status_label,
            "reasons_pass": reasons_pass,
            "reasons_fail": reasons_fail,
        })

    results.sort(key=lambda r: (r["disqualified"], -r["score"]))
    if results:
        results[0]["recommended"] = not results[0]["disqualified"]
    for r in results[1:]:
        r["recommended"] = False

    return results


def get_venue_details(venue_id):
    """Full detail payload for the Venue Details view: venue info plus its
    complete booking/session history (past + upcoming)."""
    venue = db.query_one("SELECT * FROM venues WHERE id = ?", (venue_id,))
    if not venue:
        return None
    sessions = db.query_all(
        """SELECT s.*, sp.name as speaker_name FROM sessions s
           LEFT JOIN speakers sp ON s.speaker_id = sp.id
           WHERE s.venue_id = ? AND s.status != 'Cancelled'
           ORDER BY s.session_date ASC, s.start_time ASC""",
        (venue_id,),
    )
    today = datetime.now().strftime("%Y-%m-%d")
    upcoming = [s for s in sessions if s["session_date"] >= today]
    past = [s for s in sessions if s["session_date"] < today]
    venue["facilities_list"] = parse_csv_field(venue["facilities"])
    venue["live_status"] = "Maintenance" if venue["status"] == "Maintenance" else (venue_status_today(venue_id) or "Available")
    return {
        "venue": venue,
        "upcoming_sessions": upcoming,
        "past_sessions": past,
        "next_available": get_next_available_label(venue_id),
    }


# =================================================================
# ANALYTICS
# =================================================================
def generate_operations_analytics():
    venues = db.query_all("SELECT * FROM venues")
    speakers = db.query_all("SELECT * FROM speakers")
    sessions = db.query_all("SELECT * FROM sessions")
    conflicts = db.query_all("SELECT * FROM conflict_log ORDER BY created_at DESC")

    total_venues = len(venues)
    maintenance_venues = sum(1 for v in venues if v["status"] == "Maintenance")

    active_sessions = [s for s in sessions if s["status"] != "Cancelled"]
    booked_venue_ids = set(s["venue_id"] for s in active_sessions if s["venue_id"])
    occupied_venues = len(booked_venue_ids)
    available_venues = max(0, total_venues - maintenance_venues)

    total_speakers = len(speakers)
    assigned_speaker_ids = set(s["speaker_id"] for s in active_sessions if s["speaker_id"])
    available_speakers = total_speakers  # all speakers are potentially available; assigned tracked separately

    total_sessions = len(sessions)
    status_counter = Counter(s["status"] for s in sessions)
    scheduled_sessions = status_counter.get("Scheduled", 0)
    completed_sessions = status_counter.get("Completed", 0)
    upcoming_sessions = status_counter.get("Upcoming", 0)
    cancelled_sessions = status_counter.get("Cancelled", 0)

    # Venue utilization: proportion of venues with at least one active booking
    venue_utilization_pct = round((occupied_venues / total_venues) * 100, 1) if total_venues else 0.0

    # Per-venue utilization based on booked hours vs an assumed 8-hour operating day
    per_venue_minutes = defaultdict(int)
    for s in active_sessions:
        if s["venue_id"]:
            per_venue_minutes[s["venue_id"]] += duration_minutes(s["start_time"], s["end_time"])
    venue_names = {v["id"]: v["name"] for v in venues}
    venue_util_chart = {
        "labels": [venue_names.get(vid, f"Venue {vid}") for vid in per_venue_minutes],
        "data": [round(min(100, (mins / (8 * 60)) * 100), 1) for mins in per_venue_minutes.values()],
    }

    # Speaker utilization: sessions assigned per speaker
    speaker_assignment_counter = Counter()
    for s in active_sessions:
        if s["speaker_id"]:
            speaker_assignment_counter[s["speaker_id"]] += 1
    speaker_names = {sp["id"]: sp["name"] for sp in speakers}
    speaker_util_chart = {
        "labels": [speaker_names.get(sid, f"Speaker {sid}") for sid in speaker_assignment_counter],
        "data": list(speaker_assignment_counter.values()),
    }
    speaker_utilization_pct = round((len(assigned_speaker_ids) / total_speakers) * 100, 1) if total_speakers else 0.0

    sessions_by_type = Counter(s["session_type"] for s in sessions if s["session_type"])
    sessions_by_day = Counter(s["session_date"] for s in sessions if s["session_date"])
    sorted_days = sorted(sessions_by_day.keys())

    successful_allocations = sum(1 for s in active_sessions if s["venue_id"] and s["speaker_id"])

    venue_conflicts = sum(1 for c in conflicts if c["conflict_type"] == "venue")
    speaker_conflicts = sum(1 for c in conflicts if c["conflict_type"] == "speaker")

    return {
        "total_venues": total_venues,
        "available_venues": available_venues,
        "occupied_venues": occupied_venues,
        "maintenance_venues": maintenance_venues,
        "total_speakers": total_speakers,
        "assigned_speakers": len(assigned_speaker_ids),
        "available_speakers": available_speakers,
        "total_sessions": total_sessions,
        "scheduled_sessions": scheduled_sessions,
        "completed_sessions": completed_sessions,
        "upcoming_sessions": upcoming_sessions,
        "cancelled_sessions": cancelled_sessions,
        "venue_utilization_pct": venue_utilization_pct,
        "speaker_utilization_pct": speaker_utilization_pct,
        "successful_allocations": successful_allocations,
        "total_conflicts_prevented": len(conflicts),
        "venue_conflicts_prevented": venue_conflicts,
        "speaker_conflicts_prevented": speaker_conflicts,
        "recent_conflicts": conflicts[:8],
        "charts": {
            "sessions_by_type": {"labels": list(sessions_by_type.keys()), "data": list(sessions_by_type.values())},
            "sessions_by_day": {"labels": sorted_days, "data": [sessions_by_day[d] for d in sorted_days]},
            "venue_utilization": venue_util_chart,
            "speaker_assignments": speaker_util_chart,
            "conflict_stats": {"labels": ["Venue Conflicts", "Speaker Conflicts"],
                                "data": [venue_conflicts, speaker_conflicts]},
        },
    }


def venue_status_today(venue_id):
    """Return a live status label for a venue based on today's sessions."""
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")
    sessions_today = db.query_all(
        "SELECT * FROM sessions WHERE venue_id = ? AND session_date = ? AND status != 'Cancelled'",
        (venue_id, today),
    )
    for s in sessions_today:
        if _to_time(s["start_time"]) <= _to_time(now_time) <= _to_time(s["end_time"]):
            return "Occupied"
    if sessions_today:
        return "Reserved"
    return None  # no session today -> caller falls back to base status


def get_next_available_label(venue_id):
    """Human readable next-availability label for a venue, based on today's bookings."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    now_time = now.strftime("%H:%M")
    sessions_today = db.query_all(
        "SELECT * FROM sessions WHERE venue_id = ? AND session_date = ? AND status != 'Cancelled' ORDER BY start_time ASC",
        (venue_id, today),
    )
    for s in sessions_today:
        if _to_time(s["start_time"]) <= _to_time(now_time) <= _to_time(s["end_time"]):
            return f"Free after {s['end_time']} today"
    upcoming = [s for s in sessions_today if _to_time(s["start_time"]) and _to_time(s["start_time"]) > _to_time(now_time)]
    if upcoming:
        nxt = upcoming[0]
        return f"Booked {nxt['start_time']}-{nxt['end_time']} today"
    return "Available now"


# =================================================================
# VENUE SEARCH, FILTER & SORT
# =================================================================
def search_venues(filters):
    """
    Powers the Venue Management search/listing page: full-text search,
    multi-criteria filtering (capacity/location/room type/availability/
    facilities/date-time), and sorting including a lightweight "Best Match"
    relevance score reusing the same signals as the Venue Agent.

    filters = {
        q, capacity_min, location, room_type, availability,
        facilities: [str], date, start_time, end_time, attendees, sort
    }
    """
    q = (filters.get("q") or "").strip().lower()
    try:
        capacity_min = int(filters.get("capacity_min") or 0)
    except (TypeError, ValueError):
        capacity_min = 0
    location = (filters.get("location") or "").strip()
    room_type = (filters.get("room_type") or "").strip()
    availability = (filters.get("availability") or "All").strip()
    facilities_filter = [f for f in (filters.get("facilities") or []) if f]
    date = (filters.get("date") or "").strip()
    start_time = (filters.get("start_time") or "").strip()
    end_time = (filters.get("end_time") or "").strip()
    try:
        attendees = int(filters.get("attendees") or 0)
    except (TypeError, ValueError):
        attendees = 0
    sort = (filters.get("sort") or "name").strip()

    venues = db.query_all("SELECT * FROM venues ORDER BY name ASC")
    need = set(f.lower() for f in facilities_filter)
    results = []

    for v in venues:
        facilities_have = set(f.lower() for f in parse_csv_field(v["facilities"]))

        haystack = f"{v['name']} {v['location']} {v['room_type']} {v['facilities']}".lower()
        if q and q not in haystack:
            continue
        if capacity_min and v["capacity"] < capacity_min:
            continue
        if location and location.lower() != (v["location"] or "").lower():
            continue
        if room_type and room_type.lower() != (v["room_type"] or "").lower():
            continue
        if need and not need.issubset(facilities_have):
            continue

        conflict = None
        has_time_window = bool(date and start_time and end_time)
        if has_time_window:
            conflict = find_venue_conflict(v["id"], date, start_time, end_time)

        if v["status"] == "Maintenance":
            status_label = "Maintenance"
        elif conflict:
            status_label = "Reserved"
        elif has_time_window:
            status_label = "Available"
        else:
            status_label = venue_status_today(v["id"]) or "Available"

        if availability and availability != "All" and availability != status_label:
            continue

        score = 0
        if attendees:
            score += 40 if v["capacity"] >= attendees else 0
        if need:
            matched = need & facilities_have
            score += int(30 * (len(matched) / len(need)))
        if has_time_window:
            score += 30 if not conflict else 0
        if not attendees and not need and not has_time_window:
            score = 50  # neutral score when no ranking signal supplied

        results.append({
            "venue": v,
            "facilities_list": parse_csv_field(v["facilities"]),
            "availability_status": status_label,
            "booking_count": db.query_one(
                "SELECT COUNT(*) as c FROM sessions WHERE venue_id = ? AND status != 'Cancelled'", (v["id"],)
            )["c"],
            "next_available": get_next_available_label(v["id"]),
            "score": score,
        })

    status_order = {"Available": 0, "Reserved": 1, "Occupied": 2, "Maintenance": 3}
    if sort == "capacity_asc":
        results.sort(key=lambda r: r["venue"]["capacity"])
    elif sort == "capacity_desc":
        results.sort(key=lambda r: -r["venue"]["capacity"])
    elif sort == "availability":
        results.sort(key=lambda r: status_order.get(r["availability_status"], 4))
    elif sort == "best_match":
        results.sort(key=lambda r: -r["score"])
    else:
        results.sort(key=lambda r: r["venue"]["name"].lower())

    return results
