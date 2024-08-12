import logging

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from kinesinlms.course.models import Course
from kinesinlms.forum.models import CohortForumGroup
from kinesinlms.forum.utils import get_forum_service

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=Course)
def course_deleted(sender, instance: Course, **kwargs):  # noqa: F841
    """
    If a Course is deleted, remove the associated CourseForumGroup,
    ForumCategory.

    Pre_delete because we need the cohorts before they're wiped out
    by the delete CASCADE from Course.
    """

    logger.debug(f"Course {instance.token} deleted. Removing all related Discourse items.")
    course = instance
    # Delete cohort_forum_groups and related subcategories
    cohort_forum_groups = CohortForumGroup.objects.filter(course=course).all()

    forum_service = None
    try:
        forum_service = get_forum_service()
    except Exception:
        logger.exception(f"Could not get forum forum_service for course {course}")

    if forum_service:
        for cohort_forum_group in cohort_forum_groups:
            try:
                forum_service.delete_forum_subcategory_for_cohort_forum_group(cohort_forum_group=cohort_forum_group)
            except Exception:
                logger.exception(f"Could not delete Discourse subcategory "
                                 f"for cohort_forum_group {cohort_forum_group}")

            try:
                forum_service.delete_cohort_forum_group(cohort_forum_group=cohort_forum_group,
                                                        delete_default=True)
            except Exception:
                logger.exception(f"Could not delete Discourse Group for "
                                 f"cohort_forum_group {cohort_forum_group}")

        # Now delete group and subcategory for the course itself
        try:
            forum_service.delete_forum_subcategory_for_course(course=course)
        except Exception:
            logger.exception(f"Could not delete Discourse Group for course {course}")

        try:
            forum_service.delete_course_forum_group(course=course)
        except Exception:
            logger.exception(f"Could not delete Discourse group for course{course}")

        # Now delete top-level category
        try:
            forum_service.delete_forum_category(course=course)
        except Exception:
            logger.exception(f"Could not delete Discourse category for course {course}")
