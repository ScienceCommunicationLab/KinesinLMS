from typing import List, Optional

from django.conf import settings
from django.db import models
from django.db.models import JSONField
from django.shortcuts import resolve_url
from django.utils.translation import gettext as _

DEFAULT_COURSE_HEADER_BACKGROUND_COLOR = "F1F1F1"
DEFAULT_THUMBNAIL = "default_course_thumbnail.jpg"


class CourseCatalogDescription(models.Model):
    """
    Holds meta information about a course, mostly for display to the public
    in things like the course catalog or on a course about page.
    """

    class Meta:
        ordering = ("order",)

    title = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text=_("The title of the course to be shown in the catalog."),
    )

    # Blurb is the one or two sentences of text that shows up in a card.
    blurb = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text=_("A short, marketing-oriented description of the course. Only one or two sentences long."),
    )

    overview = models.TextField(
        null=True,
        blank=True,
        help_text=_("A short description of the course, usually just a paragraph long."),
    )

    about_content = models.TextField(
        null=True,
        blank=True,
        help_text=_("The long, detailed content shown on the " "course about page. HTML is okay."),
    )

    sidebar_content = models.TextField(
        null=True,
        blank=True,
        help_text=_("Other information to show in the sidebar, if present. HTML is okay."),
    )

    thumbnail = models.FileField(
        null=True,
        blank=True,
        upload_to="catalog/images/",
        help_text=_(
            "The image to be used in the catalog card. If empty, KinesinLMS will show "
            "the 'catalog/static/catalog/default_course_thumbnail.jpg' image."
        ),
    )

    visible = models.BooleanField(default=True, help_text=_("Show this course in the course catalog"))

    hex_theme_color = models.CharField(
        max_length=6,
        default="e1e1e1",
        null=False,
        blank=False,
        help_text=_(
            "The hex value for the 'theme' color. This color "
            "is used, e.g. as the background of the hero bar "
            "on the course about page."
        ),
    )

    hex_title_color = models.CharField(
        max_length=6,
        default="ffffff",
        null=False,
        blank=False,
        help_text=_("The hex value for the color of the title text on the about page"),
    )

    custom_stylesheet = models.CharField(
        max_length=250,
        default=None,
        null=True,
        blank=True,
        help_text=_("The filename of the custom css stylesheet to " "use when showing course content."),
    )  # type: str

    # If there's a trailer...
    trailer_video_url = models.URLField(max_length=250, null=True, blank=True, help_text=_("URL for the trailer video"))

    syllabus = models.FileField(
        null=True,
        blank=True,
        upload_to="catalog/syllabi/",
        help_text=_("The public syllabus for the course, shown to users who are considering enrolling."),
    )

    effort = models.CharField(
        null=True,
        blank=True,
        max_length=100,
        help_text=_("Generic text description of effort, e.g. '3 hours / week'"),
    )

    # I defined this in the catalog, but really we should only
    # ask the Course itself how many modules there are, to keep things DRY.
    # TODO: Remove this property
    num_modules = models.IntegerField(null=True, blank=True)

    duration = models.CharField(null=True, blank=True, max_length=100)

    audience = models.CharField(null=True, blank=True, max_length=100)

    features = JSONField(
        null=True,
        blank=True,
        help_text=_("An array of strings describing each feature of the course."),
    )

    order = models.IntegerField(default=0, help_text=_("Used for ordering cards in the course catalog"))

    @property
    def testimonials(self) -> List["marketing.Testimonial"]:  # noqa: F821
        """
        Returns a list of testimonials (as dictionaries) for this course.
        """
        if hasattr(self.course, "testimonials"):
            return self.course.testimonials.all()
        return []

    @property
    def thumbnail_url(self) -> Optional[str]:
        if bool(self.thumbnail):
            return self.thumbnail.url
        # Use 'default' thumbnail
        if DEFAULT_THUMBNAIL:
            return f"{settings.STATIC_URL}catalog/images/{DEFAULT_THUMBNAIL}"

        return None

    @property
    def syllabus_url(self) -> Optional[str]:
        if bool(self.syllabus):
            return self.syllabus.url
        return None

    @property
    def custom_stylesheet_url(self):
        return "catalog/css/about/{}".format(self.custom_stylesheet)

    @property
    def about_page_url(self):
        about_page_url = resolve_url(
            "catalog:about_page",
            course_slug=self.course.slug,
            course_run=self.course.run,
        )
        return about_page_url

    def __str__(self):
        return f"Catalog Description {self.id} : {self.title}"

    @property
    def enrollment_has_started(self) -> bool:
        return self.course.enrollment_has_started

    @property
    def course_has_started(self) -> bool:
        return self.course.course_has_started

    @property
    def token(self) -> str:
        return self.course.token
