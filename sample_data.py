"""Five synthetic records required by the assignment testing brief."""


SYNTHETIC_CASES = {

    # ----------------------------------------------
    # TEST CASE 1: COMPLETE ASSESSMENT
    # ----------------------------------------------

    "complete_assessment": {

        "participant_name": "Synthetic Person A",

        "age": 22,

        "mood_description": "My mood has been okay recently.",

        "mood_score": 6,

        "stress_level": 4,

        "sleep_hours": 7.0,

        "sleep_quality": "Good",

        "anxiety_experience": "Sometimes I worry before exams.",

        "daily_functioning": "I attend classes and complete my tasks.",

        "personal_concerns": "I am concerned about upcoming exams.",

        "self_harm_thoughts": "No"

    },


    # ----------------------------------------------
    # TEST CASE 2: MISSING RESPONSES
    # ----------------------------------------------

    "missing_responses": {

        "participant_name": "Synthetic Person B",

        "age": 24,

        "mood_description": "I feel tired.",

        "mood_score": 4,

        "stress_level": 6,

        "sleep_hours": 5.0,

        "sleep_quality": "Poor",

        "anxiety_experience": "",

        "daily_functioning": "I attend work.",

        "personal_concerns": "Workload is difficult.",

        "self_harm_thoughts": "No"

    },


    # ----------------------------------------------
    # TEST CASE 3: CONFLICTING RESPONSES
    # ----------------------------------------------

    "conflicting_responses": {

        "participant_name": "Synthetic Person C",

        "age": 21,

        "mood_description": "I feel very happy and positive.",

        "mood_score": 2,

        "stress_level": 3,

        "sleep_hours": 8.0,

        "sleep_quality": "Good",

        "anxiety_experience": "No major anxiety.",

        "daily_functioning": "Daily tasks are manageable.",

        "personal_concerns": "No major concerns.",

        "self_harm_thoughts": "No"

    },


    # ----------------------------------------------
    # TEST CASE 4: SIGNIFICANT DISTRESS
    # ----------------------------------------------

    "significant_distress": {

        "participant_name": "Synthetic Person D",

        "age": 27,

        "mood_description": "I feel overwhelmed.",

        "mood_score": 2,

        "stress_level": 9,

        "sleep_hours": 3.5,

        "sleep_quality": "Poor",

        "anxiety_experience": "Frequent worry affects my day.",

        "daily_functioning": "I am struggling to manage daily activities.",

        "personal_concerns": "I feel unable to cope with pressures.",

        "self_harm_thoughts": "Yes"

    },


    # ----------------------------------------------
    # TEST CASE 5: INCOMPLETE / INTERRUPTED
    # ----------------------------------------------

    "interrupted_assessment": {

        "participant_name": "Synthetic Person E",

        "age": 23,

        "mood_description": "I feel uncertain.",

        "mood_score": 5,

        "stress_level": 5,

        "sleep_hours": 6.0,

        "sleep_quality": "Fair",

        "anxiety_experience": "Some worry about studies.",

        "daily_functioning": "I manage most tasks.",

        "personal_concerns": "",

        "self_harm_thoughts": "Prefer not to say"

    }

}