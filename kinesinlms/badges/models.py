import logging
from enum import Enum

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.http import urlencode
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class BadgeProviderType(Enum):
    BADGR = "Badgr"


class BadgeProvider(models.Model):
    """
    A BadgeProvider defines access to an external badge service.
    This class is used to store the credentials for accessing
    the external service to geneate badges.

    As of now, it's highly targeted towards the BADGR service,
    but could be extended to support other services.

    """
    site = models.OneToOneField(Site,
                                related_name='badge_provider',
                                on_delete=models.CASCADE)

    active = models.BooleanField(default=True,
                                 blank=False,
                                 null=False,
                                 help_text=_("Enable badge provider."))

    name = models.CharField(max_length=200,
                            blank=True,
                            null=True,
                            help_text=_('External badge provider name'))

    type = models.CharField(max_length=50,
                            choices=[(tag.name, tag.value) for tag in BadgeProviderType],
                            default=BadgeProviderType.BADGR.name,
                            null=True,
                            blank=True,
                            help_text=_("The type of badge provider"))

    slug = models.SlugField(max_length=40,
                            blank=True,
                            null=True,
                            help_text=_('Slug for external badge provider'))

    api_url = models.URLField(null=True,
                              blank=True,
                              help_text=_('External badge provider API url'))

    salt = models.CharField(max_length=200,
                            blank=True,
                            null=True,
                            help_text=_('"salt" key for hashing external badge provider badge'))

    issuer_entity_id = models.CharField(max_length=50,
                                        blank=True,
                                        null=True,
                                        help_text=_("Our KinesinLMS entity ID on this service"))

    access_token = models.CharField(max_length=200,
                                    blank=True,
                                    null=True,
                                    help_text=_('Badge provider API access token.'))

    refresh_token = models.CharField(max_length=200,
                                     blank=True,
                                     null=True,
                                     help_text=_('Badge provider API refresh token.'))

    def __str__(self):
        return f"Badge Provider ({self.slug})"

    @property
    def username(self) -> str:
        if self.type == BadgeProviderType.BADGR.name:
            if settings.BADGE_PROVIDER_USERNAME:
                return settings.BADGE_PROVIDER_USERNAME
            else:
                raise Exception("BadgeProvider is set to type BADGR, but "
                                "BADGE_PROVIDER_USERNAME not set in settings.py")
        else:
            raise Exception("BadgeProvider is not configured. "
                            "No badge provider username available.")

    @property
    def password(self) -> str:
        if self.type == BadgeProviderType.BADGR.name:
            if settings.BADGE_PROVIDER_PASSWORD:
                return settings.BADGE_PROVIDER_PASSWORD
            else:
                raise Exception("BadgeProvider is set to type BADGR, but "
                                "BADGE_PROVIDER_PASSWORD not set in settings.py")
        else:
            raise Exception("BadgeProvider is not configured. "
                            "No badge provider password available.")


class BadgeClassType(Enum):
    COURSE_PASSED = "Passed Course"
    MILESTONE = "Course Milestone"


class BadgeClass(models.Model):
    class Meta:
        verbose_name_plural = "badge classes"
        unique_together = ('course', 'slug')

    # The course this BadgeClass applies to, if any
    # (There may be badges unrelated to course-specific activity.)
    # TODO: not relationally sound as milestone also has a reference
    # TODO: course, and therefore potential for error if this
    # TODO: course is not the same.
    course = models.ForeignKey('course.Course',
                               null=True,
                               blank=True,
                               on_delete=models.CASCADE,
                               related_name="badge_classes")

    # a slug for this badge class. Mainly for use in events
    # but may be other uses later.
    slug = models.SlugField(max_length=100,
                            null=True,
                            blank=False)

    type = models.CharField(max_length=30,
                            blank=False,
                            default=BadgeClassType.COURSE_PASSED.name,
                            choices=[(item.name, item.value) for item in BadgeClassType],
                            help_text=_("Type of badge class using the BadgeClassType enum. "
                                        "There can only be one COURSE_PASSED type per course."))

    name = models.CharField(max_length=400,
                            blank=True,
                            null=True,
                            help_text=_('Badge display name'))

    provider = models.ForeignKey(BadgeProvider,
                                 null=True,
                                 blank=False,
                                 on_delete=models.CASCADE,
                                 related_name="providers")

    external_entity_id = models.CharField(max_length=200,
                                          null=True,
                                          blank=False,
                                          help_text=_("The ID of this badge class in the external service (used for "
                                                      "API calls)."))

    # The official ID of the BadgeClass in external badge service.
    # We assume this is a URL.
    open_badge_id = models.URLField(blank=True,
                                    null=True,
                                    help_text=_('URL of badge class definition in external badge service'))

    # The URL to the "badge" template image. Note this image is not an actual badge.
    # (Actual badges are only created in a BadgeAssertion for a particular user upon achievement.)
    image_url = models.URLField(blank=True,
                                null=True,
                                help_text=_('URL of image graphic for badge in external badge service'))

    # This description should be relatively short. Details of badge should be stored in remote service.
    # This is only for the admin to remember what the badge is about.
    description = models.CharField(max_length=500,
                                   blank=True,
                                   null=True,
                                   help_text=_('Short description of badge'))

    # If used, criteria text should match what's been entered in remote service (e.g. Badgr)
    criteria = models.TextField(blank=True,
                                null=True,
                                help_text=_('Criteria for earning badge'))

    @property
    def type_name(self) -> str:
        if self.type:
            try:
                return BadgeClassType[self.type].value
            except Exception:
                logger.error(f"Invalid BadgeClassType : {self.type}")
        return "?"

    def __str__(self):
        return f"BadgeClass ({self.id}) {self.name}"


class BadgeAssertionCreationStatus(Enum):
    STAGED = "staged"  # ready for async task
    IN_PROGRESS = "in progress"
    COMPLETE = "complete"
    FAILED = "failed"


class BadgeAssertion(models.Model):
    """
    Awards a particular BadgeClass to a particular student.

    This class is a foreign key on other models where the badge
    was awarded to a particular student.

    For example:
    - CoursePassed: if a student passes a course and
      a CoursePassed instance is created.
    - Milestone Achievement: if a student achieves a Milestone
      and that creates a MilestoneAchievement instance.

    """
    badge_class = models.ForeignKey(BadgeClass,
                                    null=False,
                                    blank=False,
                                    related_name="badge_assertions",
                                    on_delete=models.CASCADE)

    creation_status = models.CharField(max_length=20,
                                       null=False,
                                       blank=False,
                                       default=BadgeAssertionCreationStatus.STAGED.name,
                                       choices=[(item.name, item.value) for item in BadgeAssertionCreationStatus],
                                       help_text=_("Status of badge assertion creation. "
                                                   "See BadgeAssertionCreationStatus for possible states."))

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL,
                                  null=False,
                                  blank=True,
                                  related_name="badge_assertions",
                                  on_delete=models.CASCADE)

    issued_on = models.DateTimeField(null=True, blank=False)

    # This is populated with the URL to the badge assertion viewing page
    # for a particular student after the badge is registered with the badge service API
    open_badge_id = models.URLField(null=True,
                                    blank=True,
                                    help_text=_("URL to the badge assertion viewing page"))

    badge_image_url = models.URLField(null=True,
                                      blank=True,
                                      help_text=_("URL to the badge assertion image"))

    external_entity_id = models.CharField(max_length=50,
                                          null=True,
                                          blank=True,
                                          help_text=_("The ID of this assertion in the external service"))

    # Store any error messages from the remote service here. We can use this
    # for triage if any issues arise.
    error_message = models.CharField(max_length=300,
                                     null=True,
                                     blank=True,
                                     help_text=_("Error message from external badge service"))

    @property
    def badge_title(self) -> str:
        if hasattr(self, "badge_class"):
            return self.badge_class.name
        return ""

    @property
    def course_title(self) -> str:
        if hasattr(self, "badge_class"):
            if hasattr(self.badge_class, "course"):
                return self.badge_class.course.display_name
        return ""

    @property
    def twitter_share_url(self) -> str:
        """
        Construct a 'share' url for twitter.
        """
        if not self.open_badge_id:
            return '#'

        courses_url = "https://kinesinlms.org"
        url_args = urlencode({
            "original_referer": courses_url,
            "text": "I earned a badge on KinesinLMS",
            "url": self.open_badge_id,
            "via": "kinesinlms"
        })

        twitter_share_url = f"https://twitter.com/intent/tweet?{url_args}"

        return twitter_share_url

    def clear(self):
        self.open_badge_id = None
        self.badge_image_url = None
        self.issued_on = None
        self.external_entity_id = None
        self.error_message = None
        self.save()
