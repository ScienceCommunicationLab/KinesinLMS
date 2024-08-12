import logging

from django.conf import settings
from django.utils.translation import gettext as _
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import JSONField

from kinesinlms.core.models import Trackable

logger = logging.getLogger(__name__)


class ManualUnenrollment(Trackable):
    course = models.ForeignKey('course.Course',
                               on_delete=models.CASCADE,
                               related_name="manual_unenrollments",
                               null=False,
                               blank=False)

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             blank=False,
                             null=False,
                             related_name='manual_unenrollments',
                             on_delete=models.CASCADE)

    unenrolled_student_ids = ArrayField(
        models.IntegerField()
    )

    skipped_student_ids = ArrayField(
        models.IntegerField()
    )

    errors = JSONField(null=True, blank=True)


class ManualEnrollment(Trackable):

    # TODO:
    #   Maybe remove this field as it's
    #   redundant now that we also link cohort below...
    course = models.ForeignKey('course.Course',
                               on_delete=models.CASCADE,
                               related_name="manual_enrollments",
                               null=False,
                               blank=False)

    cohort = models.ForeignKey('course.Cohort',
                               on_delete=models.CASCADE,
                               related_name="manual_enrollments",
                               null=True,
                               blank=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             blank=False,
                             null=False,
                             related_name='manual_enrollments',
                             on_delete=models.CASCADE)

    added_student_ids = ArrayField(
        models.IntegerField(),
        help_text=_("IDs of students who were enrolled and added to the indicated cohort."),
        default=list
    )

    skipped_student_ids = ArrayField(
        models.IntegerField(),
        help_text=_("IDs of students who were skipped because they were already enrolled in this course and cohort."),
        default=list
    )

    moved_from_cohort_ids = ArrayField(
        models.IntegerField(),
        help_text=_("IDs of students who were already enrolled but were in a different cohort"),
        default=list
    )

    errors = JSONField(null=True, blank=True)
