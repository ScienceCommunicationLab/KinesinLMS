import logging

from celery import Task
from django.contrib.auth import get_user_model

from config import celery_app
from kinesinlms.badges.models import BadgeAssertion, BadgeAssertionCreationStatus
from kinesinlms.badges.utils import get_badge_service

logger = logging.getLogger(__name__)

User = get_user_model()


def create_external_badge_assertion_task_error_handler(self, exc, task_id, args, kwargs, einfo):  # noqa: F841
    """
    Handles any exceptions that occur when the create_external_badge_assertion_task can't
    complete, even after being auto-retried multiple times.

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

    logger.error(f"CREATE BADGE ASSERTION TASK FAILURE: Task id {task_id} not complete. \n"
                 f"  exception : {exc} \n"
                 f"  args: {args} \n"
                 f"  kwargs: {kwargs} \n"
                 f"  einfo: {einfo} \n")


# noinspection PyUnusedLocal
@celery_app.task(bind=True,
                 autoretry_for=[BadgeAssertion.DoesNotExist],
                 retry_backoff=True,
                 time_limit=60 * 2,
                 soft_time_limit=60 * 1,
                 retry_kwargs={
                     'max_retries': 3
                 },
                 on_failure=create_external_badge_assertion_task_error_handler)
def create_external_badge_assertion_task(self: Task, badge_assertion_id: int):
    """
    Contact external badge service to create a badge assertion for a
    recipient who just achieved the requirements defined in a BadgeClass.

    This task assumes:
        - a BadgeProvider instance has already been set up locally, with the external service's information.
        - a Badge class has been set up in that external service to reflect our local BadgeClass
        - a local BadgeAssertion has *already* been created for the recipient and badge class.

    All we need to do here in this task is create the assertion in the external service and
    save the returned open badge id for that new assertion (the open badge id is just an url).

    Args:
        self:                    Instance of Celery task.
        badge_assertion_id:      ID of BadgeAssertion describing recipient and badge class.

    Returns:
        ( nothing )
    """

    try:
        badge_assertion = BadgeAssertion.objects.get(id=badge_assertion_id)
    except BadgeAssertion.DoesNotExist as dne:
        logger.error(f"BadgeAssertion with id {badge_assertion_id} not found.")
        raise dne
    except Exception as e:
        logger.error(f"Error when trying to retrieve BadgeAssertion with id {badge_assertion_id}. \n"
                     f"  exception : {e}")
        raise e
    badge_assertion.creation_status = BadgeAssertionCreationStatus.IN_PROGRESS.name
    badge_assertion.save()

    logger.debug(f"create_external_badge_assertion_task() Starting...  (badge assertion: {badge_assertion}")
    service = get_badge_service()
    service.create_remote_badge_assertion(badge_assertion)

    logger.info(f"Created remote badge assertion for {badge_assertion}. "
                f"open_badge_id : {badge_assertion.open_badge_id}")

    return True
