"""
Define event notifiers that send tracking events to external services.
Some core notifiers are defined here. Others may be defined in other
apps (e.g. email_automation).
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict

from django.conf import settings

from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tasks import send_tracking_event_to_aws, send_tracking_event_to_slack

debug_logger = logging.getLogger(__name__)


class TrackerEventHandler(ABC):
    """
    Base class for all event notifiers.
    An event notifier is responsible for telling an external service
    about an event that just occurred in our system.
    """

    @classmethod
    @abstractmethod
    def handle_tracker_event(cls, event_dict: Dict, user_id: int, **kwargs) -> bool:
        """
        Handle a tracking event. This method should be overridden by
        subclasses to handle specific events.

        Returns:
            Boolean flag indicating whether event was handled.
        """
        pass


class AWSNotifier(TrackerEventHandler):

    @classmethod
    def handle_tracker_event(cls, event_dict: Dict, user_id: int, coures_id=None, **kwargs) -> bool:
        """
        Send event to AWS Lambda. From there we'll save it to CloudWatch

        Writing to log isn't as efficient, as there's no easy way
        to get json logs out of Heroku via log drain. So for now I'm writing
        events directly to Lambda via boto3 using Celery.

        Args:
            event_dict:     Dictionary of event data to send to AWS Lambda
            user_id:        ID of user associated with event, if any.
            coures_id:      ID of course associated with event, if any.

        Returns:
            Boolean flag indicating whether event was handled.

        """

        if not settings.AWS_KINESINLMS_EVENTS_LAMBDA:
            # Skipping AWS notification for event. No lambda function configured.
            return False

        # Launch the celery task
        send_tracking_event_to_aws.delay(event_dict=event_dict)

        return True


class SlackNotifier(TrackerEventHandler):
    HANDLE_EVENTS = [
        TrackingEventType.USER_REGISTRATION.value,
        TrackingEventType.USER_LOGIN.value,
        TrackingEventType.ENROLLMENT_ACTIVATED.value,
        TrackingEventType.ENROLLMENT_DEACTIVATED.value,
        TrackingEventType.COURSE_PAGE_VIEW.value,
        TrackingEventType.COURSE_VIDEO_ACTIVITY.value,
        TrackingEventType.COURSE_RESOURCE_DOWNLOAD.value,
        TrackingEventType.COURSE_BLOCK_RESOURCE_DOWNLOAD.value,
        TrackingEventType.COURSE_ASSESSMENT_ANSWER_SUBMITTED.value,
        TrackingEventType.COURSE_BOOKMARKS_VIEW.value,
        TrackingEventType.COURSE_CERTIFICATE_VIEW.value,
        TrackingEventType.COURSE_CUSTOM_APP_PAGE_VIEW.value,
        TrackingEventType.COURSE_EXTRA_PAGE_VIEW.value,
        TrackingEventType.COURSE_HOME_VIEW.value,
        TrackingEventType.COURSE_PROGRESS_VIEW.value,
        TrackingEventType.COURSE_SEARCH_REQUEST.value,
        TrackingEventType.SURVEY_COMPLETED.value
    ]

    @classmethod
    def handle_tracker_event(cls,
                             event_dict: Dict,
                             user_id: int,
                             course_id: int = None,
                             slack_message: str = None) -> bool:
        """
        Start async task to send event to Slack *if* it's an event
        that should show up there.

        Args:
            event_dict:     Dictionary of event data to send to AWS Lambda
            user_id:        ID of user associated with event, if any.
            course_id:      ID of course associated with event, if any.
            slack_message:  An extra, slack-specific message, if any.

        Returns:
            Boolean flag indicating whether event was handled.
        """
        event_type = event_dict['event_type']
        if event_type not in SlackNotifier.HANDLE_EVENTS:
            return False

        # Launch the celery tasks
        send_tracking_event_to_slack.delay(event_dict, slack_message)

        return True
