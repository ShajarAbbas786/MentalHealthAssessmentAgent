"""Automated tests for all five assessment scenarios."""

import unittest
import uuid

from sample_data import SYNTHETIC_CASES

from tools import (
    validate_answers,
    get_attention_reasons
)

from agent import (
    run_assessment,
    resume_assessment,
    resume_interrupted_assessment
)

from database import get_record


class AssessmentValidationTests(unittest.TestCase):

    # ----------------------------------------------
    # TEST 1: COMPLETE ASSESSMENT
    # ----------------------------------------------

    def test_1_complete_assessment(self):

        assessment_id = (
            "test-complete-" + str(uuid.uuid4())
        )

        answers = dict(
            SYNTHETIC_CASES["complete_assessment"]
        )

        result = run_assessment(
            assessment_id,
            answers
        )

        self.assertEqual(
            result.get("completion_status"),
            "complete"
        )

        # A complete assessment must pause
        # for Human-in-the-Loop review.

        self.assertTrue(
            result.get("__interrupt__")
        )

        reviewed = resume_assessment(
            assessment_id,
            "approved",
            "Synthetic test review approved."
        )

        self.assertEqual(
            reviewed.get("review_status"),
            "approved"
        )

        record = get_record(assessment_id)

        self.assertIsNotNone(record)

        self.assertEqual(
            record["completion_status"],
            "complete"
        )


    # ----------------------------------------------
    # TEST 2: MISSING RESPONSES
    # ----------------------------------------------

    def test_2_missing_responses(self):

        assessment_id = (
            "test-missing-" + str(uuid.uuid4())
        )

        answers = dict(
            SYNTHETIC_CASES["missing_responses"]
        )

        result = run_assessment(
            assessment_id,
            answers
        )

        self.assertEqual(
            result.get("completion_status"),
            "incomplete"
        )

        self.assertIn(
            "Anxiety experience",
            result["validation"]["missing_fields"]
        )

        self.assertTrue(
            result.get("summary")
        )

        self.assertEqual(
            result.get("review_status"),
            "not_required"
        )

        record = get_record(assessment_id)

        self.assertIsNotNone(record)


    # ----------------------------------------------
    # TEST 3: CONFLICTING RESPONSES
    # ----------------------------------------------

    def test_3_conflicting_responses(self):

        assessment_id = (
            "test-conflict-" + str(uuid.uuid4())
        )

        answers = dict(
            SYNTHETIC_CASES["conflicting_responses"]
        )

        result = run_assessment(
            assessment_id,
            answers
        )

        self.assertTrue(
            result["validation"]["inconsistencies"]
        )

        # The complete assessment is sent
        # for professional review.

        self.assertTrue(
            result.get("__interrupt__")
        )

        reviewed = resume_assessment(
            assessment_id,
            "approved",
            "Conflict noted for professional clarification."
        )

        self.assertEqual(
            reviewed.get("review_status"),
            "approved"
        )


    # ----------------------------------------------
    # TEST 4: SIGNIFICANT DISTRESS
    # ----------------------------------------------

    def test_4_significant_distress(self):

        assessment_id = (
            "test-distress-" + str(uuid.uuid4())
        )

        answers = dict(
            SYNTHETIC_CASES["significant_distress"]
        )

        reasons = get_attention_reasons(
            answers
        )

        self.assertTrue(reasons)

        self.assertTrue(
            any(
                "YES" in reason
                for reason in reasons
            )
        )

        result = run_assessment(
            assessment_id,
            answers
        )

        # The case must be routed to
        # summary generation and human review.

        self.assertTrue(
            result.get("__interrupt__")
        )

        self.assertTrue(
            result.get("professional_attention")
        )

        reviewed = resume_assessment(
            assessment_id,
            "needs_changes",
            "Synthetic priority case requires further review."
        )

        self.assertEqual(
            reviewed.get("review_status"),
            "needs_changes"
        )


    # ----------------------------------------------
    # TEST 5: INTERRUPTED AND RESUMED ASSESSMENT
    # ----------------------------------------------

    def test_5_interrupted_and_resumed_checkpoint(self):

        assessment_id = (
            "test-interruption-" + str(uuid.uuid4())
        )

        answers = dict(
            SYNTHETIC_CASES["interrupted_assessment"]
        )

        # Start assessment and pause before
        # the incomplete node.

        first = run_assessment(

            assessment_id,

            answers,

            pause_before_incomplete=True

        )

        # Check that the record was saved.

        self.assertIsNotNone(
            get_record(assessment_id)
        )

        # Summary should not exist yet because
        # the graph is paused before the node.

        self.assertFalse(
            first.get("summary")
        )

        # Resume the same graph thread.

        resumed = resume_interrupted_assessment(
            assessment_id
        )

        self.assertTrue(
            resumed.get("summary")
        )

        self.assertEqual(
            resumed.get("completion_status"),
            "incomplete"
        )

        self.assertIn(

            "Personal concerns",

            resumed["validation"]["missing_fields"]

        )

        # Confirm final record exists.

        record = get_record(
            assessment_id
        )

        self.assertIsNotNone(record)

        self.assertEqual(
            record["completion_status"],
            "incomplete"
        )


# ==================================================
# RUN ALL TESTS
# ==================================================

if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )