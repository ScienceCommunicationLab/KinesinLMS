import logging
from enum import Enum
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from kinesinlms.core.models import Trackable
from kinesinlms.course.models import Course
from kinesinlms.learning_library.models import Block
from kinesinlms.survey.constants import SurveyEmailStatus, SurveyType

logger = logging.getLogger(__name__)


class SurveyProviderType(Enum):
    # Only one kind of survey provider at the moment...
    QUALTRICS = "Qualtrics"


class SurveyProvider(Trackable):
    """
    External survey provider. At the moment the only provider implemented is
    Qualtrics, but this model could be used by and extended for other providers.
    """

    name = models.CharField(
        max_length=50,
        null=False,
        blank=False,
        help_text=_("Name of the survey provider. (This is for your use and can be anything you want.)"),
    )

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in SurveyProviderType],
        default=SurveyProviderType.QUALTRICS.name,
        null=False,
        blank=False,
    )

    active = models.BooleanField(
        default=True,
        blank=False,
        null=False,
        help_text=_(
            "Enable survey provider. If disabled, surveys associated with this provider will not be available."
        ),
    )

    slug = models.SlugField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Slug identifier for provider (used in e.g. course json imports).",
    )

    datacenter_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Data center ID, if survey provider defines one (e.g. Qualtrics.)",
    )

    callback_secret = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Secret used by remote survey provider to call webhooks on KinesinLMS.",
    )

    @property
    def api_key(self) -> Optional[str]:
        """
        API key used to access remote survey provider.
        """
        key = getattr(settings, "SURVEY_PROVIDER_API_KEY", None)
        return key

    @property
    def enabled(self) -> bool:
        return self.active

    @property
    def requires_api_key(self) -> bool:
        """
        Does this survey provider require an API key to access its services?
        Returns:
            bool: _description_
        """
        if self.type == SurveyProviderType.QUALTRICS.name:
            return False
        return True

    @property
    def can_delete(self) -> bool:
        """
        Can this survey provider be deleted?
        Returns:
            bool: _description_
        """
        if hasattr(self, "surveys") and self.surveys.count() > 0:
            return False
        return True

    def __str__(self):
        return f"Survey provider [type: {self.type} name: {self.name}]"

    def clean(self):
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)
            self.save()


class Survey(Trackable):
    """
    Describes surveys associated with Course.

    If send_reminder_email is checked, the event that causes a survey reminder
    (SurveyEmail instance) to be scheduled can vary depending on type of survey.

    PRE_COURSE:     Reminder email scheduled when a student enrolls in a course.
    BASIC:          Reminder email scheduled when student first views a unit with the survey.
    POST_COURSE:    Reminder email scheduled when a student completes a course.
    FOLLOW_UP:      Reminder email scheduled when a student completes a course.

    """

    class Meta:
        ordering = ["index"]

    slug = models.SlugField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Slug identifier for survey (used in e.g. course json imports).",
    )

    # Survey's don't have to be associated with a course.
    course = models.ForeignKey(
        Course,
        blank=True,
        null=True,
        related_name="surveys",
        on_delete=models.CASCADE,
    )

    type = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in SurveyType],
        default=SurveyType.PRE_COURSE.name,
        null=False,
        blank=False,
        help_text=_(
            "The survey type helps indicate the purpose of the "
            "survey and roughly where it appears in the course (but actual position "
            "is determined by you in the course structure and not by this setting). The type "
            "also determines when a reminder email is sent if 'Send reminder email' is checked."
        ),
    )

    provider = models.ForeignKey(
        SurveyProvider,
        blank=True,
        null=True,
        related_name="surveys",
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="The name to display above the survey when shown to a student in the "
        "course or in a reminder email.",
    )

    send_reminder_email = models.BooleanField(
        null=False,
        default=True,
        help_text="Send a reminder email. (Email will be sent after a "
        "certain time if days_delay is set to something other than 0.)",
    )

    days_delay = models.IntegerField(
        null=False,
        default=0,
        blank=False,
        help_text="How many days to wait before sending the reminder email. Otherwise, "
        "the email will be sent on the day the SurveyEmail is created.",
    )

    survey_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Survey ID",
        help_text="The ID for the survey in the third-party service that " "provides it.",
    )

    # TODO: What was I thinking with this field?
    index = models.IntegerField(null=True, blank=True)

    url = models.URLField(help_text="Public URL for the survey. This is used to render the " "survey in a course unit.")

    include_uid = models.BooleanField(
        default=False,
        help_text="Include the student's anonymous ID in the survey URL.",
    )

    # METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def url_for_user(self, user) -> str:
        """
        Returns the full URL for the survey, including student information if
        required (e.g. the student's anonymous ID).

        Returns:
            str:    Full URL to survey.
        """
        if not user:
            raise ValueError("User must be provided to generate survey URL via the url_for_user method.")
        url = self.url
        if self.include_uid:
            url += f"?uid={user.anon_username}"
        return url

    def clean(self):
        super().clean()
        if not self.slug:
            self.slug = slugify(self.survey_id)
            self.save()

    def __str__(self):
        s = "Survey "
        if hasattr(self, "course") and self.course and self.course.token:
            s += f"{self.course.token} : "
        s += self.type
        if self.name:
            s += f" : {self.name}"
        return s


class SurveyBlock(Trackable):
    """
    Adds survey information to a block (and therefore is a one-to-one relationship).
    However, an author might want to include the same survey at multiple points in
    a course, which this model affords via its foreign key to Survey.
    """

    block = models.OneToOneField(
        Block,
        on_delete=models.CASCADE,
        related_name="survey_block",
    )

    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="survey_blocks",
    )


class SurveyCompletion(Trackable):
    survey = models.ForeignKey(
        Survey,
        blank=False,
        null=False,
        related_name="completions",
        on_delete=models.CASCADE,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=False,
        blank=True,
        related_name="survey_completions",
        on_delete=models.CASCADE,
    )

    times_completed = models.IntegerField(default=0, null=False, blank=False)


class SurveyEmail(Trackable):
    """
    Stores a task to send an email with a survey link

    TODO: Add token and use that token in email URLs
    TODO: to track interaction.
    One way to do tokens is add a unique field
    and generate on save:
    import uuid
    uuid.uuid4().hex[:6].upper()

    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="survey_emails",
    )
    survey = models.ForeignKey(
        Survey,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="survey_emails",
    )
    scheduled_date = models.DateField(blank=True, null=True)

    status = models.CharField(
        max_length=250,
        choices=[(tag.name, tag.value) for tag in SurveyEmailStatus],
        default=SurveyEmailStatus.UNPROCESSED.name,
        null=False,
        blank=False,
    )
