import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import JSONField

from kinesinlms.tracking.event_types import TrackingEventType

logger = logging.getLogger(__name__)

User = get_user_model()


class TrackingEvent(models.Model):
    """
    Stores user and system events, optimized for storage
    by event time 'event_type'.
    """

    class Meta:
        indexes = [models.Index(fields=['time', ]),
                   models.Index(fields=['event_type', ])]
        ordering = ('-time',)

    event_type = models.CharField(max_length=200, null=True, blank=True, default="1")

    time = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             blank=True,
                             null=True,
                             related_name='tracking_events',
                             on_delete=models.SET_NULL)

    # We also store anon_username directly, as we want
    # to preserve uniqueness of student's events even
    # if user is somehow deleted.
    anon_username = models.UUIDField(null=True,
                                     blank=True)

    course_slug = models.SlugField(max_length=200,
                                   null=True,
                                   blank=True,
                                   allow_unicode=True)

    course_run = models.CharField(max_length=200,
                                  null=True,
                                  blank=True)

    unit_node_slug = models.SlugField(max_length=200,
                                      null=True,
                                      blank=True,
                                      allow_unicode=True)

    course_unit_id = models.IntegerField(null=True,
                                         blank=True)

    course_unit_slug = models.SlugField(max_length=200,
                                        null=True,
                                        blank=True,
                                        allow_unicode=True)

    block_uuid = models.UUIDField(null=True,
                                  blank=True)

    event_data = JSONField(null=True, blank=True)

    def get_nice_message(self) -> str:
        """
        Returns a nice, descriptive message for an event that just occurred.
        This is helpful when, for example, sending a message to Slack.
        Pass in the username if you need something other than anon_username.
        """

        message = ""
        try:
            if self.user and self.user.is_staff:                    # noqa
                message = f"[staff: `{self.user.username}`] "       # noqa
            else:
                message = f"[student: `{str(self.anon_username)[:6]}...`] "
        except Exception:
            logger.error(f"Could not set prefix in get_nice_message")

        try:
            if self.event_type == TrackingEventType.MILESTONE_COMPLETED.value:
                message += " just completed a milestone in "
            elif self.event_type == TrackingEventType.COURSE_PAGE_VIEW.value:
                message += f"just viewed unit *{self.unit_node_slug}* in "
            elif self.event_type == TrackingEventType.USER_LOGIN.name:
                message += "just logged in "
            elif self.event_type == TrackingEventType.ENROLLMENT_ACTIVATED.value:
                message += "just enrolled in "
            elif self.event_type == TrackingEventType.ENROLLMENT_DEACTIVATED.value:
                message += "just unenrolled from "
            elif self.event_type == TrackingEventType.COURSE_EXTRA_PAGE_VIEW.value:
                page_name = self.event_data.get('page_name', "")
                message += f" just viewed the {page_name} tab in "
            elif self.event_type == TrackingEventType.COURSE_CUSTOM_APP_PAGE_VIEW.value:
                custom_app_name = self.event_data.get('custom_app', "?")
                message += f" just viewed the {custom_app_name} tab in "
            elif self.event_type == TrackingEventType.COURSE_PROGRESS_VIEW.value:
                message += " just viewed the progress tab in "
            elif self.event_type == TrackingEventType.COURSE_CERTIFICATE_VIEW.value:
                message += " just viewed the certificate tab in "
            elif self.event_type == TrackingEventType.COURSE_BOOKMARKS_VIEW.value:
                message += " just viewed the bookmarks tab in "
            elif self.event_type == TrackingEventType.COURSE_HOME_VIEW.value:
                message += " just viewed the home tab in "
            elif self.event_type == TrackingEventType.COURSE_RESOURCE_DOWNLOAD.value:
                message += f" just downloaded course resource {self.event_data} in "
            elif self.event_type == TrackingEventType.COURSE_BLOCK_RESOURCE_DOWNLOAD.value:
                message += f" just downloaded course block resource {self.event_data} in "
            elif self.event_type == TrackingEventType.SURVEY_COMPLETED.value:
                message += f" just completed the {self.event_data.get('survey_type', '?')} survey in "
            else:
                message += f" event type: {self.event_type} "

            course_slug = self.course_slug
            if course_slug:
                course_run = self.course_run
                message += f"course {course_slug}_{course_run}"

        except Exception:
            logger.exception("Could not build nice message for event")
            message += f" ( tracking event {self.id} )"

        return message
