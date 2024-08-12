import logging
from typing import Optional

from django.conf import settings

from kinesinlms.course.exceptions import CourseFinishedException
from kinesinlms.course.models import Course
from kinesinlms.email_automation.notifiers import EmailAutomationNotifier
from kinesinlms.email_automation.utils import get_email_automation_provider
from kinesinlms.tracking.event_types import ALL_VALID_EVENTS, POST_COURSE_TRACKED_EVENTS, ANON_USER_VALID_EVENTS
from kinesinlms.tracking.models import TrackingEvent
from kinesinlms.tracking.notifiers import AWSNotifier
from kinesinlms.tracking.notifiers import SlackNotifier
from kinesinlms.tracking.serializers import TrackingEventSerializer

tracking_logger = logging.getLogger("Tracker")
debug_logger = logging.getLogger(__name__)


class Tracker(object):
    """
    This class :
    - saves events to the database
    - asks various 'notifiers' to tell external services about events that just occurred.
    """

    @classmethod
    def track(cls,
              event_type,
              user=None,
              course=None,
              event_data=None,
              **kwargs) -> bool:
        """
        This method does two main things:
            -   Create and save a TrackingEvent for an event that just occurred.
                (The TrackingEventSerializer is used to save the event)
            -   Emit that same event as a json message to any services that need to know.

        This method should fail silently so the calling method isn't
        derailed from doing the main task it was working on.

        Args:
            event_type:
            user:
            course:
            event_data:

        Returns:
            Boolean flag indicating whether event was tracked.
        """

        # Save TrackingEvent
        if event_type not in ALL_VALID_EVENTS:
            debug_logger.exception(f"Invalid event type {event_type} kwargs: {kwargs}")
            return False

        if not kwargs:
            data = {}
        else:
            data = kwargs

        data['event_type'] = event_type
        data['event_data'] = event_data

        if course:
            data['course_slug'] = course.slug
            data['course_run'] = course.run

        if user:
            if user.is_anonymous:
                if event_type in ANON_USER_VALID_EVENTS:
                    data['anon_username'] = None
                    data['user'] = None
                else:
                    debug_logger.warning(f"Event had anonymous user: {data}. IGNORING")
                    return False
            else:
                data['anon_username'] = user.anon_username
                data['user'] = user.id

        try:
            serializer = TrackingEventSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            tracking_event = serializer.save()
        except CourseFinishedException:
            debug_logger.info(f"Ignore event event_type {event_type} user {user} "
                              f"course {course} kwargs {kwargs} because course has already finished. ")
            return False
        except Exception:
            debug_logger.exception(f"Could not track event : event_type {event_type} user {user} "
                                   f"course {course} kwargs {kwargs}  ")
            return False

        # Notify any external services about event
        try:
            cls.notify(user=user, event=tracking_event, course=course)
        except Exception:
            debug_logger.exception(f"Could not emit event! user: {user} event: {tracking_event}")
            return False

        # All done!
        return True

    @classmethod
    def notify(cls, user, event: TrackingEvent, course: Optional[Course] = None):
        """
        Parse a previously-saved TrackingEvent and notify various external services.

        For best performance, the sending of events to each target service should
        be handled asynchronously via Celery.

        Args:
            user:           Instance of user related to this action.
            event:          TrackingEvent instance.
            course:         Course instance, if any, related to this action.

        Returns:
            ( nothing )
        """

        serializer = TrackingEventSerializer(event)
        event_dict = serializer.data

        if course:
            course_id = course.id
            # If a course has finished, the only thing we track are things like interactions with videos.
            if course.has_finished and event.event_type not in POST_COURSE_TRACKED_EVENTS:
                debug_logger.warning(f"Not emitting event {event} as course is finished and this event"
                                     f"is not in the POST_COURSE_TRACKED_EVENTS")
                raise CourseFinishedException()
        else:
            course_id = None

        email_automation_provider = get_email_automation_provider()
        if email_automation_provider and email_automation_provider.enabled:
            try:
                EmailAutomationNotifier.handle_tracker_event(event_dict=event_dict,
                                                             user_id=user.id,
                                                             course_id=course_id)
            except Exception as e:
                debug_logger.exception(f"Could not send tracking event to"
                                       f" ActiveCampaignNotifier: {event_dict}: {e}")

        if settings.AWS_KINESINLMS_EVENTS_LAMBDA:
            try:
                AWSNotifier.handle_tracker_event(event_dict=event_dict,
                                                 user_id=user.id,
                                                 course_id=course_id)
            except Exception:
                debug_logger.exception(f"Could not send tracking event to AWS Lambda: {event_dict}")

        if settings.SLACK_TOKEN:
            try:
                event_message = event.get_nice_message()
                SlackNotifier.handle_tracker_event(event_dict=event_dict,
                                                   user_id=user.id,
                                                   slack_message=event_message,
                                                   course_id=course_id)
            except Exception:
                debug_logger.exception(f"Could not send tracking event to SlackNotifier: {event_dict}")
