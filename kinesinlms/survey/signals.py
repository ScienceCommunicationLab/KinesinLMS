import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from kinesinlms.course.models import CoursePassed, Enrollment
from kinesinlms.survey.constants import SurveyType
from kinesinlms.survey.service import SurveyEmailService

logger = logging.getLogger(__name__)


# noinspection PyUnusedLocal
@receiver(post_save, sender=Enrollment)
def handle_course_enrolled(sender, instance: Enrollment, **kwargs):
    """
    When a user enrolls in a course, create (and therefore schedule) SurveyEmail
    for all survey types that should be scheduled at the beginning of a course.

    Args:
        sender:
        instance:
        kwargs:

    Returns:
        ( nothing )
    """

    enrollment = instance

    try:
        course = enrollment.course
        user = enrollment.student
        course_surveys = course.surveys.all()
    except Exception:
        logger.exception("Could not get objects related to " "course survey completion")
        return None

    # DON'T BOTHER IF NO SURVEYS DEFINED FOR COURSE...
    if not course_surveys:
        logger.info(
            f"#Survey: User {user} enrollment changed in course {course} "
            f"but no surveys defined for scheduling so nothing to do..."
        )
        return None

    if enrollment.active:
        # Student is enrolling so schedule them for survey emails.
        try:
            SurveyEmailService.schedule_survey_emails_for_start_of_course(
                user=user, 
                course_surveys=course_surveys,
            )
        except Exception:
            logger.exception(
                f"#Survey: User {user} unerolled in course {course} "
                f"but encountered error when trying to schedule SurveyEmails."
            )
    else:
        # User is unenrolling to unschedule them for survey emails.
        try:
            SurveyEmailService.unschedule_survey_emails(course, user)
        except Exception:
            logger.exception(
                f"#Survey: User {user} unerolled in course {course} "
                f"but encountered error when trying to delete scheduled SurveyEmails."
            )
        return None


# noinspection PyUnusedLocal
@receiver(post_save, sender=CoursePassed)
def handle_course_passed(sender, instance: CoursePassed, **kwargs):
    """
    When a user completes a course, create (and therefore schedule) SurveyEmails
    for all survey types that should be scheduled when a user completes successfully.

    Args:
        sender:
        instance:
        kwargs:

    Returns:
        ( nothing )
    """
    course_passed = instance
    try:
        course = course_passed.course
        user = course_passed.student
        course_surveys = course.surveys.all()
    except Exception:
        logger.exception("Could not get objects related to " "course survey completion")
        return

    if not course_surveys or len(course_surveys) == 0:
        logger.info(
            f"#Survey: User {user} completed course but no "
            f"surveys for course {course} defined for scheduling."
        )
        return None

    # Schedule surveys that apply for a user who's finished a course.
    relevant_survey_types = [SurveyType.POST_COURSE.name, SurveyType.FOLLOW_UP.name]
    for course_survey in course_surveys:
        if (
            course_survey.type in relevant_survey_types
            and course_survey.send_reminder_email
        ):
            try:
                SurveyEmailService.schedule_survey_email(course_survey, user)
            except Exception:
                logger.exception(
                    f"Could not schedule SurveyEmail for survey {course_survey} and user {user}"
                )
