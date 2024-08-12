import logging

import allauth.account.models
from allauth.account.signals import email_confirmed
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from kinesinlms.email_automation.utils import get_email_automation_service
from kinesinlms.forum.utils import get_forum_service
from kinesinlms.users.models import UserSettings, InviteUser
from kinesinlms.users.utils import process_invite_user

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def save_user_signal(sender, instance, created, **kwargs):  # noqa: F841
    """Create a UserSettings object if one doesn't exist when a user is created."""
    if created:
        UserSettings.objects.create(user=instance)


@receiver(post_delete, sender=User)
def user_deleted_signal(sender, instance, **kwargs):
    """
    Perform any actions required after a user is deleted.
    """

    # Remove any InviteUsers for this user's email.
    try:
        InviteUser.objects.filter(email=instance.email).delete()
        logger.debug(f"Removed Invite user for {instance.email}")
    except Exception:
        logger.exception("Could not remove InviteUsers during user_deleted_signal().")


# @receiver(user_signed_up)
# def user_signed_up(request, user, **kwargs):
#    pass


@receiver(email_confirmed)
def email_confirmed(
    request, email_address: "allauth.account.models.EmailAddress", **kwargs
):
    """
    When a user clicks the confirmation link in their welcome email after signing up,
    we may want to do some things right away, such as
     - adding them to ActiveCampaign.
     - enrolling them in any courses they've been invited to and marked for autoenroll
     - add to Discourse
     - add to general 'users' group in Django.

    Those things should go here in this signal handler.

    It's important that exceptions are caught as we don't want to prevent the registration
    from going through.

    """
    if hasattr(email_address, "user"):
        # Only do this if we're running in PRODUCTION
        if settings.DJANGO_PIPELINE == "PRODUCTION":
            # Use celery task to register user in ActiveCampaign...
            logger.info(
                f"User confirmed email address {email_address}. Let's add them to ActiveCampaign."
            )
            try:
                user = email_address.user
                email_service = get_email_automation_service()
                result = email_service.register_user(
                    user_id=user.id, authorized_email=email_address.email
                )
                logger.debug(f"Celery async result {result}")
            except Exception:
                logger.exception(
                    f"email_confirmed() SIGNAL: Could not launch celery "
                    f"task to add user {email_address} to ActiveCampaign "
                )
    else:
        logger.error(
            f"email_confirmed() SIGNAL: Can't access user via email_address.user "
            f"property. email_address {email_address}"
        )

    # Add to external forum
    new_student = email_address.user
    try:
        if settings.DJANGO_PIPELINE in ["STAGING", "PRODUCTION"]:
            """
            Sync user with forum SSO. We want to do this right after student signs up
            otherwise Discourse only creates an SSO user when they first visit (and therefore it
            won't know who the user is if we try to do something after they register on v2 but
            before they visit Discourse, e.g. they have enrolled in a course, and we
            want Discourse to add them to a group.)
            """
            forum_service = get_forum_service()
            forum_service.sync_discourse_sso_user(user=new_student)

    except Exception:
        logger.exception("email_confirmed() SIGNAL: Could not sync Discourse SSO user")

    # Process InviteUser if necessary
    try:
        invite_user = InviteUser.objects.get(email__icontains=new_student.email)
    except InviteUser.DoesNotExist:
        invite_user = None

    if invite_user:
        return_messages = None
        try:
            return_messages = process_invite_user(
                new_user=new_student, invite_user=invite_user
            )
        except Exception:
            logger.exception(
                f"email_confirmed() SIGNAL: Could not "
                f"process invite_user: {invite_user}"
            )

        if return_messages:
            try:
                for return_message_type, return_message in return_messages:
                    messages.add_message(request, return_message_type, return_message)
            except Exception:
                logger.exception(
                    "email_confirmed() SIGNAL: Could not send "
                    "return messages to client"
                )
