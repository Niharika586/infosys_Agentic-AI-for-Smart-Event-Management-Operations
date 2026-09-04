"""
decision_support.py
---------------------
MILESTONE 4 — Real-Time Decision Support Center.

Thin, presentation-focused layer on top of agent_orchestrator.py. Provides
the canned example questions shown in the Decision Support UI and formats
orchestration results for that page specifically.
"""

import agent_orchestrator as orch

SAMPLE_QUESTIONS = [
    "Which venue should be selected?",
    "Which speaker is best for this session?",
    "Is the event ready?",
    "What are the biggest risks?",
    "Which sponsors need follow-up?",
    "Are there scheduling conflicts?",
    "What should the organizer prioritize?",
    "What is likely to cause event disruption?",
]


def analyze(question, user="Event Organizer", context_extra=None):
    """Run the orchestrator for a free-text decision-support question."""
    return orch.run_orchestration(problem_text=question, context_extra=context_extra, user=user)


def run_quick_action(action_key, user="Event Organizer"):
    return orch.run_orchestration(quick_action=action_key, user=user)
