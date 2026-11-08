"""LangGraph workflow for the mental health initial assessment agent."""

import json
import logging

from typing import Literal

from langchain_core.messages import (
    SystemMessage,
    HumanMessage
)

from langchain_ollama import ChatOllama

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langgraph.checkpoint.sqlite import SqliteSaver

from langgraph.types import (
    interrupt,
    Command
)

from config import (
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    CHECKPOINT_PATH,
    LOG_PATH
)

from schemas import AssessmentState

from database import update_record

from tools import (
    validate_assessment_tool,
    save_assessment_tool,
    get_attention_reasons
)


# ==================================================
# 1. EXECUTION LOGGING
# ==================================================

logging.basicConfig(

    filename=str(LOG_PATH),

    level=logging.INFO,

    format="%(asctime)s | %(levelname)s | %(message)s"

)

logger = logging.getLogger("mental_health_agent")


# ==================================================
# 2. FALLBACK SUMMARY
# ==================================================

def fallback_summary(answers, validation, reasons):

    """
    Generate a deterministic summary.

    This summary is used if the local LLM is unavailable
    or if the generated summary fails validation.
    """

    return f"""
### Summary of Reported Concerns

- Mood description: {answers.get('mood_description') or 'Not provided'}

- Mood score: {
    answers.get('mood_score')
    if answers.get('mood_score') is not None
    else 'Not provided'
} / 10

- Stress level: {
    answers.get('stress_level')
    if answers.get('stress_level') is not None
    else 'Not provided'
} / 10

- Average sleep: {
    answers.get('sleep_hours')
    if answers.get('sleep_hours') is not None
    else 'Not provided'
} hours

- Sleep quality: {answers.get('sleep_quality') or 'Not provided'}

- Anxiety experiences: {answers.get('anxiety_experience') or 'Not provided'}

- Daily functioning: {answers.get('daily_functioning') or 'Not provided'}

- Personal concerns: {answers.get('personal_concerns') or 'Not provided'}


### Missing or Inconsistent Information

- Missing fields: {validation.get('missing_fields', [])}

- Invalid responses: {validation.get('errors', [])}

- Possible inconsistencies requiring clarification:
  {validation.get('inconsistencies', [])}


### Areas for Professional Review

- {
    chr(10).join(reasons)
    if reasons
    else 'A qualified mental health professional should review this organized information as part of the initial assessment.'
}


**Scope notice:** This report organizes self-reported information only.
It does not diagnose a condition, assess clinical risk, or recommend treatment.
"""


# ==================================================
# 3. AI SUMMARY GENERATION
# ==================================================

def generate_summary(answers, validation, reasons):

    """
    Use the local Qwen model through LangChain
    to generate a structured assessment summary.
    """

    fallback = fallback_summary(
        answers,
        validation,
        reasons
    )

    try:

        llm = ChatOllama(

            model=OLLAMA_MODEL,

            base_url=OLLAMA_BASE_URL,

            temperature=0

        )

        system_prompt = """
You organize self-reported information for a qualified
mental health professional.

Your responsibilities:

1. Organize the participant's reported information.
2. Preserve the original answers and scores.
3. Identify missing information.
4. Identify invalid responses.
5. Identify possible inconsistencies.
6. Highlight areas requiring professional review.

IMPORTANT SAFETY RULES:

- Do not diagnose mental health conditions.
- Do not estimate clinical risk.
- Do not recommend treatment.
- Do not invent facts.
- Do not change participant scores.
- Do not interpret answers as a medical diagnosis.
- Use only the supplied information.

Use these exact Markdown headings:

### Summary of Reported Concerns

### Missing or Inconsistent Information

### Areas for Professional Review

End with a statement that this is not a diagnosis
or treatment recommendation.
"""

        payload = {

            "answers": answers,

            "validation": validation,

            "professional_attention_reasons": reasons

        }

        response = llm.invoke([

            SystemMessage(
                content=system_prompt
            ),

            HumanMessage(
                content=json.dumps(
                    payload,
                    ensure_ascii=False
                )
            )

        ])

        content = response.content

        if isinstance(content, list):

            content = " ".join(
                str(part)
                for part in content
            )

        content = str(content).strip()

        required_headings = (

            "Summary of Reported Concerns",

            "Missing or Inconsistent Information",

            "Areas for Professional Review"

        )

        if (
            content
            and all(
                heading.lower() in content.lower()
                for heading in required_headings
            )
        ):

            return content

        logger.warning(
            "LLM summary failed required heading check. "
            "Using fallback summary."
        )

    except Exception:

        logger.exception(
            "LLM summary generation failed. "
            "Using fallback summary."
        )

    return fallback


# ==================================================
# 4. VALIDATION NODE
# ==================================================

def validation_node(state: AssessmentState):

    """
    Validate participant answers.

    Identify missing fields, invalid values,
    and possible inconsistencies.
    """

    logger.info(
        "Assessment %s: validation started",
        state["assessment_id"]
    )

    raw = validate_assessment_tool.invoke({

        "answers_json": json.dumps(
            state["answers"]
        )

    })

    validation = json.loads(raw)

    reasons = get_attention_reasons(
        state["answers"]
    )

    completion = (

        "complete"
        if validation["is_complete"]
        else "incomplete"

    )

    logger.info(
        "Assessment %s: validation finished (%s)",
        state["assessment_id"],
        completion
    )

    return {

        "validation": validation,

        "completion_status": completion,

        "review_status": "pending",

        "professional_attention": bool(reasons),

        "attention_reasons": reasons

    }


# ==================================================
# 5. DATABASE SAVE NODE
# ==================================================

def save_node(state: AssessmentState):

    """
    Save assessment responses and validation
    information into the SQLite database.
    """

    logger.info(
        "Assessment %s: saving record",
        state["assessment_id"]
    )

    save_assessment_tool.invoke({

        "assessment_id": state["assessment_id"],

        "answers_json": json.dumps(
            state["answers"]
        ),

        "validation_json": json.dumps(
            state["validation"]
        ),

        "completion_status": state["completion_status"],

        "professional_attention": state["professional_attention"]

    })

    return {}


# ==================================================
# 6. INCOMPLETE ASSESSMENT NODE
# ==================================================

def incomplete_node(state: AssessmentState):

    """
    Handle assessments containing missing or
    invalid required information.
    """

    summary = fallback_summary(

        state["answers"],

        state["validation"],

        state.get("attention_reasons", [])

    )

    update_record(

        state["assessment_id"],

        summary=summary,

        completion_status="incomplete",

        review_status="not_required",

        reviewer_decision="not_required",

        reviewer_notes=(
            "Assessment needs missing or invalid "
            "information completed."
        )

    )

    logger.info(
        "Assessment %s: routed to incomplete path",
        state["assessment_id"]
    )

    return {

        "summary": summary,

        "review_status": "not_required",

        "reflection": {

            "passed": True,

            "method": (
                "Deterministic rule-based report "
                "for incomplete assessment"
            )

        }

    }


# ==================================================
# 7. SUMMARY NODE
# ==================================================

def summary_node(state: AssessmentState):

    """
    Generate the structured assessment summary
    using the local LLM.
    """

    logger.info(
        "Assessment %s: generating summary",
        state["assessment_id"]
    )

    summary = generate_summary(

        state["answers"],

        state["validation"],

        state.get("attention_reasons", [])

    )

    return {

        "summary": summary

    }


# ==================================================
# 8. REFLECTION AND VALIDATION NODE
# ==================================================

def reflection_node(state: AssessmentState):

    """
    Review the generated summary.

    Check required headings, reported numeric values,
    and safe language.

    Replace the summary with a deterministic version
    if the checks fail.
    """

    summary = state.get(
        "summary",
        ""
    )

    answers = state["answers"]

    validation = state["validation"]

    reasons = state.get(
        "attention_reasons",
        []
    )

    required = (

        "Summary of Reported Concerns",

        "Missing or Inconsistent Information",

        "Areas for Professional Review"

    )

    # Check summary structure

    structure_ok = (

        bool(summary.strip())

        and all(
            heading.lower() in summary.lower()
            for heading in required
        )

    )

    # Check whether supplied numerical values
    # are represented in the generated summary.

    anchors = [

        answers.get("mood_score"),

        answers.get("stress_level"),

        answers.get("sleep_hours")

    ]

    anchors_ok = all(

        value is None or str(value) in summary

        for value in anchors

    )

    # Check that the report does not present itself
    # as a diagnosis.

    safety_ok = (

        "diagnos" not in summary.lower()

        or "not a diagnosis" in summary.lower()

    )

    passed = (

        structure_ok

        and anchors_ok

        and safety_ok

    )

    # Use a deterministic summary if reflection fails.

    if not passed:

        logger.warning(
            "Assessment %s: reflection failed. "
            "Deterministic summary substituted.",
            state["assessment_id"]
        )

        summary = fallback_summary(

            answers,

            validation,

            reasons

        )

    reflection = {

        "passed": passed,

        "structure_check": structure_ok,

        "reported_value_check": anchors_ok,

        "scope_language_check": safety_ok,

        "method": (
            "Rule-based structure, value-anchor "
            "and scope validation"
        ),

        "fallback_used": not passed

    }

    logger.info(
        "Assessment %s: reflection completed (passed=%s)",
        state["assessment_id"],
        passed
    )

    return {

        "summary": summary,

        "reflection": reflection

    }


# ==================================================
# 9. HUMAN-IN-THE-LOOP NODE
# ==================================================

def human_review_node(state: AssessmentState):

    """
    Pause workflow execution.

    Wait for a human reviewer to approve the report
    or request changes.
    """

    decision = interrupt({

        "message": (
            "Human review is required before "
            "this report is approved."
        ),

        "assessment_id": state["assessment_id"],

        "summary": state["summary"],

        "validation": state["validation"],

        "professional_attention": state.get(
            "professional_attention",
            False
        ),

        "attention_reasons": state.get(
            "attention_reasons",
            []
        ),

        "completion_status": state.get(
            "completion_status",
            "incomplete"
        )

    })

    decision_value = decision.get(
        "decision",
        "needs_changes"
    )

    if decision_value not in {
        "approved",
        "needs_changes"
    }:

        decision_value = "needs_changes"

    notes = str(
        decision.get("notes", "")
    )

    review_status = (

        "approved"
        if decision_value == "approved"
        else "needs_changes"

    )

    # Save human review information

    update_record(

        state["assessment_id"],

        summary=state["summary"],

        completion_status=state.get(
            "completion_status",
            "incomplete"
        ),

        review_status=review_status,

        reviewer_decision=decision_value,

        reviewer_notes=notes

    )

    logger.info(
        "Assessment %s: human review decision=%s",
        state["assessment_id"],
        decision_value
    )

    return {

        "reviewer_decision": decision_value,

        "reviewer_notes": notes,

        "review_status": review_status

    }


# ==================================================
# 10. BUILD LANGGRAPH STATEGRAPH
# ==================================================

def build_graph(checkpointer, interrupt_before=None):

    """
    Build the LangGraph StateGraph.

    Nodes:
    validate
    save
    incomplete
    summarize
    reflect
    human_review
    """

    builder = StateGraph(
        AssessmentState
    )

    # Register workflow nodes

    builder.add_node(
        "validate",
        validation_node
    )

    builder.add_node(
        "save",
        save_node
    )

    builder.add_node(
        "incomplete",
        incomplete_node
    )

    builder.add_node(
        "summarize",
        summary_node
    )

    builder.add_node(
        "reflect",
        reflection_node
    )

    builder.add_node(
        "human_review",
        human_review_node
    )

    # Initial workflow connection

    builder.add_edge(
        START,
        "validate"
    )

    builder.add_edge(
        "validate",
        "save"
    )

    # Conditional routing

    def route_assessment(
        state: AssessmentState
    ) -> Literal["incomplete", "summarize"]:

        """
        Route assessments according to validation
        and professional attention requirements.

        Significant-attention cases are summarized
        and sent for human review even if some
        required fields are missing.
        """

        if (
            state.get("professional_attention")

            or state["validation"]["is_complete"]
        ):

            return "summarize"

        return "incomplete"

    builder.add_conditional_edges(

        "save",

        route_assessment,

        {

            "incomplete": "incomplete",

            "summarize": "summarize"

        }

    )

    # Remaining workflow connections

    builder.add_edge(
        "incomplete",
        END
    )

    builder.add_edge(
        "summarize",
        "reflect"
    )

    builder.add_edge(
        "reflect",
        "human_review"
    )

    builder.add_edge(
        "human_review",
        END
    )

    # Compile graph with checkpointing

    return builder.compile(

        checkpointer=checkpointer,

        interrupt_before=interrupt_before or []

    )


# ==================================================
# 11. RUN ASSESSMENT
# ==================================================

def run_assessment(
    assessment_id,
    answers,
    *,
    pause_before_incomplete=False
):

    """
    Start a new assessment workflow.

    A persistent SQLite checkpointer preserves
    workflow progress.
    """

    with SqliteSaver.from_conn_string(
        str(CHECKPOINT_PATH)
    ) as checkpointer:

        interrupts = (

            ["incomplete"]
            if pause_before_incomplete
            else []

        )

        graph = build_graph(

            checkpointer,

            interrupt_before=interrupts

        )

        config = {

            "configurable": {

                "thread_id": assessment_id

            }

        }

        initial_state = {

            "assessment_id": assessment_id,

            "answers": answers

        }

        return graph.invoke(

            initial_state,

            config=config

        )


# ==================================================
# 12. RESUME INTERRUPTED ASSESSMENT
# ==================================================

def resume_interrupted_assessment(assessment_id):

    """
    Resume a workflow paused at a checkpoint.

    This function is used to demonstrate
    assessment interruption and resumption.
    """

    with SqliteSaver.from_conn_string(
        str(CHECKPOINT_PATH)
    ) as checkpointer:

        graph = build_graph(
            checkpointer
        )

        config = {

            "configurable": {

                "thread_id": assessment_id

            }

        }

        return graph.invoke(
            None,
            config=config
        )


# ==================================================
# 13. RESUME HUMAN REVIEW
# ==================================================

def resume_assessment(
    assessment_id,
    decision,
    notes=""
):

    """
    Resume the workflow after human review.

    The reviewer can approve the summary
    or request changes.
    """

    with SqliteSaver.from_conn_string(
        str(CHECKPOINT_PATH)
    ) as checkpointer:

        graph = build_graph(
            checkpointer
        )

        config = {

            "configurable": {

                "thread_id": assessment_id

            }

        }

        return graph.invoke(

            Command(

                resume={

                    "decision": decision,

                    "notes": notes

                }

            ),

            config=config

        )