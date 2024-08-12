import logging

from kinesinlms.assessments.models import SubmittedAnswer
from kinesinlms.course.models import CourseUnit
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)


def track_answer_submission(submitted_answer: SubmittedAnswer,
                            course_unit: CourseUnit = None,
                            previous_answer_status: str = None):
    """
    Record a tracking event for the student's submission.
    This doesn't mean it was accepted or grade, just that they submitted it.

    Args:

        submitted_answer:           An instance of a SubmittedAnswer object, representing the students
                                    answer to the Assessment
        course_unit:                An instance of the CourseUnit the student answers this assessment in,
                                    if available.
        previous_answer_status:     The previous status of the answer, should be string from
                                    AnswerStatus Enum.

    Returns:
        ( nothing )
    """
    try:
        data = submitted_answer.get_answer_data_for_tracking_log()
        data['previous_answer_status'] = previous_answer_status
        block = submitted_answer.assessment.block
        unit_node_slug = None
        if course_unit:
            course_unit_id = course_unit.id
            course_unit_slug = course_unit.slug
        else:
            course_unit_id = None
            course_unit_slug = None
        course = submitted_answer.course
        Tracker.track(event_type=TrackingEventType.COURSE_ASSESSMENT_ANSWER_SUBMITTED.value,
                      user=submitted_answer.student,
                      event_data=data,
                      course=course,
                      unit_node_slug=unit_node_slug,
                      course_unit_id=course_unit_id,
                      course_unit_slug=course_unit_slug,
                      block_uuid=block.uuid)
    except Exception:
        # Fail silently...we want answer to be saved even if we didn't track it.
        logger.exception("#SubmittedAnswerSerializer: Couldn't log tracking event for "
                         "assessment answer submission .")

    return submitted_answer
