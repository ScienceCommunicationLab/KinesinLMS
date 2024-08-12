from typing import Tuple

from kinesinlms.certificates.models import CertificateTemplate


class CertificateTemplateFactory:
    """
    Factory for creating certificate templates.
    Making this a separate class rather than a method on the CertificateTemplate model manager
    as we need to use the course model to create the certificate template. Also, we may want to
    add more functionality to this factory in the future.
    """

    @classmethod
    def get_or_create_certificate_template(cls, course: "kinesinlms.course.models.Course") \
            -> Tuple[CertificateTemplate, bool]:
        """
        Get the certificate template for a course.
        Create a generic one if none exists.

        Args:
            course:         The course to get the certificate template for.

        Returns:
            The certificate template for the course.

        Raises:
            CertificateTemplate.DoesNotExist: If no certificate template exists for the given course and auto_create is False.
        """

        try:
            certificate_template = CertificateTemplate.objects.get(course=course)
            return certificate_template, False
        except CertificateTemplate.DoesNotExist:
            pass

        certificate_template = cls.create_generic_certificate_template(course=course)

        return certificate_template, True

    @classmethod
    def create_generic_certificate_template(cls, course: "kinesinlms.course.models.Course") -> CertificateTemplate:
        """
        Do generic certificate template setup.
        By default, the generic certificate template will have no signatories.
        """

        certificate_template = CertificateTemplate.objects.create(course=course, custom_template_name=None)
        return certificate_template
