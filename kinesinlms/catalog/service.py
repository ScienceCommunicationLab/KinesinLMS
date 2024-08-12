import logging

from django.contrib.auth.models import Group
from django.utils.timezone import now

from kinesinlms.course.models import Enrollment
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)


class StudentAlreadyEnrolled(Exception):
    pass


class EnrollmentPeriodHasNotStarted(Exception):
    pass


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HELPER METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def do_enrollment(
    user=None, course=None, cohort=None, check_enrollment_period_started: bool = False
) -> Enrollment:
    """Enrolls a user in a course.

    This method enrolls a user in a course as well as ancillary
    activities like :
        - adding the user to the course group
        - adding the user to a course cohort
        - adding the user to Discourse discussion forums course and cohort groups

    Enrolling before enrollment is open:

    We allow enrollments before the enrollment date if the check_enrollment_period_started
    boolean argument is False. That way, an admin or other internal process that is calling this
    method directly can indicate it doesn't want to respect the enrollment date.
    Otherwise, the check_enrollment_period_started should be set to True (like when
    calling from a view method exposed to users).

    Args:
        user:                               Instance of User model.
        course:                             Instance of Course model to enroll user in.
        cohort:                             Target cohort to enroll user in. If None, use DEFAULT cohort.
        check_enrollment_period_started:    Respect the enrollment open date if defined.

    Returns:
        Instance of an Enrollment model.

    """

    logger.debug(f"do_enrollment() called for user: {user} course {course}")

    # Check enrollment date if required.
    if not user.is_superuser and check_enrollment_period_started:
        logger.info("  - checking to see if enrollment is open")
        enrollment_date = course.enrollment_start_date
        if enrollment_date and enrollment_date < now():
            logger.error(
                "  - enrollment is not open. Raising EnrollmentPeriodHasNotStarted exception"
            )
            raise EnrollmentPeriodHasNotStarted()

    # Add the user to a course cohort.
    # Important to do this before creating the enrollment, because we
    # need that cohort as part of the enrollment save signal.
    # This will most likely be the DEFAULT cohort.
    try:
        cohort_membership = course.add_to_cohort(user=user, cohort=cohort)
        logger.debug(f"Added user to cohort {cohort_membership} in course {course}")
    except Exception as e:
        raise Exception(
            "do_enrollment(): Could not add new user to a course cohort"
        ) from e

    # Create an enrollment instance to represent enrollment...
    # There might already be an enrollment instance for this user/course if they've unenrolled.
    # If so, we'll just reactivate it.
    try:
        enrollment = Enrollment.objects.get(student=user, course=course)
    except Enrollment.DoesNotExist:
        enrollment = Enrollment.objects.create(student=user, course=course, active=True)
        # Let exceptions bubble up here...
    if not enrollment.active:
        enrollment.active = True
        enrollment.save()

    # From here, catch exceptions. We'll
    # let the user continue on their way, and try to
    # troubleshoot any issues if we see them in Sentry.

    # Add user to Django group for course.
    # We have some permissions that derive from membership to the Django Group for this course.
    # TODO: Right now the group is just for a course run. It doesn't yet involve cohorts.
    # TODO: We may need to update this to be granular enough for cohorts.
    try:
        group_name = course.course_group_name
        logger.debug("Adding user to course group: {}".format(group_name))
        group = Group.objects.get(name=group_name)
        try:
            group.user_set.add(user)
        except Exception:
            logger.exception(
                f"do_enrollment(): Couldn't add user {user} to group "
                f"{group}. FAILING SILENTLY."
            )
    except Group.DoesNotExist:
        logger.exception(
            f"do_enrollment(): Could not add user to course group for "
            f"{course} because it doesn't exist. FAILING SILENTLY."
        )
    except Exception as e:
        logger.exception(
            f"do_enrollment(): Could not add user to course group for "
            f"{course} FAILING SILENTLY. Exception: {e} "
        )

    # Finally, report activity
    try:
        if hasattr(cohort_membership, "cohort"):
            cohort_id = cohort_membership.cohort.id
            cohort_name = str(cohort_membership.cohort)
        else:
            logger.warning(
                "do_enrollment() Could not find cohort in cohort_membership."
            )
            cohort_id = "?"
            cohort_name = "?"

        Tracker.track(
            event_type=TrackingEventType.ENROLLMENT_ACTIVATED.value,
            user=enrollment.student,
            course=course,
            event_data={"cohort_id": cohort_id, "cohort_name": cohort_name},
        )
    except Exception:
        logger.exception(
            "do_enrollment(): Could not create tracking event for ENROLLMENT_ACTIVATED"
        )

    return enrollment


def do_unenrollment(user=None, course=None) -> Enrollment:
    """
    Unenrolls a user from a course. Does not delete an existing
    enrollment instance, just makes it 'inactive'.

    Args:
        user:       Instance of User to unenroll from course.
        course:     Instance of Course to unenroll user from.

    Returns:
        Enrollment instance, now set to 'inactive'.

    Raises:
        Enrollment.DoesNotExist exception if user isn't enrolled in course.
    """

    # Allow the DoesNotExist exception to bubble up.
    enrollment = Enrollment.objects.get(student=user, course=course)
    enrollment.active = False
    enrollment.save()

    # Remove user from cohort in course...
    try:
        course.remove_from_cohort(user=user)
    except Exception as e:
        logger.exception(
            f"do_unenrollment(): Could not remove user from "
            f"course cohorts. Exception: {e}"
        )

    # Remove user from Django group for course...
    try:
        group_name = course.course_group_name
        logger.debug("Removing user from course group: {}".format(group_name))
        group = Group.objects.get(name=group_name)
        group.user_set.remove(user)
    except Group.DoesNotExist:
        logger.error(
            f"do_unenrollment(): Couldn't remove user "
            f"from group {course.course_group_name} because "
            f"that group doesn't exist."
        )
    except Exception:
        logger.exception(f"Couldn't remove user from group {course.course_group_name}")

    # Finally, report activity
    try:
        Tracker.track(
            event_type=TrackingEventType.ENROLLMENT_DEACTIVATED.value,
            user=enrollment.student,
            course=course,
        )
    except Exception:
        logger.exception(
            "do_unenrollment(): Could not create tracking event for ENROLLMENT_DEACTIVATED"
        )

    return enrollment
