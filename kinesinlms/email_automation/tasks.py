import logging
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model

from config import celery_app
from kinesinlms.email_automation.clients.active_campaign_client import NoActiveCampaignTagIDDefined
from kinesinlms.email_automation.service import EmailAutomationService
from kinesinlms.email_automation.utils import get_email_automation_service

logger = logging.getLogger(__name__)

User = get_user_model()


# ASYNC TASKS THAT COMMUNICATE WITH EMAIL AUTOMATION PROVIDER
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
def register_user_with_email_automation_provider(user_id: int,
                                                 provider_id: int,
                                                 authorized_email: str) -> Optional[str]:
    """
    Registers a new user with our external email automation service.

    It's assumed that user has already validated their email, so don't
    call this task until you know email has been validated in our own system.

    IMPORTANT: When we create a user with the email automation provider, the
    provider should return an ID string for that user that we can use later for
    that user. We save it as `email_automation_provider_user_id` in the user model.

    Args:

        user_id:                ID of User who just validated their email (and therefore has successfully registered)
                                The ActiveCampaign contact ID if user was created, otherwise None
        provider_id:            ID of EmailAutomationProvider to use to register user
        authorized_email:       The email authorized by Allauth.

    Returns:
        The user's ID from the email service.

    """
    if user_id is None:
        raise ValueError("user_id is required")
    if provider_id is None:
        raise ValueError("provider_id is required")

    service: EmailAutomationService = get_email_automation_service()

    logger.info(f"Trying to add user id {user_id} to email automation provider")
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist as e:
        logger.exception(f"Could not find user by id {user_id}")
        raise e

    # GET CONTACT ID IF USER EMAIL ALREADY EXISTS IN AC...
    # They might be there b/c they used v1.
    existing_contact_id = None
    try:
        # Make sure to use the email address that was validated by Allauth.
        existing_contact_id = service.get_contact_id(authorized_email)
        if existing_contact_id:
            logger.info(f"User already exists in email automation provider. "
                        f"Saving existing contact ID {existing_contact_id}")
    except Exception as e:
        # we'll create user in next step...
        logger.info(f"Error when checking for existing user : {e}. Ignoring...")

    if not existing_contact_id:
        email_automation_provider_user_id = service.add_contact(user=user,
                                                                authorized_email=authorized_email)
    else:
        email_automation_provider_user_id = existing_contact_id

    user.email_automation_provider_user_id = email_automation_provider_user_id
    user.save()

    return email_automation_provider_user_id


@celery_app.task(retry_backoff=True,
                 retry_kwargs={'max_retries': 3},
                 on_failure=task_error_handler)
def add_tag_to_user(tag: str,
                    user_id: int,
                    provider_id: int):
    if tag is None:
        raise ValueError("tag is required")
    if user_id is None:
        raise ValueError("user_id is required")
    if provider_id is None:
        raise ValueError("provider_id is required")

    service: EmailAutomationService = get_email_automation_service()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist as dne:
        logger.exception(f"Could not find user by id {user_id}")
        raise dne  # and retry...

    # If we're running on STAGING or DEVELOPMENT,
    # we only want to send messages to our external
    # service if this is a test user
    if settings.DJANGO_PIPELINE in ["DEVELOPMENT", "STAGING"] and not user.is_test_user:
        logger.warning(f"Skipping sending ActiveCampaign a tag. We're "
                       f"running in {settings.DJANGO_PIPELINE} and user "
                       f"{user} IS NOT a test user.")
        return None  # no need to retry...

    if not user.email_automation_provider_user_id:
        logger.exception(f"Could not notify email automation provider because user {user} "
                         f"does not have email_automation_provider_user_id defined!")
        return None  # no need to retry...

    try:
        service.add_tag_to_contact(user=user,
                                   tag=tag)
        logger.debug(f"Updated username {user.username} contact in email automation provider "
                     f"to have tag ID {tag} ")
    except NoActiveCampaignTagIDDefined:
        logger.error(f"Could not add a tag to email automation provider contact because "
                     f"tag does not exist. "
                     f"tag: {tag} user_id: {user_id}")
    except Exception as e:
        logger.exception(f"Could not add a tag to email automation provider contact. "
                         f"tag: {tag} user_id: {user_id}")
        raise e  # and retry...


@celery_app.task(retry_backoff=True,
                 retry_kwargs={'max_retries': 3},
                 on_failure=task_error_handler)
def remove_tag_from_user(tag: str,
                         user_id: int,
                         provider_id: int):
    if tag is None:
        raise ValueError("tag is required")
    if user_id is None:
        raise ValueError("user_id is required")
    if provider_id is None:
        raise ValueError("provider_id is required")

    service: EmailAutomationService = get_email_automation_service()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist as dne:
        logger.info(f"Could not find user by id {user_id}")
        raise dne  # and retry...

    # If we're running on STAGING or DEVELOPMENT,
    # we only want to send messages to our external
    # service if this is a test user
    if settings.DJANGO_PIPELINE in ["DEVELOPMENT", "STAGING"] and not user.is_test_user:
        logger.warning(f"Skipping sending email automation provider a tag. We're "
                       f"running in {settings.DJANGO_PIPELINE} and user "
                       f"{user} IS NOT a test user.")
        return None  # no need to retry...

    if not user.email_automation_provider_user_id:
        logger.exception(f"Could not notify email automation provider because user {user} "
                         f"does not have email_automation_provider_user_id defined!!")
        return None  # no need to retry...

    try:
        service.remove_tag_from_contact(user=user,
                                        tag=tag)
        logger.debug(f"Updated username {user.username} contact in email service "
                     f" (email_automation_provider_user_id {user.email_automation_provider_user_id} "
                     f"to remove tag ID {tag}")
    except Exception as e:
        logger.exception(f"Could not remove a tag from email service contact. "
                         f"tag: {tag} user_id: {user_id}")
        raise e  # and retry...
