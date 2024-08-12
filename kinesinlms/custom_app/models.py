
from enum import Enum

from django.db import models
from django.conf import settings
from django.db.models import JSONField

# Create your models here.
from kinesinlms.assessments.models import Assessment
from kinesinlms.core.models import Trackable
from kinesinlms.course.models import Course

import logging
logger = logging.getLogger(__name__)


class CustomAppTypes(Enum):
    PEER_REVIEW_JOURNAL = "Peer review journal"
    COURSE_SPEAKERS = "Course Speakers"
    SIMPLE_HTML_CONTENT = "Html Content"


class CustomApp(Trackable):
    display_name = models.CharField(max_length=400, null=True, blank=True)
    type = models.CharField(null=False,
                            blank=True,
                            max_length=100,
                            choices=[(tag.name, tag.value) for tag in CustomAppTypes],
                            )
    slug = models.SlugField(max_length=200, null=True, blank=True, allow_unicode=True)
    course = models.ForeignKey(Course,
                               null=False,
                               blank=True,
                               on_delete=models.CASCADE,
                               related_name="custom_apps")
    short_description = models.CharField(max_length=200, null=True, blank=True)

    # This field is used for HTML content for types like SIMPLE_HTML_CONTENT
    description = models.TextField(null=True, blank=True)
    tab_label = models.CharField(max_length=50, null=False, default="Custom")


class CustomAppStudentSettings(models.Model):
    custom_app = models.ForeignKey(CustomApp,
                                   null=False,
                                   blank=True,
                                   on_delete=models.CASCADE,
                                   related_name="student_settings")
    student = models.ForeignKey(settings.AUTH_USER_MODEL,
                                null=False,
                                blank=True,
                                on_delete=models.CASCADE,
                                )
    allow_public_view = models.BooleanField(null=False, default=False)
    allow_user_view = models.BooleanField(null=False, default=False)
    allow_user_comments = models.BooleanField(null=False, default=False)
    allow_classmate_view = models.BooleanField(null=False, default=False)
    allow_classmate_comments = models.BooleanField(null=False, default=False)


class PeerComment(models.Model):
    custom_app = models.ForeignKey(CustomApp,
                                   null=False,
                                   blank=True,
                                   on_delete=models.CASCADE,
                                   related_name="comments")
    student_owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                                      null=False,
                                      blank=True,
                                      on_delete=models.CASCADE,
                                      related_name="custom_app_student_settings"
                                      )
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               null=False,
                               blank=True,
                               on_delete=models.CASCADE,
                               )
    html_content = models.TextField(null=True, blank=True)
    json_content = JSONField(null=True, blank=True)


class AppItemTypes(Enum):
    LONG_FORM_ENTRY_REVIEW = "long_form_entry_review"

    def __str__(self):
        return self.name


class AppItem(Trackable):
    type = models.CharField(null=False,
                            blank=True,
                            max_length=100,
                            choices=[(tag.name, tag.value) for tag in AppItemTypes],
                            )
    custom_app = models.ForeignKey(CustomApp,
                                   null=False,
                                   blank=True,
                                   on_delete=models.CASCADE,
                                   related_name="items")
    assessment = models.ForeignKey(Assessment,
                                   null=True,
                                   blank=True,
                                   on_delete=models.SET_NULL)
    order = models.IntegerField(default=0, null=False)
    html_content = models.TextField(null=True,  blank=True)
    json_content = JSONField(null=True, blank=True)




