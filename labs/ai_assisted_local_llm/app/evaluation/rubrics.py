"""Default rubric definitions for case fidelity and student performance evaluation."""

from __future__ import annotations

CASE_FIDELITY_RUBRIC: dict = {
    "name": "Case Fidelity",
    "layer": "case_fidelity",
    "version": "1.0",
    "dimensions": [
        {
            "key": "history_accuracy",
            "name": "History Accuracy",
            "weight": 0.25,
            "anchors": {
                1: "Hallucinated symptoms or contradicts case",
                3: "Minor inconsistencies; core facts correct",
                5: "All facts match case; no additions or omissions",
            },
        },
        {
            "key": "disclosure_pacing",
            "name": "Disclosure Pacing",
            "weight": 0.20,
            "anchors": {
                1: "Dumps entire history at once or withholds key info",
                3: "Occasionally volunteers info unprompted",
                5: "Info revealed naturally in response to targeted questions",
            },
        },
        {
            "key": "emotional_portrayal",
            "name": "Emotional Portrayal",
            "weight": 0.20,
            "anchors": {
                1: "Robotic or wildly incongruent emotional responses",
                3: "Partially aligned; some tonal mismatches",
                5: "Tone matches case description; appropriate affect",
            },
        },
        {
            "key": "stays_in_character",
            "name": "Stays in Character",
            "weight": 0.15,
            "anchors": {
                1: "Breaks character; acts as assistant instead of patient",
                3: "Minor slips (e.g., uses medical jargon inappropriately)",
                5: "Never breaks character; deflects meta questions",
            },
        },
        {
            "key": "physical_exam_response",
            "name": "Physical Exam Response",
            "weight": 0.20,
            "anchors": {
                1: "Fabricates findings not in case or refuses to engage",
                3: "Reports findings but with minor inconsistencies",
                5: "Reports findings consistent with case when asked",
            },
        },
    ],
}

STUDENT_PERFORMANCE_RUBRIC: dict = {
    "name": "Student Performance",
    "layer": "student_performance",
    "version": "1.0",
    "dimensions": [
        {
            "key": "diagnostic_reasoning",
            "name": "Diagnostic Reasoning",
            "weight": 0.25,
            "anchors": {
                1: "Anchors on one diagnosis; no systematic approach",
                3: "Reasonable differential but questioning is unfocused",
                5: "Generates broad differential; systematically narrows with targeted questions",
            },
        },
        {
            "key": "history_gathering",
            "name": "History Gathering",
            "weight": 0.20,
            "anchors": {
                1: "Superficial; misses critical domains",
                3: "Gets most key elements but misses 1-2 domains",
                5: "Covers HPI, PMH, meds, allergies, social, family, ROS systematically",
            },
        },
        {
            "key": "red_flag_recognition",
            "name": "Red Flag Recognition",
            "weight": 0.20,
            "anchors": {
                1: "Misses critical red flags entirely",
                3: "Identifies some red flags but delays follow-up",
                5: "Identifies and follows up on all critical findings promptly",
            },
        },
        {
            "key": "empathy_rapport",
            "name": "Empathy & Rapport",
            "weight": 0.20,
            "anchors": {
                1: "Purely transactional; no emotional acknowledgment",
                3: "Some empathic responses but inconsistent",
                5: "Active listening, validates emotions, NURSE framework",
            },
        },
        {
            "key": "communication_clarity",
            "name": "Communication Clarity",
            "weight": 0.15,
            "anchors": {
                1: "Overuses jargon; no teach-back or clarification",
                3: "Generally clear but occasional jargon without clarification",
                5: "Avoids jargon; checks understanding; summarizes",
            },
        },
    ],
}


def get_rubric(layer: str) -> dict:
    """Return the default rubric for the given evaluation layer."""
    if layer == "case_fidelity":
        return CASE_FIDELITY_RUBRIC
    if layer == "student_performance":
        return STUDENT_PERFORMANCE_RUBRIC
    raise ValueError(f"Unknown layer: {layer}")
