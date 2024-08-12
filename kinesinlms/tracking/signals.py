""" Signals for tracking app. We listen for key events and log them to our tracking log. """

import logging

import allauth
# Hooking into AllAuth signals here for analytics tracking
from allauth.account.signals import email_confirmed
from allauth.account.signals import user_logged_in
from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)


# noinspection PyUnusedLocal
@receiver(user_signed_up)
def user_signed_up(request, user, **kwargs):
    """
    Listen for sign up and log event to tracking log.

    Args:
        request:
        user:
        kwargs:

    Returns:
        ( nothing )
    """
    Tracker.track(event_type=TrackingEventType.USER_REGISTRATION.value,
                  user=user,
                  event_data={},
                  course=None)


# noinspection PyUnusedLocal
@receiver(email_confirmed)
def user_email_confirmed(request, email_address: [allauth.account.models.EmailAddress], **kwargs):
    """
    Listen for email confirmation and log event to tracking log.

    Args:
        request:
        email_address: This is an AllAuth EmailAddress object, not a string!
        kwargs:

    Returns:
        ( nothing )

    """
    Tracker.track(event_type=TrackingEventType.USER_EMAIL_CONFIRMED.value,
                  user=email_address.user,
                  event_data={"email": email_address.email},
                  course=None)


# noinspection PyUnusedLocal
@receiver(user_logged_in)
def user_logged_in(request, user, **kwargs):
    """
    Listen for user login and log event to tracking log.

     Args:
        request:
        user:
        kwargs:

    Returns:
        ( nothing )
    """
    Tracker.track(event_type=TrackingEventType.USER_LOGIN.value,
                  user=user,
                  event_data={},
                  course=None)
