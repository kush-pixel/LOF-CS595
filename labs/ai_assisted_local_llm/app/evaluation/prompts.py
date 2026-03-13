"""Prompt templates for LLM-as-Judge evaluation."""

from __future__ import annotations

from app.evaluation.schemas import CaseDescription, Transcript


def _format_transcript(transcript: Transcript) -> str:
    """Format transcript turns into readable text."""
    lines = []
    for turn in transcript.turns:
        lines.append(f"[Turn {turn.turn_number}] {turn.speaker}: {turn.content}")
    return "\n".join(lines)


def _format_rubric_dimensions(dimensions: list[dict]) -> str:
    """Format rubric dimensions into XML for the prompt."""
    parts = []
    for dim in dimensions:
        anchors = dim["anchors"]
        parts.append(
            f"""<dimension>
  <name>{dim['name']}</name>
  <key>{dim['key']}</key>
  <weight>{dim['weight']}</weight>
  <anchor score="1">{anchors[1]}</anchor>
  <anchor score="3">{anchors[3]}</anchor>
  <anchor score="5">{anchors[5]}</anchor>
</dimension>"""
        )
    return "\n".join(parts)


def _format_case_description(case: CaseDescription) -> str:
    """Format case description into XML."""
    sections = []
    if case.demographics:
        demo_lines = [f"  <{k}>{v}</{k}>" for k, v in case.demographics.items()]
        sections.append(f"<demographics>\n{''.join(demo_lines)}\n</demographics>")
    if case.chief_complaint:
        sections.append(f"<chief_complaint>{case.chief_complaint}</chief_complaint>")
    if case.hpi:
        sections.append(f"<hpi>{case.hpi}</hpi>")
    if case.pmh:
        sections.append(f"<past_medical_history>{', '.join(case.pmh)}</past_medical_history>")
    if case.medications:
        sections.append(f"<medications>{', '.join(case.medications)}</medications>")
    if case.allergies:
        sections.append(f"<allergies>{', '.join(case.allergies)}</allergies>")
    if case.social_history:
        sh_lines = [f"  <{k}>{v}</{k}>" for k, v in case.social_history.items()]
        sections.append(f"<social_history>\n{''.join(sh_lines)}\n</social_history>")
    if case.family_history:
        sections.append(f"<family_history>{', '.join(case.family_history)}</family_history>")
    if case.ros:
        ros_lines = [f"  <{k}>{v}</{k}>" for k, v in case.ros.items()]
        sections.append(f"<review_of_systems>\n{''.join(ros_lines)}\n</review_of_systems>")
    if case.physical_exam_findings:
        pe_lines = [f"  <{k}>{v}</{k}>" for k, v in case.physical_exam_findings.items()]
        sections.append(f"<physical_exam>\n{''.join(pe_lines)}\n</physical_exam>")
    if case.labs:
        lab_lines = [f"  <{k}>{v}</{k}>" for k, v in case.labs.items()]
        sections.append(f"<labs>\n{''.join(lab_lines)}\n</labs>")
    if case.imaging:
        sections.append(f"<imaging>{', '.join(case.imaging)}</imaging>")
    if case.differential_diagnosis:
        sections.append(
            f"<differential_diagnosis>{', '.join(case.differential_diagnosis)}</differential_diagnosis>"
        )
    if case.final_diagnosis:
        sections.append(f"<final_diagnosis>{case.final_diagnosis}</final_diagnosis>")
    if case.emotional_presentation:
        sections.append(
            f"<emotional_presentation>{case.emotional_presentation}</emotional_presentation>"
        )
    return "\n".join(sections)


SYSTEM_PROMPT = """You are an expert medical education evaluator acting as an impartial judge. \
You will evaluate a student-patient conversation transcript against a structured rubric.

IMPORTANT INSTRUCTIONS:
1. Think step-by-step (chain-of-thought) BEFORE assigning any score.
2. For each dimension, cite specific transcript turn numbers as evidence.
3. Quote the exact text from the transcript that supports your score.
4. Do NOT favor verbose responses — evaluate substance over length.
5. Do NOT let the order of turns create position bias — evaluate the full conversation holistically.
6. Be calibrated: a score of 3 means adequate, not bad. Reserve 1 for genuinely poor performance \
and 5 for genuinely excellent performance.
7. Provide actionable feedback in growth_areas — be specific about what could improve."""


def build_evaluation_prompt(
    case: CaseDescription,
    transcript: Transcript,
    rubric: dict,
    layer: str,
) -> str:
    """Assemble the full LLM-as-judge prompt using XML tags."""

    layer_description = (
        "CASE FIDELITY: Evaluate how faithfully the simulated patient represents the case. "
        "Does the patient stay accurate to the case description?"
        if layer == "case_fidelity"
        else "STUDENT PERFORMANCE: Evaluate the student's clinical reasoning, "
        "history-gathering skills, and communication abilities."
    )

    return f"""<evaluation_task>
<layer>{layer}</layer>
<description>{layer_description}</description>
</evaluation_task>

<case_description>
{_format_case_description(case)}
</case_description>

<transcript>
{_format_transcript(transcript)}
</transcript>

<rubric>
{_format_rubric_dimensions(rubric['dimensions'])}
</rubric>

<instructions>
Evaluate the transcript against EACH dimension in the rubric above.

For each dimension:
1. Re-read the relevant parts of the transcript
2. Compare against the case description and rubric anchors
3. Reason through your assessment step-by-step
4. Cite specific turn numbers and quotes as evidence
5. Assign an integer score from 1 to 5
6. List concrete strengths and growth areas

After scoring all dimensions, compute the weighted total score and provide:
- An overall summary paragraph
- Your single top recommendation for improvement
</instructions>"""
