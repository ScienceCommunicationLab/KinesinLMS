import logging
from typing import Optional

from django.contrib.auth import get_user_model

from config import celery_app
from kinesinlms.course.exceptions import CourseFinishedException
from kinesinlms.course.milestone_monitor import MilestoneMonitor
from kinesinlms.course.models import Course
from kinesinlms.learning_library.models import Block

logger = logging.getLogger(__name__)

User = get_user_model()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# MILESTONE TRACKING TASKS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ERROR HANDLER FUNCTION.
def task_error_handler(self, exc, task_id, args, kwargs, einfo):  # noqa: F841
    """
    Handles any exceptions that occur when the task can't
    complete, even after being auto-retried multiple times.

    Args:
        self:                   A reference to the instance of the task.
        exc (Exception):        The exception object raised during task exec.
        task_id (str):          The unique identifier of the failed task.
        args (list):            The positional arguments passed to the task.
        kwargs (dict):          The keyword arguments passed to the task.
        einfo (ExceptionInfo):  An object containing information about the exception.

    Returns:
        None: This method does not return a value.

    """

    message = f"TASK ERROR: Task id {task_id} not complete. \n" \
              f"  exception : {exc} \n" \
              f"  args: {args} \n" \
              f"  kwargs: {kwargs} \n" \
              f"  einfo: {einfo} \n"
    # Let Sentry tell us what went wrong...
    logger.error(message)


@celery_app.task(retry_backoff=True,
                 retry_kwargs={'max_retries': 3},
                 on_failure=task_error_handler)
def track_milestone_progress(course_id: int,
                             user_id: int,
                             block_uuid: str,
                             **kwargs) -> bool:
    """
    Tracks progress towards the affected course milestones.

    Args:
        course_id:       ID of current course.
        user_id:         ID of User who just validated their email (and therefore has successfully registered)
        block_uuid:      UUID of the Block the user interacted with
        kwargs:          extra arguments to pass to tracking method, must be serializable.

    Returns:
        Boolean flag representing success of operation
    """
    logger.debug(f"track_milestone_progress() Tracking progress in course {course_id} "
                 f" for user {user_id} and block {block_uuid} ({kwargs})")

    mm = MilestoneMonitor()
    return mm.track_interaction_by_id(course_id=course_id,
                                      user_id=user_id,
                                      block_uuid=block_uuid,
                                      **kwargs)


@celery_app.task(retry_backoff=True,
                 retry_kwargs={'max_retries': 3},
                 on_failure=task_error_handler)
def remove_assessment_from_milestone_progress(course_id: int,
                                              user_id: Optional[int] = None,
                                              assessment_id: Optional[int] = None) -> int:
    """
    Removes assessment block(s) from the relevant MilestoneProgress objects

    Args:
        course_id:       ID of current course.
        user_id:         ID of User (optional), limit removals to this user's MilestoneProgress
        assessment_id:   ID of Assessment (optional), limit removals to this Assessment's MilestoneProgressBlocks

    Returns:
        Number of MilestoneProgress items updated or deleted.
    """
    mm = MilestoneMonitor()

    return mm.remove_assessment_from_progress_by_id(course_id=course_id,
                                                    user_id=user_id,
                                                    assessment_id=assessment_id)


@celery_app.task(retry_backoff=True,
                 retry_kwargs={'max_retries': 3},
                 on_failure=task_error_handler)
def rescore_assessment_milestone_progress(course_id: int,
                                          user_id: Optional[int] = None,
                                          assessment_id: Optional[int] = None) -> int:
    """
    Re-grades and re-scores the given assessment block(s) for the relevant MilestoneProgress objects.

    Args:
        course_id:       ID of current course.
        user_id:         ID of User (optional), limit re-scoring to this user's MilestoneProgress
        assessment_id:   ID of Assessment (optional), limit rescoring to this Assessment's MilestoneProgressBlocks

    Returns:
        Number of MilestoneProgress items updated.
    """
    mm = MilestoneMonitor()

    return mm.rescore_assessment_progress_by_id(course_id=course_id,
                                                user_id=user_id,
                                                assessment_id=assessment_id)
