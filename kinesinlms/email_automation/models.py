from typing import Optional

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import gettext_lazy as _

from kinesinlms.email_automation.constants import EmailAutomationProviderType
from kinesinlms.tracking.event_types import TrackingEventType


class EmailAutomationProvider(models.Model):
    """
    Defines the properties of the third-party email automation service
    to use for email automation tasks.

    IMPORTANT: In order for this class to be used, the settings.EMAIL_AUTOMATION_PROVIDER_API_KEY
    must be defined.
    """

    site = models.OneToOneField(Site,
                                null=False,
                                blank=False,
                                on_delete=models.CASCADE,
                                related_name="email_automation_provider")

    type = models.CharField(max_length=30,
                            blank=False,
                            null=False,
                            choices=[(item.name, item.value) for item in EmailAutomationProviderType],
                            help_text=_("Provider of email automation provider."))

    active = models.BooleanField(default=True,
                                 blank=False,
                                 null=False,
                                 help_text=_("Enable email automation provider."))

    api_url = models.URLField(null=False,
                              blank=False,
                              help_text=_("Email automation provider API endpoint"))

    tag_ids = models.JSONField(null=True,
                               blank=True,
                               help_text=_("If a provider supports tags, but uses IDs rather "
                                           "than the the tag itself during API calls, "
                                           "this field maps tag names to the tag IDs."))

    @property
    def api_key(self) -> Optional[str]:
        key = settings.EMAIL_AUTOMATION_PROVIDER_API_KEY
        return key

    @property
    def enabled(self) -> bool:
        return self.api_key is not None and self.active


# This is the subset of tracking events that we want to allow to be sent to the
# email automation service for a particular course. Since we're just sending string 'tags' to the
# service, the events should be very coarse events that don't need extra data to be sent with them.
# Later we might consider  sending any tag, and just appending metadata to the tag, e.g. kinesinlms.course.video.play.(video ID).
TRACKING_EVENTS_FOR_EMAIL_AUTOMATION = [
    TrackingEventType.USER_REGISTRATION,
    TrackingEventType.ENROLLMENT_ACTIVATED,
    TrackingEventType.ENROLLMENT_DEACTIVATED,
    TrackingEventType.COURSE_CERTIFICATE_EARNED,
]


class CourseEmailAutomationSettings(models.Model):
    """
    Defines the properties of the email automation service
    for a particular course.
    """

    course = models.OneToOneField("course.Course",
                                  null=False,
                                  blank=False,
                                  on_delete=models.CASCADE,
                                  related_name="email_automation_settings")

    active = models.BooleanField(default=True,
                                 blank=False,
                                 null=False,
                                 help_text=_("Enable email automation service for this course."))

    send_event_as_tag = ArrayField(models.CharField(max_length=50,
                                                    blank=False,
                                                    null=False,
                                                    choices=[
                                                        (item.name, item.value)
                                                        for item
                                                        in TRACKING_EVENTS_FOR_EMAIL_AUTOMATION
                                                    ],
                                                    help_text=_("Tracking events that will be sent "
                                                                "as a tag to email automation.")),
                                   blank=True,
                                   null=True)

    def is_event_enabled(self, tracking_event_name) -> bool:
        """
        Convenience method to check if a tag is enabled for an event type
        in this course.
        """

        if not self.active:
            return False
        if not hasattr(self, 'send_event_as_tag'):
            return False
        if not self.send_event_as_tag:
            return False
        tracking_event_name = TrackingEventType(tracking_event_name).name
        return tracking_event_name in self.send_event_as_tag
