import logging
from typing import List, Tuple

from django.contrib import messages
from django.utils.timezone import now
from django.contrib.auth.models import Group

from kinesinlms.catalog.service import do_enrollment
from kinesinlms.course.utils import user_is_enrolled
from kinesinlms.users.models import GroupTypes, InviteUser, User

logger = logging.getLogger(__name__)


def process_invite_user(
    new_user: User, invite_user: InviteUser
) -> List[Tuple[int, str]]:
    """
    Do all actions required once an "InviteUser" has registered.
    Right now that just means auto-enrolling them in a target course.

    TODO:
        -   Later we might want to extend this to do things like e.g.
            set the user up as a CourseEducator if they're marked for that.

    Args:
        new_user        A User instance for the user who just registered
        invite_user     An instance of InviteUser encapsulating things user have been invited to.
        request         An instance of Django messages if any messages should be sent back to
                        user after registration.

    Returns:
        An list of messages, each a tuple with message type and message string,
        indicating what actions have been taken. These can be used to
        create messages to return to the user via the response object.

        ex: (messages.INFO, "You were enrolled)

    """

    invite_messages = []

    if not invite_user.cohort:
        logger.error(
            f"Cannot auto-enroll InviteUser {invite_user} as the instance does not have a course set."
        )
        return invite_messages

    cohort = invite_user.cohort
    course = cohort.course

    # Check to make sure student isn't already somehow enrolled.
    is_already_enrolled = user_is_enrolled(user=new_user, course=course)
    if is_already_enrolled:
        if not invite_user.registered_date:
            invite_user.registered_date = now()
            invite_user.save()
        return invite_messages

    # Enroll invited user into target course.
    try:
        do_enrollment(user=new_user, course=course, cohort=cohort)
        logger.info(
            f"Auto-enrolled newly registered 'invite' user {invite_user} "
            f"into course {course} cohort {cohort}"
        )
        invite_user.registered_date = now()
        invite_user.save()
        invite_messages.append(
            (
                messages.INFO,
                f"NOTE: You have been automatically enrolled in "
                f"the course '{course.display_name}'",
            )
        )
    except Exception:
        logger.exception(
            f"Could not enroll newly registered 'invite' user {invite_user}"
        )

    return invite_messages


def create_default_groups():
    """
    Create all default groups for KinesinLMS
    """
    logger.info("Creating default groups for KinesinLMS")
    groups = []
    for group_type in GroupTypes:
        group, group_created = Group.objects.get_or_create(name=group_type.name)
        if group_created:
            logger.debug(f" - created '{group_type.name}' group")
        else:
            logger.debug(f" - '{group_type.name}' group already exists")
        groups.append(group)
    return groups
