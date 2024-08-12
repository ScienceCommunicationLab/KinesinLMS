from enum import Enum
from django.db import models
from django.utils.translation import gettext_lazy as _
from kinesinlms.core.models import Trackable
from kinesinlms.course.models import Course

# "Are you planning on evaluating?"
EVALUATING_CHOICES = [
    ("YES", "Yes"),
    ("NO", "No"),
    ("NOT_SURE", "Not sure"),
]


# Create your models here.
class EducatorSurvey(models.Model):
    plan_to_use = models.TextField(null=True, blank=True)
    evaluating = models.CharField(
        max_length=40, choices=EVALUATING_CHOICES, blank=True, null=True
    )
    institution = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)


class EducatorResourceType(Enum):
    """
    Enum for types of educator resources.
    """

    GUIDE = "guide"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


class EducatorResource(Trackable):
    """
    Model for educator resources associated with a course.
    This is a many-to-one relationship, so there can be different
    types of resources associated with a course.

    An "educator resources" is any document, guide or other file
    that is specifically designed for the educator and not for the student.

    Creating an instance of this class and associating with a course
    essentially enables educator resources for that course.
    """

    enabled = models.BooleanField(default=True, blank=False, null=False)

    type = models.CharField(
        max_length=20,
        choices=[(tag.name, tag.value) for tag in EducatorResourceType],
        default=EducatorResourceType.GUIDE.name,
    )

    course = models.ForeignKey(
        Course,
        null=True,
        related_name="educator_resources",
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=100, null=True, blank=True)

    overview = models.TextField(
        null=True,
        blank=True,
        help_text=_("A short description of the educator resource."),
    )

    content = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "The complete content of the resource (if it's just text and you want to store it here.)"
        ),
    )

    file = models.FileField(
        null=True, blank=True, upload_to="educator_resources/files/"
    )

    url = models.URLField(
        null=True,
        blank=True,
        help_text=_("URL to resource, if the resource is hosted externally."),
    )

    @property
    def get_type_display(self):
        if self.type:
            return EducatorResourceType[self.type].value
        return "( none )"
