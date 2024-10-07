import logging
import uuid
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import resolve_url
from django.utils.translation import gettext as _
from slugify import slugify

from kinesinlms.core.models import Trackable

logger = logging.getLogger(__name__)

User = get_user_model()


class Signatory(models.Model):
    """
    Defines a signatory for a certificate.
    """

    slug = models.SlugField(null=False, blank=True, unique=True)

    name = models.CharField(max_length=200, null=False, blank=False)

    title = models.CharField(max_length=200, null=False, blank=False)

    organization = models.CharField(max_length=200, null=False, blank=False)

    signature_image = models.FileField(upload_to="signatures/", null=False, blank=False)

    def clean(self):
        if self.slug is None:
            self.slug = slugify(self.name)
            self.save()


class CertificateTemplate(models.Model):
    """
    Defines a template for a certificate for a course.
    """

    # We may later want multiple certs per course, but for now, one-to-one...
    course = models.OneToOneField(
        "course.Course", on_delete=models.CASCADE, related_name="certificate_template"
    )

    signatories = models.ManyToManyField(
        Signatory, related_name="certificate_templates", blank=True
    )

    # If custom_template_name is not defined
    # we'll use the default HTML template for the site.
    # If name is defined, we look for it in
    # templates/course/certificate/custom_templates/
    custom_template_name = models.CharField(
        null=True,
        blank=True,
        max_length=200,
        help_text=_(
            "Custom template name to use for certificate (if any). "
            "This template should exist in "
            "templates/course/certificate/custom"
        ),
    )

    description = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text=_("An admin description of this certificate template."),
    )

    def __str__(self):
        return f"CertificateTemplate for {self.course}"


# This class describes a completion certificate for a course, if one is available.
class Certificate(Trackable):
    """
    Defines a student's certificate for completion of a course.
    This class is a little slim at the moment.
    We assume there's only one cert per course.
    In the future, information about the context around the certificate should be
    captured here with more fields (e.g. Honors, etc.)
    """

    class Meta:
        unique_together = (("student", "certificate_template"),)

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="certificates",
    )

    certificate_template = models.ForeignKey(
        CertificateTemplate, null=False, blank=False, on_delete=models.CASCADE
    )

    uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, null=True, blank=False, editable=True
    )

    @property
    def certificate_url(self):
        if self.certificate_template and self.certificate_template.course:
            course = self.certificate_template.course
            return resolve_url(
                "course:certificate_page",
                course_slug=course.slug,
                course_run=course.run,
            )
        logger.warning(
            "Cannot determine certificate URL because course or course certificate template is missing."
        )
        return ""

    # noinspection PyUnresolvedReferences
    @property
    def student_name(self) -> Optional[str]:
        if self.student:
            if self.student.name:
                return self.student.name
            else:
                return self.student.username
        return None

    @property
    def course_name(self) -> Optional[str]:
        if self.certificate_template and self.certificate_template.course:
            return self.certificate_template.course.display_name
        return None

    @property
    def course(self) -> Optional["kinesinlms.course.models.Course"]:
        if self.certificate_template and self.certificate_template.course:
            return self.certificate_template.course
        return None


# Not sure how to track "passing" so for now creating this class,
# which can be many to one but for now will just be practically one-to-one,
# with only one possible milestone that we'll be using: number of assessments to pass.
