"""LangChain tools and deterministic assessment validation rules."""

import json

from langchain_core.tools import tool

from database import (
    save_record,
    get_record,
    get_recent_records
)


# --------------------------------------------------
# REQUIRED ASSESSMENT FIELDS
# --------------------------------------------------

REQUIRED_FIELDS = {

    "participant_name": "Participant name or anonymous ID",

    "age": "Age",

    "mood_description": "Mood description",

    "mood_score": "Mood score",

    "stress_level": "Stress level",

    "sleep_hours": "Average sleep hours",

    "sleep_quality": "Sleep quality",

    "anxiety_experience": "Anxiety experience",

    "daily_functioning": "Daily functioning",

    "personal_concerns": "Personal concerns",

    "self_harm_thoughts": "Safety question"

}


# --------------------------------------------------
# CHECK EMPTY VALUES
# --------------------------------------------------

def _is_blank(value):

    return (
        value is None
        or (
            isinstance(value, str)
            and not value.strip()
        )
    )


# --------------------------------------------------
# VALIDATE ASSESSMENT ANSWERS
# --------------------------------------------------

def validate_answers(answers: dict):

    missing = []

    errors = []

    inconsistencies = []

    # Check missing required fields

    for field, label in REQUIRED_FIELDS.items():

        if (
            field not in answers
            or _is_blank(answers.get(field))
        ):

            missing.append(label)

    # Validate age

    if not _is_blank(answers.get("age")):

        try:

            age = int(answers["age"])

            if not 1 <= age <= 120:

                errors.append(
                    "Age must be between 1 and 120."
                )

        except (TypeError, ValueError):

            errors.append(
                "Age must be a whole number."
            )

    # Validate mood and stress scores

    for field, label in [

        ("mood_score", "Mood score"),

        ("stress_level", "Stress level")

    ]:

        if not _is_blank(answers.get(field)):

            try:

                score = int(answers[field])

                if not 1 <= score <= 10:

                    errors.append(
                        f"{label} must be between 1 and 10."
                    )

            except (TypeError, ValueError):

                errors.append(
                    f"{label} must be a whole number from 1 to 10."
                )

    # Validate sleep hours

    if not _is_blank(answers.get("sleep_hours")):

        try:

            hours = float(answers["sleep_hours"])

            if not 0 <= hours <= 24:

                errors.append(
                    "Sleep hours must be between 0 and 24."
                )

        except (TypeError, ValueError):

            errors.append(
                "Sleep hours must be a number."
            )

    # Validate sleep quality

    quality = answers.get("sleep_quality")

    if (
        not _is_blank(quality)
        and quality not in {
            "Good",
            "Fair",
            "Poor",
            "Varies"
        }
    ):

        errors.append(
            "Sleep quality must be Good, Fair, Poor, or Varies."
        )

    # Validate safety question

    safety = answers.get("self_harm_thoughts")

    if (
        not _is_blank(safety)
        and safety not in {
            "Yes",
            "No",
            "Prefer not to say"
        }
    ):

        errors.append(
            "Safety response must be Yes, No, or Prefer not to say."
        )

    # Check possible mood inconsistencies

    mood_text = str(
        answers.get("mood_description") or ""
    ).lower()

    try:

        mood_score = int(
            answers.get("mood_score")
        )

        positive = (
            "happy",
            "good",
            "positive",
            "excellent"
        )

        negative = (
            "sad",
            "hopeless",
            "terrible",
            "very bad"
        )

        if (
            mood_score <= 3
            and any(word in mood_text for word in positive)
        ):

            inconsistencies.append(
                "Mood score is low, while the written mood "
                "description contains positive wording. "
                "Please confirm."
            )

        if (
            mood_score >= 8
            and any(word in mood_text for word in negative)
        ):

            inconsistencies.append(
                "Mood score is high, while the written mood "
                "description contains negative wording. "
                "Please confirm."
            )

    except (TypeError, ValueError):

        pass

    return {

        "is_complete": (
            not missing
            and not errors
        ),

        "missing_fields": missing,

        "errors": errors,

        "inconsistencies": inconsistencies

    }


# --------------------------------------------------
# IDENTIFY RESPONSES REQUIRING PROFESSIONAL ATTENTION
# --------------------------------------------------

def get_attention_reasons(answers):

    reasons = []

    # Safety response flag

    if (
        str(
            answers.get("self_harm_thoughts", "")
        ).strip().lower() == "yes"
    ):

        reasons.append(
            "The participant answered YES to the safety question. "
            "Prompt human review without delay."
        )

    # High reported stress flag

    try:

        if int(answers.get("stress_level")) >= 8:

            reasons.append(
                "The participant reported a stress score of 8 or higher."
            )

    except (TypeError, ValueError):

        pass

    # Daily functioning flag

    functioning = str(
        answers.get("daily_functioning", "")
    ).lower()

    difficulty_words = (

        "unable",

        "cannot manage",

        "not able",

        "severely affected",

        "struggling to manage"

    )

    if any(
        word in functioning
        for word in difficulty_words
    ):

        reasons.append(
            "The participant described difficulty with daily functioning."
        )

    return reasons


# --------------------------------------------------
# LANGCHAIN TOOL 1: VALIDATE ASSESSMENT
# --------------------------------------------------

@tool
def validate_assessment_tool(answers_json: str) -> str:

    """
    Validate submitted answers.

    Identify missing fields, invalid values,
    and possible inconsistent responses.
    """

    answers = json.loads(answers_json)

    result = validate_answers(answers)

    return json.dumps(result)


# --------------------------------------------------
# LANGCHAIN TOOL 2: SAVE ASSESSMENT
# --------------------------------------------------

@tool
def save_assessment_tool(
    assessment_id: str,
    answers_json: str,
    validation_json: str,
    completion_status: str,
    professional_attention: bool
) -> str:

    """
    Save assessment responses and validation results
    into the SQLite database.
    """

    save_record(

        assessment_id,

        json.loads(answers_json),

        json.loads(validation_json),

        completion_status,

        professional_attention

    )

    return "Assessment record saved."


# --------------------------------------------------
# LANGCHAIN TOOL 3: RETRIEVE ASSESSMENT
# --------------------------------------------------

@tool
def retrieve_assessment_tool(
    assessment_id: str = "",
    limit: int = 10
) -> str:

    """
    Retrieve one assessment using its ID,
    or retrieve recent assessment records.
    """

    if assessment_id.strip():

        record = get_record(assessment_id)

        return (
            json.dumps(
                record,
                ensure_ascii=False,
                default=str
            )
            if record
            else "Record not found."
        )

    records = get_recent_records(limit)

    return json.dumps(
        records,
        ensure_ascii=False,
        default=str
    )