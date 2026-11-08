"""Streamlit interface for the Mental Health Initial Assessment Agent."""

import uuid

import streamlit as st

from agent import (
    run_assessment,
    resume_assessment
)

from database import (
    initialize_database,
    get_recent_records
)


 #PAGE CONFIGURATION

st.set_page_config(

    page_title="Mental Health Initial Assessment Agent",

    page_icon="🧠",

    layout="wide"

)

initialize_database()



# 2. SESSION STATE

for key, default in {

    "pending_id": None,

    "pending_review": None,

    "last_result": None

}.items():

    if key not in st.session_state:

        st.session_state[key] = default


# 3. APPLICATION HEADER

st.title(
    "🧠 Mental Health Screening and Initial Assessment Agent"
)

st.subheader(
    "Structured Information Collection and Professional Review"
)

st.info(
    "This educational prototype organizes information "
    "reported by a participant for review by a qualified "
    "mental health professional. It does not diagnose "
    "conditions, assess clinical risk, or recommend treatment."
)

st.warning(
    "This application is not an emergency service. "
    "If someone may be in immediate danger, contact local "
    "emergency services or go to the nearest emergency "
    "department. Do not wait for this application or "
    "an AI-generated report."
)



# 4. APPLICATION NAVIGATION


new_tab, records_tab, about_tab = st.tabs([

    "New Assessment",

    "Previous Records",

    "About This Project"

])


# TAB 1: NEW ASSESSMENT

with new_tab:

    st.header(
        "1. Participant Information"
    )

    st.caption(
        "Use synthetic information for coursework demonstrations. "
        "Avoid collecting unnecessary identifying details."
    )


    # ASSESSMENT FORM

    with st.form(
        "assessment_form",
        clear_on_submit=False
    ):

        left, right = st.columns(2)

        # LEFT COLUMN

        with left:

            participant_name = st.text_input(

                "Participant name or anonymous ID *",

                placeholder="Enter an ID or anonymous label"

            )

            age_text = st.text_input(

                "Age *",

                placeholder="Enter age in years"

            )

            mood_description = st.text_area(

                "Mood and emotional wellbeing *",

                placeholder=(
                    "How would you describe your mood recently?"
                )

            )

            mood_score_choice = st.selectbox(

                "Mood score (1 = very low, 10 = very positive) *",

                ["Not answered"] + list(range(1, 11))

            )

            stress_choice = st.selectbox(

                "Stress level (1 = low, 10 = very high) *",

                ["Not answered"] + list(range(1, 11))

            )

            sleep_text = st.text_input(

                "Average sleep hours per night *",

                placeholder="For example: 7.5"

            )

        # RIGHT COLUMN

        with right:

            sleep_quality = st.selectbox(

                "Sleep quality *",

                [

                    "Not answered",

                    "Good",

                    "Fair",

                    "Poor",

                    "Varies"

                ]

            )

            anxiety_experience = st.text_area(

                "Anxiety-related experiences *",

                placeholder=(
                    "Have you experienced anxiety or excessive worry?"
                )

            )

            daily_functioning = st.text_area(

                "Daily activities and functioning *",

                placeholder=(
                    "How are your daily activities, studies, "
                    "work, and relationships?"
                )

            )

            personal_concerns = st.text_area(

                "Personal concerns and challenges *",

                placeholder=(
                    "What concerns or challenges would you like to share?"
                )

            )

            safety_answer = st.selectbox(

                "Safety question *",

                [

                    "Not answered",

                    "Prefer not to say",

                    "No",

                    "Yes"

                ],

                help=(
                    "Are you currently thinking about harming "
                    "yourself or someone else? A YES response "
                    "is flagged for prompt human review."
                )

            )

        st.caption(
            "* Required for a complete assessment. "
            "You may leave a field unanswered; the validation "
            "tool will identify it."
        )

        submitted = st.form_submit_button(

            "Submit Assessment",

            type="primary",

            use_container_width=True

        )


    # 5. PROCESS SUBMITTED ASSESSMENT

    if submitted:

        # Convert age into a number when possible

        try:

            age_value = (
                int(age_text.strip())
                if age_text.strip()
                else None
            )

        except ValueError:

            age_value = age_text.strip()


        # Convert sleep hours into a number when possible

        try:

            sleep_value = (
                float(sleep_text.strip())
                if sleep_text.strip()
                else None
            )

        except ValueError:

            sleep_value = sleep_text.strip()


        # Build participant response dictionary

        answers = {

            "participant_name": (
                participant_name.strip()
                or None
            ),

            "age": age_value,

            "mood_description": (
                mood_description.strip()
                or None
            ),

            "mood_score": (
                mood_score_choice
                if isinstance(mood_score_choice, int)
                else None
            ),

            "stress_level": (
                stress_choice
                if isinstance(stress_choice, int)
                else None
            ),

            "sleep_hours": sleep_value,

            "sleep_quality": (
                sleep_quality
                if sleep_quality != "Not answered"
                else None
            ),

            "anxiety_experience": (
                anxiety_experience.strip()
                or None
            ),

            "daily_functioning": (
                daily_functioning.strip()
                or None
            ),

            "personal_concerns": (
                personal_concerns.strip()
                or None
            ),

            "self_harm_thoughts": (
                safety_answer
                if safety_answer != "Not answered"
                else None
            )

        }


        # Generate unique assessment ID

        assessment_id = str(
            uuid.uuid4()
        )


        # Run LangGraph workflow

        try:

            with st.spinner(
                "LangGraph agent is validating and processing the assessment..."
            ):

                result = run_assessment(

                    assessment_id,

                    answers

                )

            st.session_state.last_result = result

            # Check Human-in-the-Loop interruption

            if result.get("__interrupt__"):

                interrupt_value = (
                    result["__interrupt__"][0].value
                )

                st.session_state.pending_id = assessment_id

                st.session_state.pending_review = interrupt_value

                st.success(
                    "The report is ready and has been paused for human review."
                )

            else:

                st.session_state.pending_id = None

                st.session_state.pending_review = None

                st.warning(
                    "The assessment is incomplete. "
                    "Review the missing or invalid fields below "
                    "and submit a completed assessment when ready."
                )

        except Exception as exc:

            st.error(
                f"The workflow could not be completed: {exc}"
            )


    # ==================================================
    # 6. HUMAN-IN-THE-LOOP REVIEW
    # ==================================================

    if st.session_state.pending_review:

        review = st.session_state.pending_review

        st.divider()

        st.header(
            "2. Human-in-the-Loop Review"
        )

        # Display priority flag

        if review.get("professional_attention"):

            st.error(
                "Priority flag: this assessment contains "
                "responses requiring prompt professional attention."
            )

            for reason in review.get(
                "attention_reasons",
                []
            ):

                st.write(
                    f"- {reason}"
                )

        # Display generated summary

        st.markdown(
            review.get("summary", "")
        )

        st.subheader(
            "Reviewer Decision"
        )

        with st.form(
            "human_review_form"
        ):

            reviewer_notes = st.text_area(

                "Reviewer notes",

                placeholder=(
                    "Record clarification or review notes."
                )

            )

            decision = st.radio(

                "Decision",

                [

                    "approved",

                    "needs_changes"

                ],

                format_func=lambda value: (

                    "Approve report"

                    if value == "approved"

                    else "Request changes"

                ),

                horizontal=True

            )

            review_submitted = st.form_submit_button(

                "Save Human Review",

                type="primary"

            )


        # Resume LangGraph after human decision

        if review_submitted:

            try:

                with st.spinner(
                    "Saving reviewer decision..."
                ):

                    result = resume_assessment(

                        st.session_state.pending_id,

                        decision,

                        reviewer_notes

                    )

                st.session_state.last_result = result

                st.session_state.pending_review = None

                st.session_state.pending_id = None

                st.success(
                    "Human review decision saved."
                )

                st.rerun()

            except Exception as exc:

                st.error(
                    f"Could not save the review decision: {exc}"
                )


    # ==================================================
    # 7. DISPLAY FINAL ASSESSMENT OUTPUT
    # ==================================================

    result = st.session_state.last_result

    if (
        result

        and not st.session_state.pending_review

        and result.get("summary")
    ):

        st.divider()

        st.header(
            "3. Assessment Output"
        )

        st.markdown(
            result["summary"]
        )

        st.write(

            "**Assessment completion status:**",

            result.get(
                "completion_status",
                "incomplete"
            )

        )

        st.write(

            "**Human review status:**",

            result.get(
                "review_status",
                "not_required"
            )

        )

        st.write(

            "**Validation results:**",

            result.get(
                "validation",
                {}
            )

        )

        st.write(

            "**Reflection checks:**",

            result.get(
                "reflection",
                {}
            )

        )

        if result.get("reviewer_decision"):

            st.write(

                "**Reviewer decision:**",

                result["reviewer_decision"]

            )


# ==================================================
# TAB 2: PREVIOUS ASSESSMENT RECORDS
# ==================================================

with records_tab:

    st.header(
        "Previous Assessment Records"
    )

    st.caption(
        "Records are stored locally in the project's SQLite database."
    )

    records = get_recent_records(50)

    if not records:

        st.info(
            "No assessment records are available yet."
        )

    else:

        for record in records:

            heading = (

                f"{record.get('created_at', '')[:19]}"

                f" | {record.get('completion_status')}"

                f" | {record['assessment_id'][:8]}"

            )

            with st.expander(heading):

                st.write(

                    "**Assessment ID:**",

                    record["assessment_id"]

                )

                st.write(

                    "**Participant:**",

                    record["answers"].get(
                        "participant_name"
                    ) or "Not provided"

                )

                st.write(

                    "**Completion status:**",

                    record.get("completion_status")

                )

                st.write(

                    "**Review status:**",

                    record.get("review_status")

                )

                st.write(

                    "**Professional attention flag:**",

                    record.get("professional_attention")

                )

                st.write(

                    "**Reviewer decision:**",

                    record.get("reviewer_decision")

                )

                st.write(

                    "**Validation:**",

                    record.get("validation", {})

                )

                if record.get("summary"):

                    st.markdown(
                        record["summary"]
                    )


# ==================================================
# TAB 3: ABOUT THIS PROJECT
# ==================================================

with about_tab:

    st.header(
        "About the Project"
    )

    st.write(
        "Development of an Intelligent Mental Health "
        "Screening and Initial Assessment Agent Using LangGraph."
    )

    st.subheader(
        "Implemented Requirements"
    )

    st.markdown("""

    - Interactive collection of mood, stress, sleep,
      anxiety, daily functioning, and personal concerns.

    - Structured validation of missing, invalid,
      and possibly inconsistent answers.

    - Three LangChain tools: validate, save,
      and retrieve assessment records.

    - LangGraph StateGraph with a typed state schema
      and conditional routing.

    - SQLite storage for assessment records and
      SQLite checkpointing for workflow progress.

    - AI-generated summary with a deterministic fallback.

    - Reflection checks for required sections,
      reported values, and safe scope language.

    - Human-in-the-Loop approval or change request.

    - Execution logs written to data/agent.log.

    - Five synthetic test scenarios, including
      checkpoint interruption and resume.

    """)

    st.subheader(
        "Technology Stack"
    )

    st.write(
        "Python, Streamlit, LangChain, LangGraph, "
        "Ollama/Qwen, and SQLite."
    )

    st.caption(
        "This is a coursework prototype, not a clinically "
        "validated screening instrument or emergency service."
    )