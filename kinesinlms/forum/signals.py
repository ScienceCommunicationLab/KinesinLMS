import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from kinesinlms.course.models import Cohort, CohortMembership, Enrollment
from kinesinlms.course.utils import get_student_cohort
from kinesinlms.forum.models import ForumCategory, CohortForumGroup
from kinesinlms.forum.service.base_service import BaseForumService
from kinesinlms.forum.utils import get_forum_service

logger = logging.getLogger(__name__)


# Most of our 'setup' tasks for an external forum happen here: we listen for save signals from things like
# a course or a cohort, and then we create the corresponding structure in our external forum service.

# The only thing we *don't* handle here is adding a new enrollee to an external forum group.
# That happens as a celery task (it's a celery task because we don't want it to slow up or
# error out the user's enrollment process).

# ~~~~~~~~~~~~~~~~~~~~~~~~~
# ADMIN ACTIONS
# ~~~~~~~~~~~~~~~~~~~~~~~~~

# Handle changes that arise from admin or system actions, like creating a new cohort.

# noinspection PyUnusedLocal
@receiver(post_save, sender=Cohort)
def cohort_saved(sender, instance: Cohort, created, **kwargs):
    """
    After a cohort is saved, we need to set up the
    necessary forum items:
        - groups
        - subcategory under the category for the cohort's course
        - topics for ForumTopic Blocks in the course.

    Note: We only do this if the forum category for the course
    has been set up. We ignore otherwise. During course import,
    the default cohort is created before the import is finished, so
    we're going to ignore that signal and let the "import finished" signal
    handle all the setup. But when an admin creates a cohort for the course
    later, we'll handle it here.

    Note: This *does not* need to be async, since the admin should be
    then one setting up cohorts, before enrollments into that cohort start.
    """
    cohort = instance

    if not created:
        # TODO: What do we do with CohortForumGroup if Cohort is updated?
        logger.info("cohort_saved(): cohort updated (not created). Ignoring signal")
        return

    # Only proceed if forum category has been set up
    course = cohort.course
    try:
        ForumCategory.objects.get(course=course)
    except ForumCategory.DoesNotExist:
        logger.warning("Received a signal that a cohort was created. However, "
                       "the forum Category does not exist yet. Therefore "
                       "we can't create the CohortForumGroup yet. So ignoring.")
        return

    if cohort.cohort_forum_group is not None:
        # If the cohort already has a forum_cohort
        # assigned, we don't have to do anything
        return

    if not CohortForumGroup.objects.filter(course=course, is_default=True).exists():
        logger.warning(f"No DEFAULT CohortForumGroup exists for course {course}."
                       f"Creating a new DEFAULT CohortForumGroup.")
        try:
            forum_service = get_forum_service()
            default_cohort = course.get_default_cohort()
            default_cohort_forum_group, created = forum_service.get_or_create_default_cohort_forum_group(
                cohort=default_cohort)
            forum_service.populate_cohort_forum_group_with_subcategory_and_topics(
                cohort_forum_group=default_cohort_forum_group)
        except Exception as e:
            logger.exception(f"Could not configure new default CohortForumGroup. This means"
                             f"new cohort {cohort} could not be assigned a cohort_forum_group.")
            return

    # Assign the 'default' forum cohort to this cohort.
    default_cohort = CohortForumGroup.objects.get(course=course, is_default=True)
    cohort.cohort_forum_group = default_cohort
    cohort.save()


# noinspection PyUnusedLocal
@receiver(post_delete, sender=Cohort)
def cohort_deleted(sender, instance: Cohort, **kwargs):
    """
    If a cohort is deleted, remove the associated CohortForumGroup if
    it exists, and it's not the 'default'.
    As part of this operation, Delete all the subcategories in forum
    beneath that CohortForumGroup.
    """
    cohort = instance

    if not cohort or not cohort.cohort_forum_group:
        return
    if cohort.cohort_forum_group.is_default:
        # We don't delete the 'default' CohortForumGroup.
        return

    try:
        service = get_forum_service()
    except Exception:
        logger.exception("cohort_deleted(): Could not get forum service. "
                         "Cannot continue cohort_deleted() signal handler")
        return

    # Delete the forum subcategory assigned to this cohort.
    try:
        service.delete_forum_subcategory_for_cohort_forum_group(cohort_forum_group=cohort.cohort_forum_group)
    except Exception as e:
        logger.exception(f"Could not delete cohort subcategories for cohort {cohort.cohort_forum_group}")

    # Delete the forum group assigned to this cohort.
    try:
        try:
            service.delete_cohort_forum_group(cohort_forum_group=cohort.cohort_forum_group,
                                              delete_default=True)
        except Exception as e:
            logger.exception(f"Could not delete cohort group: {cohort.cohort_forum_group}")
    except Exception as e:
        logger.exception(f"Could not delete forum Group for cohort {cohort}")


# ~~~~~~~~~~~~~~~~~~~~~~~~~
# STUDENT ACTIONS
# ~~~~~~~~~~~~~~~~~~~~~~~~~

# Handle student actions that need a corresponding change in forum

# noinspection PyUnusedLocal
@receiver(post_save, sender=Enrollment)
def student_enrollment_changed(sender, instance: Enrollment, created, **kwargs):
    """
    When a student enrolls or unenrolls in a course, add them to or
    remove them from the forum 'course' group.

    IMPORTANT: Student should already be part of a cohort by this point.
    If we don't have a cohort we can't set up the CohortForumGroup.

    It's important we catch all errors here as we don't want to stop any parent
    processes from completing.
    
    Args:
        sender:
        instance:
        created:
        kwargs:

    Returns:
        ( nothing )
    """
    enrollment = instance
    student = enrollment.student
    course = enrollment.course

    try:
        service: BaseForumService = get_forum_service()
    except Exception:
        logger.exception("student_enrollment_changed(): Could not get forum service.")
        return

    # TODO:
    #  Check if student exists in forum. They should have been added upon registration
    #  but perhaps that process failed and now when we're ready to add them to a forum
    #  group, the forum won't recognize the user.

    if enrollment.active:
        # STUDENT ENROLLED.
        # Add student to forum 'Course' group for this course
        try:
            course_forum_group_id = course.course_forum_group.group_id
            username = student.username
            # TODO: Make this a proper async call...right now we're doing in process...
            try:
                service.add_user_to_group(group_id=course_forum_group_id, username=username)
            except Exception as e:
                logger.exception(f"add_user_to_forum_group() couldn't add username "
                                 f"{username} to discussion group via API call. error: {e}")
                return
        except Exception as e:
            logger.exception(f"Error adding student {student} to forum course "
                             f"group for course {course}")
            pass

        # We need to try to add the student to the forum cohort group for this course,
        # even though that also happens when the student is added to a cohort.
        # We have to do this here because the student's enrollment may have been made
        # inactivate and then active again, so the cohort membership is already established.
        # If they're already added, we'll just assume the add_user_to_forum_group will
        # throw an exception, with forum saying they already belong.
        try:
            cohort = get_student_cohort(course=course, student=student)
            cohort_forum_group = getattr(cohort, 'cohort_forum_group', None)
            if cohort_forum_group is None:
                raise Exception(f"Cohort {cohort} does not have cohort_forum_group defined.")
            cohort_forum_group_id = cohort_forum_group.group_id
            if cohort_forum_group_id is None:
                raise Exception(f"CohortForumGroup {cohort_forum_group} group_id "
                                f"property is not defined.")
            username = enrollment.student.username
            service.add_user_to_group(group_id=cohort_forum_group_id,
                                      username=username)
        except Exception as e:
            logger.exception(f"Error adding student {enrollment.student} to forum "
                             f"cohort group for course {enrollment.course}: {e}")
            pass
    else:
        # STUDENT UNENROLLED.
        # Remove student from forum 'Cohort' Group for this course...
        try:
            cohort = get_student_cohort(course=enrollment.course,
                                        student=enrollment.student,
                                        auto_add_to_default=False)
            if cohort:
                cohort_forum_group_id = cohort.cohort_forum_group.group_id
                username = enrollment.student.username
                # TODO: Make this a proper async call...right now we're doing in process...
                try:
                    service = get_forum_service()
                    service.remove_user_from_group(group_id=cohort_forum_group_id, username=username)
                except Exception as e:
                    logger.exception("remove_user_from_forum_group() couldn't complete API call.")
                    return
            else:
                logger.error(f"student_enrollment_changed(): Student just unenrolled. But could "
                             f"not find student cohort for enrollment {enrollment}")
        except Exception as e:
            logger.exception(f"Error removing student {enrollment.student} from forum "
                             f"cohort group for course {enrollment.course}.")
            pass

        # Remove student from forum 'Course' Group for this course...
        try:
            course_forum_group_id = enrollment.course.course_forum_group.group_id
            username = enrollment.student.username

            service.remove_user_from_group(group_id=course_forum_group_id,
                                           username=username)
        except Exception as e:
            logger.exception(f"Error removing student {enrollment.student} from forum "
                             f"course group for course {enrollment.course}.")
            pass


# noinspection PyUnusedLocal
@receiver(post_save, sender=CohortMembership)
def cohort_membership_saved(sender, instance: CohortMembership, created, **kwargs):
    """
    When a student joins a cohort, add them to the corresponding forum group.

    It's important we catch all errors here as we don't want to stop any parent
    processes from completing.

    TODO:   We want this to spawn a celery task for this as we don't want a delay in
            course enrollment (which is probably what kicked off this signal).
    """
    cohort_membership = instance
    if not hasattr(cohort_membership, 'cohort'):
        logger.exception(f"cohort_membership_saved() cannot add student {cohort_membership.student} "
                         f"to forum as the CohortMembership instance {cohort_membership} "
                         f"does not have a cohort.")
        return
    cohort = cohort_membership.cohort

    if not hasattr(cohort, 'cohort_forum_group'):
        logger.exception(f"cohort_membership_saved() cannot add student {cohort_membership.student} "
                         f"to forum as the cohort {cohort_membership.cohort} does not have "
                         f"a cohort_forum_group defined.")
        return
    cohort_forum_group = cohort.cohort_forum_group

    if not cohort_forum_group:
        logger.exception(f"cohort_membership_saved() cannot add student {cohort_membership.student} "
                         f"to forum as the DiscoursCohortGroup {cohort_forum_group} "
                         f"is not defined.")
        return

    if not cohort_forum_group.group_id:
        logger.exception(f"cohort_membership_saved() cannot add student {cohort_membership.student} "
                         f"to forum as the DiscoursCohortGroup {cohort_forum_group} "
                         f"does not have a group_id defined.")
        return

    try:
        username = cohort_membership.student.username
        # TODO:
        #   Make this a proper async call.
        #   Right now we're doing in process...
        service = get_forum_service()
        if service:
            service.add_user_to_group(group_id=cohort_forum_group.group_id,
                                      username=username)
    except Exception:
        logger.error(f"Could not add student in {cohort_membership} to forum group. ")


# noinspection PyUnusedLocal
@receiver(post_delete, sender=CohortMembership)
def cohort_membership_deleted(sender, instance: CohortMembership, **kwargs):
    """
    Signal handler to run when a cohort membership is deleted. This
    happens when a student leaves a cohort.

    At the moment, this method's only task is to remove the student from the
    corresponding forum Cohort group.

    IMPORTANT: We want this to spawn a celery task as we don't want a delay in
    course unenrollment (which is probably what kicked off this signal).
    """
    cohort_membership = instance
    if not hasattr(cohort_membership, 'cohort'):
        logger.error(f"cohort_membership_deleted() signal: Could not remove student in CohortMembership "
                     f"{cohort_membership} from forum group as no Cohort object exists for "
                     f"this CohortMembership.")
        return
    cohort = cohort_membership.cohort

    if not hasattr(cohort_membership, 'student'):
        logger.error(f"cohort_membership_deleted() signal: Could not remove student in CohortMembership "
                     f"{cohort_membership} from forum Cohort Group because CohortMembership instance"
                     f"has no user defined.")
        return
    student = cohort_membership.student

    if not hasattr(cohort, 'cohort_forum_group'):
        # ForumCohort may not have been assigned to a Cohort. This will happen when
        # testing in an environment where forum items were not creating during course import.
        # This could also happen if a course hasn't been associated with forum.
        logger.warning(f"cohort_membership_deleted() signal: Could not remove student in "
                       f"CohortMembership {cohort_membership} from forum group as a Cohort object does "
                       f"exist ({cohort}), but no CohortForumGroup exists for this Cohort.")
        return

    cohort_forum_group = cohort.cohort_forum_group
    forum_group_id = None
    if cohort_forum_group:
        forum_group_id = cohort_forum_group.group_id
        if not forum_group_id:
            logger.error(f"cohort_membership_deleted() signal: Could not remove student in CohortMembership "
                         f"{cohort_membership} from CohortForumGroup instance {cohort_forum_group} because"
                         f"the CohortForumGroup instance does not have a 'group_id' defined to represent "
                         f"that cohort in forum.")
            return
    else:
        logger.error("cohort_membership_deleted() signal: Could not remove student from CohortForumGroup "
                     "as cohort.cohort_forum_group is None")
        return

    try:
        username = student.username
        service = get_forum_service()
        if service:
            service.remove_user_from_group(group_id=forum_group_id,
                                           username=username)
    except Exception:
        logger.exception(f"Could not remove student in {cohort_membership} from forum "
                         f"group ID {forum_group_id}.")
