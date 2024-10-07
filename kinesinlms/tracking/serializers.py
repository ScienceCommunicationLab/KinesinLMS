import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from kinesinlms.course.exceptions import CourseFinishedException
from kinesinlms.course.models import Course, Enrollment
from kinesinlms.tracking.event_types import TrackingEventType, ALL_VALID_EVENTS, ALL_VALID_VIDEO_EVENTS, \
    POST_COURSE_TRACKED_EVENTS
from kinesinlms.tracking.models import TrackingEvent

logger = logging.getLogger(__name__)

# These are the only events to be tracked via API
VALID_API_TRACKING_EVENT_TYPES = [TrackingEventType.COURSE_VIDEO_ACTIVITY.value]

User = get_user_model()


class VideoEventDataSerializer(serializers.Serializer):
    # This is the YouTube ID, like 'k519LgRBnEM'
    video_id = serializers.CharField(max_length=200, required=True, allow_null=False)
    video_event_type = serializers.CharField(max_length=200, required=True, allow_null=False)

    def validate(self, data):
        video_event_type = data.get('video_event_type')
        if video_event_type not in ALL_VALID_VIDEO_EVENTS:
            raise serializers.ValidationError(f"Invalid video_event_type {video_event_type}")
        return data


class APITrackingEventSerializer(serializers.ModelSerializer):
    """
    Serializes a 'tracking' event received via the API.
    Right now that just means events sent from our video component.
    Because this event is arriving via API, we have to be a bit
    stricter when validating.

    Because events are coming from API, we place additional
    restrictions on the data than what a more generic
    tracking event needs.

    Most importantly, the extra restrictions include:
    - the user and course are required.
    - the user cannot be anonymous or null and must be enrolled
      in the course defined in the event.

    """

    course_unit_id = serializers.IntegerField(allow_null=False,
                                              required=True)

    event_type = serializers.CharField(allow_null=False,
                                       required=True)

    event_data = serializers.JSONField(allow_null=True,
                                       required=False)

    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(),
                                              default=serializers.CurrentUserDefault())

    class Meta:
        model = TrackingEvent
        fields = (
            'event_type',
            'time',
            'user',
            'anon_username',
            'course_slug',
            'course_run',
            'unit_node_slug',
            'course_unit_id',
            'course_unit_slug',
            'block_uuid',
            'event_data'
        )

    def validate_event_type(self, value):
        if value not in VALID_API_TRACKING_EVENT_TYPES:
            err_msg = f"Invalid tracking_event_type : {value}"
            logger.exception(f"#APITrackingEventSerializer validate(): {err_msg}")
            raise serializers.ValidationError(err_msg)
        return value

    def validate(self, data):
        # Force user to be current user b/c this is an API request
        try:
            request = self.context.get('request')
            data['user'] = self.context['request'].user
        except Exception:
            err_msg = "Cannot get current user from request."
            logger.exception(f"#APITrackingEventSerializer validate(): {err_msg}")
            raise serializers.ValidationError(err_msg)

        if data['user'] == AnonymousUser:
            err_msg = "A TrackingEvent user must be logged in user"
            logger.exception(f"#APITrackingEventSerializer validate(): {err_msg}")
            raise serializers.ValidationError()

        # Make sure course exists...
        course_slug = data.get('course_slug', None)
        course_run = data.get('course_run', None)
        if course_slug and course_run:
            try:
                course = Course.objects.get(slug=course_slug, run=course_run)
            except Course.DoesNotExist:
                err_msg = f"Could not find course for {course_slug}_{course_run}"
                logger.exception(f"#APITrackingEventSerializer validate(): {err_msg}")
                raise serializers.ValidationError(err_msg)

        else:
            logger.error(f"#APITrackingEventSerializer validate(): course_slug and course_run are required.")
            raise serializers.ValidationError("Course run and course slug are required.")

        # Make sure student enrolled...
        try:
            Enrollment.objects.get(course=course, student=request.user, active=True)
        except Enrollment.DoesNotExist:
            if request.user.is_staff or request.user.is_superuser:
                logger.info(f"Could not find enrollment for {request.user} but that's ok "
                            f"because the user is staff or superuser and could just be viewing a course unit directly.")
            else:
                err_msg = f"User {request.user} is not actively enrolled in this course."
                logger.exception(f"#APITrackingEventSerializer validate(): {err_msg}")
                raise serializers.ValidationError(err_msg)

        event_type = data.get('event_type', None)
        event_data = data.get('event_data', None)

        # VIDEO-SPECIFIC EVENTS
        # Right now we only expect video activity tracking events via the API, but later
        # we might have others so be explicit here...
        # Check for video-specific data we expect
        if event_type == TrackingEventType.COURSE_VIDEO_ACTIVITY.value:
            if not event_data:
                err_msg = f"Invalid {event_type} event. Missing 'event_data'"
                logger.error(f"#APITrackingEventSerializer validate(): {err_msg}")
                raise serializers.ValidationError(err_msg)

            serializer = VideoEventDataSerializer(data=event_data)
            if not serializer.is_valid():
                err_msg = f"Invalid event_data {event_type} errors: {serializer}"
                logger.error(f"#APITrackingEventSerializer validate(): {err_msg}")
                raise serializers.ValidationError(err_msg)
        else:
            # Not implemented
            logger.warning(f"#APITrackingEventSerializer validate(): unhandled event_type. data: {data}")

        return data


class TrackingEventSerializer(serializers.ModelSerializer):
    """
    Serializes a 'tracking' event generated by internal
    methods. Fields like 'course_slug' and 'course_run'
    may sometimes be null.
    """

    event_type = serializers.CharField(allow_null=False,
                                       required=True)

    event_data = serializers.JSONField(allow_null=True,
                                       required=False)

    user = serializers.PrimaryKeyRelatedField(allow_null=True,
                                              required=False,
                                              queryset=User.objects.all())
    
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = TrackingEvent
        fields = (
            'uuid',
            'event_type',
            'time',
            'user',
            'anon_username',
            'course_slug',
            'course_run',
            'unit_node_slug',
            'course_unit_id',
            'course_unit_slug',
            'block_uuid',
            'event_data'
        )

    def validate_event_type(self, value):
        if value not in ALL_VALID_EVENTS:
            raise serializers.ValidationError("Invalid tracking_event_type : {}".format(value))
        return value

    def validate(self, data):
        course_run = data.get('course_run', None)
        course_slug = data.get('course_slug', None)
        if course_slug and course_run:
            event_type = data.get('event_type')
            try:
                course = Course.objects.get(slug=course_slug, run=course_run)
                if course.has_finished and event_type not in POST_COURSE_TRACKED_EVENTS:
                    raise CourseFinishedException(f"Invalid tracking event_type : {event_type} "
                                                  f"for course slug {course_slug} course run {course_run} as course has "
                                                  f"already finished")
            except Course.DoesNotExist:
                raise ValidationError(f"Could not track event for course slug {course_slug} "
                                      f"run {course_run} as course does not exist")

        return data
