"""Typed state shared by LangGraph nodes."""

from typing import Any, TypedDict


class AssessmentState(TypedDict, total=False):

    # Unique assessment identifier
    assessment_id: str

    # Participant responses
    answers: dict[str, Any]

    # Validation information
    validation: dict[str, Any]

    # Assessment completion status
    # complete / incomplete
    completion_status: str

    # Human review status
    # pending / approved / needs_changes / not_required
    review_status: str

    # Professional attention flag
    professional_attention: bool

    # Reasons requiring professional review
    attention_reasons: list[str]

    # Generated assessment summary
    summary: str

    # Reflection and validation results
    reflection: dict[str, Any]

    # Human reviewer information
    reviewer_decision: str
    reviewer_notes: str