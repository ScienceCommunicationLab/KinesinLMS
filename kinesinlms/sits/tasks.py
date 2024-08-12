import logging

from celery import Task
from django.contrib.auth import get_user_model

from config import celery_app
from kinesinlms.course.models import CourseUnit
from kinesinlms.sits.models import SimpleInteractiveToolSubmission
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)

User = get_user_model()


def track_simple_interactive_tool_submission_error_handler(self, exc, task_id, args, kwargs, einfo):  # noqa: F841
    """
    Handles any exceptions that occur when the track_simple_interactive_tool_submission task can't
    complete (including after being auto-retried multiple times).

    Args:
        self:
        exc:
        task_id:
        args:
        kwargs:
        einfo:

    Returns:
        ( nothing )
    """

    # This should get sent to Sentry
    logger.error(f"TRACK SIMPLE INTERACTIVE TOOL SUBMISSION ERROR: Task id {task_id} not complete. \n"
                 f"  exception : {exc} \n"
                 f"  args: {args} \n"
                 f"  kwargs: {kwargs} \n"
                 f"  einfo: {einfo} \n")


@celery_app.task(bind=True,
                 autoretry_for=(Exception,),
                 time_limit=60 * 2,
                 retry_backoff=True,
                 soft_time_limit=60 * 1,
                 retry_kwargs={'max_retries': 10},
                 on_failure=track_simple_interactive_tool_submission_error_handler)
def track_simple_interactive_tool_submission(
        self: Task,
        simple_interactive_tool_submission_id: int,
        course_unit_id: int = None,
        previous_simple_interactive_tool_status: str = None):  # noqa: F841
    """
    Record a tracking event for the student's SimpleInteractiveTool submission.

    Args:

        self:                                               Instance of Celery task
        simple_interactive_tool_submission_id:              ID for instance of a SimpleInteractiveToolSubmission object,
                                                            representing the students latest submission.
        course_unit_id:                                     ID for instance of the CourseUnit the student submitted this
                                                            SimpleInteractiveTool in.
        previous_simple_interactive_tool_status:            The previous status of the SimpleInteractiveToolSubmission,
                                                            should be string from AnswerStatus Enum.

    Returns:
        boolean flag indicating success

    """
    sit_submission = SimpleInteractiveToolSubmission.objects.get(
        id=simple_interactive_tool_submission_id)

    data = sit_submission.get_data_for_tracking_log()
    data['previous_simple_interactive_tool_status'] = previous_simple_interactive_tool_status
    block = sit_submission.simple_interactive_tool.block
    unit_node_slug = None

    if course_unit_id:
        course_unit = CourseUnit.objects.get(id=course_unit_id)
        course_unit_slug = course_unit.slug
    else:
        course_unit_slug = None

    course = sit_submission.course
    success = Tracker.track(event_type=TrackingEventType.COURSE_SIMPLE_INTERACTIVE_TOOL_SUBMITTED.value,
                            user=sit_submission.student,
                            event_data=data,
                            course=course,
                            unit_node_slug=unit_node_slug,
                            course_unit_id=course_unit_id,
                            course_unit_slug=course_unit_slug,
                            block_uuid=block.uuid)

    return success
