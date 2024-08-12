import logging

from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kinesinlms.course.constants import MilestoneType
from kinesinlms.course.models import Course
from kinesinlms.course.tasks import track_milestone_progress
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.serializers import APITrackingEventSerializer
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~
# DRF Classes...
# ~~~~~~~~~~~~~~~~~~~~~~~


class TrackingViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Handle incoming tracking events from client via the API.
    Because events are coming from API, we place additional
    restrictions on the data above what's usually required for a
    tracking event.

    Most importantly, the extra restrictions include:
    - the user and course are required.
    - the user cannot be anonymous or null and must be enrolled
      in the course defined in the event.
    """

    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    serializer_class = APITrackingEventSerializer

    def create(self, request, *args, **kwargs):
        """
        We override the create() method b/c after
        validation and saving TrackingEvent we want to send
        it on via the Tracker to things like AWS logs
        and Slack.

        Args:
            request:
            args:
            kwargs:

        Return:
            HTTP response
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tracking_event = serializer.save(anon_username=request.user.anon_username)
        headers = self.get_success_headers(serializer.data)

        # Course run and slug will have been validated by serializer.
        course_slug = serializer.validated_data['course_slug']
        course_run = serializer.validated_data['course_run']
        block_uuid = serializer.validated_data['block_uuid']
        course = Course.objects.get(slug=course_slug, run=course_run)

        try:
            # Launch tracking event
            Tracker.notify(user=request.user, event=tracking_event, course=course)
        except Exception:
            # Log error but keep tracking event as we want it stored in DB.
            logger.error(f"Could not emit tracking event arriving "
                         f"via API: event{tracking_event} ")

        # VIDEO-SPECIFIC EVENTS
        # Right now we only expect video activity tracking events via the API, but later
        # we might have others so be explicit here...
        event_type = serializer.validated_data['event_type']
        logger.debug(f"Handing event of type: {event_type}")
        if event_type == TrackingEventType.COURSE_VIDEO_ACTIVITY.value:
            # Do any extra stuff, for video events, like updating milestones
            try:
                track_milestone_progress.apply_async(
                    args=[],
                    kwargs={
                        "course_id": course.id,
                        "user_id": request.user.id,
                        "block_uuid": block_uuid,
                    },
                )
            except Exception:
                logger.exception(f"Saved tracking event but error in "
                                 f"track_milestone_progress(). ")
                pass

        response_data = {
            "tracking_event_type": tracking_event.event_type,
            "received": True
        }
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
