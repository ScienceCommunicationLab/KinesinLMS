import logging
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime
from django.core.exceptions import ObjectDoesNotExist

from kinesinlms.course.models import CohortMembership, Cohort

logger = logging.getLogger(__name__)

User = get_user_model()


def can_enroll(user, course) -> bool:
    if not user:
        raise ValueError("user argument cannot be None")
    if not course:
        raise ValueError("course argument cannot be None")

    if user.is_superuser or user.is_staff:
        return True

    if not course.enrollment_has_started:
        # TODO: Create a beta access table to join students to courses in beta
        # TODO: and then check whether we're in the beta access period
        # today = datetime.today()
        # beta_start = today - timedelta(days=course.days_early_for_beta)
        logger.debug("can_enroll() : User {} is not allowed to enrol in course ID {} "
                     "because course enrollment has not started: ".format(user.username, course.id))
        return False

    return True


def user_is_enrolled(user, course) -> bool:
    if not user:
        raise ValueError("user argument cannot be None")
    if not course:
        raise ValueError("course argument cannot be None")
    try:
        course.enrollments.get(student=user, course=course, active=True)
        return True
    except ObjectDoesNotExist:
        return False


def get_student_cohort(course,
                       student,
                       auto_add_to_default: bool = True) -> Optional[Cohort]:
    """
    Get the student's cohort for a course. If one doesn't
    exist, we'll add them to the 'default' cohort for the course if
    auto_add_to_default is True. (And if that default cohort
    doesn't exist, we'll go ahead and create it first.)

    Args:
        course:
        student:
        auto_add_to_default:        Automatically add student to DEFAULT
                                    cohort if not currently assigned to a cohort.

    Returns:
        A cohort if one can be found, otherwise None

    Raises:
        Exception if student isn't enrolled in the provided course.

    """
    cohort_membership: Optional[CohortMembership] = None
    try:
        cohort_membership = CohortMembership.objects.get(cohort__course=course, student=student)
        return cohort_membership.cohort
    except CohortMembership.MultipleObjectsReturned:
        logger.exception(f"Student {student} belongs to multiple cohorts in course: {course}! Using most recent...")
        cohort_membership = CohortMembership.objects.filter(cohort__course=course, student=student).last()
        return cohort_membership.cohort
    except CohortMembership.DoesNotExist:
        pass

    if cohort_membership is None and auto_add_to_default:
        if not user_is_enrolled(user=student, course=course):
            raise Exception(f"Student {student} is not enrolled in "
                            f"course {course} so cannot be part of a cohort.")
        logger.info(f"get_student_cohort() Student {student} does not belong to a Cohort. "
                    f"Adding to default cohort...")
        cohort_membership: CohortMembership = course.add_to_cohort(user=student)
        return cohort_membership.cohort

    return None


def update_node_time(node, current_time):
    release_dt_utc = node.get('release_datetime_utc', None)
    release_date = parse_datetime(release_dt_utc)
    node['is_released'] = current_time > release_date
    node['release_datetime'] = release_date

