from typing import Dict
import logging

from kinesinlms.email_automation.models import EmailAutomationProvider, CourseEmailAutomationSettings
from kinesinlms.email_automation.tasks import add_tag_to_user, register_user_with_email_automation_provider, remove_tag_from_user
from kinesinlms.email_automation.utils import get_email_automation_provider
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.notifiers import TrackerEventHandler

debug_logger = logging.getLogger(__name__)


class EmailAutomationNotifier(TrackerEventHandler):
    """
    An event notifier is responsible for telling an external service
    about a tracking event that just occurred in our system.

    Requests to the external service are made asynchronously via Celery,
    as they should not block the main request, and multiple tries should be made
    in case of failure.

    """

    @classmethod
    def handle_tracker_event(cls, event_dict: Dict, user_id: int, course_id=None, **kwargs) -> bool:
        """
        A user event just happened. Decide here if we want to
        send this event to our email automation system.

        Args:
            event_dict:      Dictionary for event
            user_id:         The user id, if any, associated with this event.
            course_id:       If this event is associated with a course, the course id.

        Returns:
            Boolean flag indicating whether event was handled.
        """

        email_automation_provider: EmailAutomationProvider = get_email_automation_provider()
        if not email_automation_provider.enabled:
            # Ignore this event
            return False

        # Make sure we handle this event either globally or at the course level.
        GLOBAL_HANDLED_EVENTS = [
            TrackingEventType.USER_EMAIL_CONFIRMED.value
        ]

        event_type_value = event_dict['event_type']
        if event_type_value not in GLOBAL_HANDLED_EVENTS:
            # This is a course-related event
            # Let's check whether it's enabled for this course.
            if course_id:
                email_settings, created = CourseEmailAutomationSettings.objects.get_or_create(course_id=course_id)
                if not email_settings.is_event_enabled(event_type_value):
                    # Ignore this event...it's not enabled for this course
                    return False
            else:
                # Not a global event and no course_id provided,
                # so nothing we can do.
                return False

        # OK to send!
        course_slug = event_dict.get('course_slug', None)
        course_run = event_dict.get('course_run', None)
        if course_slug and course_run:
            tag = f"{course_slug}_{course_run}:{event_type_value}"
        else:
            tag = event_type_value
        cls.set_tag(tag=tag, user_id=user_id)

        return True

    @classmethod
    def register_user(cls, user_id: int, authorized_email: str):
        """
        Start an async task to register a new user in an email
        automation system.

        Args:
            user_id:            ID of user to register
            authorized_email:   The email authorized by Allauth.
        """
        provider: EmailAutomationProvider = get_email_automation_provider()
        if provider and provider.enabled:
            register_user_with_email_automation_provider.apply_async(
                args=[],
                kwargs={
                    "user_id": user_id,
                    "provider_id": provider.id,
                    "authorized_email": authorized_email
                },
                countdown=1)

    @classmethod
    def set_tag(cls, tag: str, user_id: int):
        """
        Start an async task to add a tag to a contact in
        an email automation system.
        """
        provider: EmailAutomationProvider = get_email_automation_provider()
        if provider and provider.enabled:
            add_tag_to_user.apply_async(args=[],
                                        kwargs={
                                            "tag": tag,
                                            "user_id": user_id,
                                            "provider_id": provider.id
                                        },
                                        countdown=5)

    @classmethod
    def remove_tag(cls, tag: str, user_id: int):
        """
        Start an async task to remove a tag from a contact in
        an email automation system.
        """
        provider: EmailAutomationProvider = get_email_automation_provider()
        if provider and provider.enabled:
            remove_tag_from_user.apply_async(args=[],
                                             kwargs={
                                                 "tag": tag,
                                                 "user_id": user_id,
                                                 "provider_id": provider.id
                                             },
                                             countdown=5)
