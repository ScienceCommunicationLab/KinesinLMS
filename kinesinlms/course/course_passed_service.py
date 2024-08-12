# Service methods for CoursePassed and related.
import logging
from typing import Optional
from kinesinlms.users.models import User
from kinesinlms.badges.models import BadgeClass, BadgeClassType
from kinesinlms.badges.utils import get_badge_service
from kinesinlms.certificates.models import Certificate
from kinesinlms.certificates.service import CertificateTemplateFactory
from kinesinlms.course.models import Course, CoursePassed
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)


def student_passed_course(student: User, course: Course) -> Optional[CoursePassed]:
    """
    Perform all tasks required when a student passes a course.

    This method is not part of the CoursePassed model as it has
    concerns that cut across other models. (e.g. Badges)

    Args:
            student:
            course:

    Returns:

        An instance of the new CoursePassed object, or None
        if CoursePassed could not be created.

    """

    logger.info(
        f"STARTING COURSE COMPLETION process for student {student} course {course}"
    )

    # MARK COMPLETION
    try:
        course_passed, created = CoursePassed.objects.get_or_create(
            course=course, student=student
        )
        logger.info(f"Created course passed: {course_passed}")
    except Exception:
        logger.exception("Could not create CoursePassed object!")
        return None

    if course_passed:
        Tracker.track(
            event_type=TrackingEventType.COURSE_PASSED.value,
            user=student,
            course=course,
        )

    # AWARD CERT...
    if course.enable_certificates:
        certificate_template, created = (
            CertificateTemplateFactory.get_or_create_certificate_template(course)
        )

        try:
            certificate, created = Certificate.objects.get_or_create(
                certificate_template=certificate_template, student=student
            )
            logger.info(
                f"Created certificate : {certificate} for student {student.anon_username}"
            )
        except Exception:
            logger.exception("Could not create Certificate object! : {e}")
            certificate = None

        if certificate:
            Tracker.track(
                event_type=TrackingEventType.COURSE_CERTIFICATE_EARNED.value,
                user=student,
                course=course,
            )

    # AWARD BADGE...
    if course.enable_badges:
        badge_class = None
        try:
            badge_class = BadgeClass.objects.get(
                course=course, type=BadgeClassType.COURSE_PASSED.name
            )
        except BadgeClass.DoesNotExist:
            logger.error(
                f"Course {course}is marked enable_badges but no BadgeClass is defined"
            )

        badge_assertion = None
        if badge_class:
            try:
                badge_class = BadgeClass.objects.get(
                    course=course, type=BadgeClassType.COURSE_PASSED.name
                )
                # Create a local BadgeAssertion and start the async process to
                # generate the external badge assertion.
                service = get_badge_service()
                # Do this async. We don't want the current request to be hung up if
                # the external badge provider takes time.
                badge_assertion = service.issue_badge_assertion(
                    badge_class=badge_class, recipient=student, do_async=True
                )

                if badge_assertion:
                    course_passed.badge_assertion = badge_assertion
                    course_passed.save()
                    logger.info(
                        f"Created badge assertion : {badge_assertion} for student {student.anon_username}"
                    )
                else:
                    raise Exception(
                        "issue_badge_assertion() did not return a badge assertion instance."
                    )

            except Exception:
                logger.exception("Error when trying to issue badge")

        if badge_assertion and badge_class:
            badge_earned_event_data = {
                "badge_class_id": badge_class.id,
                "badge_class_slug": badge_class.slug,
                "badge_class_type": badge_class.type,
                "badge_assertion_id": badge_assertion.id,
            }
            Tracker.track(
                event_type=TrackingEventType.COURSE_BADGE_EARNED.value,
                user=student,
                course=course,
                event_data=badge_earned_event_data,
            )

    return course_passed
