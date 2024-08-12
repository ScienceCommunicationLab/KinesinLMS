"""
Defines a service class that provides a high-level interface to the Discourse API.
NOTE: This is older code written for direct interaction with Discourse.
Still working on getting this to align with BaseForumService.
"""

import hashlib
import hmac
import json
import logging
from base64 import b64encode, b64decode
from typing import List, Dict, Optional, Tuple
from urllib.parse import unquote, urlencode, parse_qs

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from pydiscourse.exceptions import DiscourseClientError

from kinesinlms.core.utils import is_valid_hex_string
from kinesinlms.course.models import Cohort, CourseUnit, Course, Enrollment
from kinesinlms.forum.clients.discourse_client import DiscourseClient
from kinesinlms.forum.models import (CohortForumGroup, ForumSubcategory, ForumCategory, ForumTopic,
                                     ForumSubcategoryType,
                                     ForumProvider, ForumActivityType, CourseForumGroup)
from kinesinlms.forum.service.base_service import BaseForumService, ForumAPIUnsuccessful, ForumAPIFailed, \
    ForumServiceError
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.learning_library.models import Block
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)

User = get_user_model()


# CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class DiscourseForumService(BaseForumService):
    """
    Implements the BaseForumService for use
    with Discourse.org.

    Communications with Discourse require that a
    username and api key have been set up in Discourse
    and that:
    - the username has been saved to the ForumProvider model
    - the FORUM_API_KEY env variable has been set

    (We save the api key in the env rather that in the model
    as it's more secure there.)

    """

    def __init__(self, provider: ForumProvider):
        super().__init__(provider)

        # In this service subclass, we use a specialized client,
        # based on the pydiscourse library, to communicate with Discourse.
        self.client = DiscourseClient(
            provider.forum_url,
            api_username=provider.forum_api_username,
            api_key=provider.api_key)

        logger.debug("DiscourseForumService initialized")

    def is_course_forum_configured(self, course) -> bool:
        """
        Check if a course has a forum configured. We determine
        this by seeing if a group and category have been defined
        for the course.
        """
        try:
            course_forum_group = CourseForumGroup.objects.get(course=course)
            forum_category = ForumCategory.objects.get(course=course)
        except (CourseForumGroup.DoesNotExist, ForumCategory.DoesNotExist):
            return False

        # Even if we have local models for the remote group and category,
        # make sure we have actual IDs, meaning they really exist in Discourse.
        return course_forum_group.group_id and forum_category.category_id

    # ~~~~~~~~~~~~~~~~~~~
    # GROUPS
    # ~~~~~~~~~~~~~~~~~~~

    # Groups should be defined before categories and subcategories
    # as we need to establish group permissions, which are then
    # used when creating new category and subcategories.

    # As a reminder:
    #
    # - A CourseForumGroup is a group in Discourse that holds all students enrolled in a course.
    # - A CohortForumGroup is a group in Discourse that holds all students enrolled in a cohort in a course.
    #
    # So topics that everyone in the course should be able to access should go in a subcategory limited to the forum course group
    # and topics that only students in a particular cohort should be able to access should go in a subcategory limited to the forum cohort group.

    def get_or_create_course_forum_group(self, course: Course) -> Tuple[CourseForumGroup, bool]:
        if not course:
            raise ValueError("course argument may not be None")

        try:
            course_forum_group = CourseForumGroup.objects.get(course=course)
            if course_forum_group.group_id:
                return course_forum_group, False
        except CourseForumGroup.DoesNotExist:
            course_forum_group = None

        group_id, group_name = self._create_group_for_course(course)

        if course_forum_group is None:
            course_forum_group = CourseForumGroup.objects.create(course=course, group_id=group_id, name=group_name)
            was_created = True
        else:
            course_forum_group.group_id = group_id
            course_forum_group.name = group_name
            course_forum_group.save()
            was_created = False

        return course_forum_group, was_created

    def get_or_create_cohort_forum_group(self,
                                         cohort: Cohort,
                                         use_default_cohort_forum_group: bool = True) -> Tuple[CohortForumGroup, bool]:

        """
        Create a new group in Discourse for a particular cohort and return a
        populated CohortForumGroup model instance.

        Note that often KinesinLMS users will want many cohorts in a course, but only one
        forum group for all of them. In this case, this method will return the
        DEFAULT CohortForumGroup for the course.

        If you want to create a new group for a new cohort, set use_default_cohort_forum_group to False.


        """
        if not cohort:
            raise ValueError("cohort argument may not be None")

        course = cohort.course

        if use_default_cohort_forum_group is True and cohort.is_default is False:
            # The user wants this non-DEFAULT cohort to use the DEFAULT cohort group in Discourse
            # (this cohort should see the general discussion the DEFAULT cohort does).
            # So switch the cohort to the DEFAULT cohort before continuing
            cohort = cohort.course.get_default_cohort()

        if cohort.cohort_forum_group:
            cohort_forum_group = cohort.cohort_forum_group
            if cohort.cohort_forum_group.group_id:
                return cohort_forum_group, False
            else:
                # We have a CohortForumGroup model, but it's not fully populated.
                # So we'll add in an ID below...
                pass
        else:
            cohort_forum_group = None

        cohort_forum_group_id, cohort_forum_group_name = self._create_group_for_cohort(cohort)

        if cohort_forum_group is None:
            cohort_forum_group = CohortForumGroup.objects.create(course=course,
                                                                 is_default=cohort.is_default,
                                                                 group_id=cohort_forum_group_id,
                                                                 name=cohort_forum_group_name)
            was_created = True
        else:
            # Make sure existing model is correct
            cohort_forum_group.group_id = cohort_forum_group_id
            cohort_forum_group.name = cohort_forum_group_name
            cohort_forum_group.is_default = cohort.is_default
            cohort_forum_group.save()
            was_created = False

        if cohort.cohort_forum_group != cohort_forum_group:
            cohort.cohort_forum_group = cohort_forum_group
            cohort.save()

        return cohort_forum_group, was_created

    def delete_course_forum_group(self, course: Course, delete_model=True):
        """
        Delete the Discourse Group associated with a Course

        Args:
            course:
            delete_model:        Delete KinesinLMS model for this Discourse item.

        Returns:
            Boolean flag if Group was deleted in Discourse
        """

        if not hasattr(course, 'course_forum_group'):
            logger.info("delete_course_forum_group() was called for course {course}...but this "
                        "course does not have a CohortForumGroup to delete. So nothing to do here.")
            return False

        course_forum_group: CourseForumGroup = course.course_forum_group
        try:
            self.client.delete_group(groupid=course_forum_group.group_id)
        except Exception:
            raise ForumAPIFailed("Discourse API call failed.")

        if delete_model:
            try:
                course_forum_group.delete()
            except Exception:
                logger.exception(f"Could not delete CourseForumGroup model {course_forum_group}")

        # If we got this far it must have been a 200, so call good. Cohort deleted.
        return True

    def delete_cohort_forum_group(self,
                                  cohort_forum_group: CohortForumGroup,
                                  delete_model=True,
                                  delete_default=False):
        """
        Delete the forum group associated with a cohort.

        Args:
            cohort_forum_group:     An instance of CohortForumGroup
            delete_model:               Delete the local instance of CohortForumGroup, not
                                        just the group on Discourse.
            delete_default:             Delete even if CohortForumGroup is 'default'

        Returns:
            ( nothing )

        Raises:
            Exception if CohortForumGroup is the DEFAULT group.
        """

        if cohort_forum_group and cohort_forum_group.is_default and delete_default is False:
            raise ForumServiceError("Cannot delete the default CohortForumGroup")

        try:
            self.client.delete_group(groupid=cohort_forum_group.group_id)
        except Exception as e:
            # Remote group might have already been deleted if we're e.g.
            # in the process of deleting a course.
            raise ForumAPIFailed(f"Discourse API call failed. Error : {e}")

        if delete_model:
            try:
                cohort_forum_group.delete()
            except Exception:
                logger.exception(f"Could not delete CohortForumGroup model {cohort_forum_group}.")

        # If we got this far it must have been a 200, so call good. Cohort deleted.
        return True

    def _create_group_for_cohort(self, cohort: Cohort) -> Tuple[int, str]:
        """
        Create a group in Discourse for a particular cohort and return
        the new group ID and name.
        If the group already exists in Discourse, just return
        the existing group ID and name.

        Args:
            cohort: The cohort to create the group for.

        Returns:
            Tuple of (group_id, group_name)
        """
        # Get any existing groups in Discourse
        logger.info("Loading existing Discourse groups")
        existing_remote_discourse_groups: Dict[str, int] = {}
        results = self.client.groups()
        if results:
            for result in results:
                g_id = result.get('id')
                name = result.get('name', '')
                existing_remote_discourse_groups[name] = g_id

        course = cohort.course
        if cohort.is_default:
            cohort_forum_group_name = f"{course.token}_co_DEFAULT"
            if len(cohort_forum_group_name) > 20:
                cohort_forum_group_name = cohort_forum_group_name[:20]
            title = f"Default group for cohorts in course {course.token}"
        else:
            cohort_forum_group_name = f"{course.token}_co_{cohort.token}"
            if len(cohort_forum_group_name) > 20:
                cohort_forum_group_name = cohort_forum_group_name[:20]
            title = f"Group for cohort {cohort.name} in course {course.token}"

        logger.debug(f"Trying to create or link default cohort group in "
                     f"Discourse for course: "
                     f"Group name: {cohort_forum_group_name} "
                     f"Title: {title}")

        result = None
        remote_cohort_forum_group_id = existing_remote_discourse_groups.get(cohort_forum_group_name, None)
        if not remote_cohort_forum_group_id:
            # Need to create a new Discourse Group in Discourse to act
            # as the 'default' discourse cohort group.
            try:
                result = self.client.create_group(name=cohort_forum_group_name,
                                                  visible=False,
                                                  title=title)
                # Let's hold on to the ID for the new Group created by Discourse
                # (Yes, for some reason they call the object in the return object 'basic_group')
                remote_cohort_forum_group_id = result['basic_group']['id']
            except Exception:
                raise ForumAPIFailed("create_group_for_cohort() ")

        logger.debug(f"create_group_for_cohort() result: {result}")

        return remote_cohort_forum_group_id, cohort_forum_group_name

    def _create_group_for_course(self, course: Course) -> Tuple[int, str]:
        """
        Create a group in Discourse that holds all students enrolled in course.

        If the group already exists in Discourse (as identified by our default way
        of giving groups an ID), just return its ID and name.

        Otherwise, create a new group in Discourse and return the ID and name.

        Args:
            course:

        Returns:
            Tuple of (group_id, group_name)
        """

        if course is None:
            raise ValueError("course argument may not be None")

        # Get any existing groups in Discourse
        logger.info("Loading existing Discourse groups")
        existing_remote_discourse_groups: Dict[str, int] = {}
        results = self.client.groups()
        if results:
            for result in results:
                g_id = result.get('id')
                name = result.get('name', '')
                existing_remote_discourse_groups[name] = g_id

        # Create COURSE GROUP in Discourse
        # By convention, we use the course token for the Discourse group name...
        # (Remember Discourse doesn't allow group names > 20 chars)
        group_name = course.token
        if len(group_name) > 20:
            group_name = group_name[:20]

        # We use a default group title for now.
        # TODO: This should be configurable in the composer UI.
        title = f"Discourse group for all students of course {course.token}"

        if group_name in existing_remote_discourse_groups:
            group_id = existing_remote_discourse_groups[group_name]
            if group_id:
                # This group was already created, so just return the ID
                return group_id, title

        logger.debug(f"Trying to create or link group in Discourse for course: "
                     f"Group name: {group_name} "
                     f"Title: {title} ...")

        try:
            result = self.client.create_group(name=group_name, visible=False, title=title)
            # Let's hold on to the ID for the new Group created by Discourse
            # (Yes, for some reason they call the object in the return object 'basic_group')
            group_id = result['basic_group']['id']
        except Exception:
            raise ForumAPIFailed("_create_group_for_course() Discourse API call failed. ")

        logger.debug(f"_create_group_for_course() result: {result}")

        return group_id, group_name

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CATEGORIES & SUBCATEGORIES
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_or_create_forum_category(self, course: Course) -> Tuple[ForumCategory, bool]:

        if not course:
            raise ValueError("get_or_create_forum_category() course cannot be None")
        was_created = False
        try:
            forum_category = ForumCategory.objects.get(course=course)
            if forum_category.category_id:
                return forum_category, False
            else:
                # We have a ForumCategory model, but it's not fully populated.
                # So we'll add in an ID below...
                pass
        except ForumCategory.DoesNotExist:
            was_created = False
            forum_category = None

        c_id, c_slug, c_name, c_descrip = self._create_discourse_category_for_course(course)

        if forum_category is None:
            forum_category = ForumCategory.objects.create(course=course)
            was_created = True

        forum_category.category_id = c_id
        forum_category.category_slug = c_slug
        forum_category.category_name = c_name
        forum_category.category_description = c_descrip
        forum_category.save()

        return forum_category, was_created

    def get_or_create_forum_subcategory(self,
                                        forum_category: ForumCategory,
                                        subcategory_type: str,
                                        cohort_forum_group: Optional[CohortForumGroup] = None,
                                        ensure_unique_name: bool = False) \
            -> Tuple[ForumSubcategory, bool]:

        if not forum_category:
            raise ValueError("get_or_create_forum_subcategory() forum_category cannot be None")
        if subcategory_type not in [item.name for item in ForumSubcategoryType]:
            raise ValueError(f"get_or_create_forum_subcategory() type {subcategory_type} is not valid.")

        if subcategory_type == ForumSubcategoryType.COHORT.name:
            if not cohort_forum_group:
                raise ValueError("get_or_create_forum_subcategory() cohort_forum_group must be defined "
                                 "when creating a forum subcategory of type COHORT")
        elif subcategory_type == ForumSubcategoryType.ALL_ENROLLED.name:
            if not forum_category.course:
                raise ValueError("get_or_create_forum_subcategory() forum_category.course "
                                 "must be defined for type ALL_ENROLLED")
            try:
                CourseForumGroup.objects.get(course=forum_category.course)
            except CourseForumGroup.DoesNotExist:
                raise ValueError("get_or_create_forum_subcategory() course must have a "
                                 "course_forum_group defined before creating a subcategory.")

        course = forum_category.course
        logger.debug(f"Creating new subcategory for course {course} of type {subcategory_type}")

        try:
            forum_subcategory = ForumSubcategory.objects.get(forum_category=forum_category)
            if forum_subcategory.subcategory_id:
                return forum_subcategory, False
        except ForumSubcategory.DoesNotExist:
            forum_subcategory = ForumSubcategory.objects.create(forum_category=forum_category)

        try:
            sc_id, sc_slug, sc_name, sc_color = self._create_subcategory(subcategory_type=subcategory_type,
                                                                         parent_category=forum_category,
                                                                         cohort_forum_group=cohort_forum_group,
                                                                         ensure_unique_name=ensure_unique_name)
        except Exception as e:
            logger.exception(f"get_or_create_forum_subcategory() failed. Error: {e}")
            raise ForumServiceError(f"Could not create subcategory in Discourse.")

        forum_subcategory.subcategory_id = sc_id
        forum_subcategory.subcategory_slug = sc_slug
        forum_subcategory.name = sc_name
        forum_subcategory.color = sc_color
        forum_subcategory.type = subcategory_type

        if subcategory_type == ForumSubcategoryType.ALL_ENROLLED.name:
            course_forum_group = CourseForumGroup.objects.get(course=course)
            forum_subcategory.course_forum_group = course_forum_group
        elif subcategory_type == ForumSubcategoryType.COHORT.name:
            forum_subcategory.cohort_forum_group = cohort_forum_group
        else:
            raise ValueError(f"get_or_create_forum_subcategory() type {subcategory_type} is not valid.")

        forum_subcategory.save()

        logger.debug(f"Created Discourse (sub)category {forum_subcategory}")

        return forum_subcategory, True

    def delete_forum_category(self, course: Course, delete_model=True) -> bool:
        """
        Delete the Course's top category in Discourse if it exists.

        Args:
            course:
            delete_model:            Delete the ForumCategory model for this category.

        Returns:
            Boolean indicating whether the deletion happened or not.
        """
        forum_category: ForumCategory = getattr(course, "forum_category")
        if not forum_category:
            logger.info("No ForumCategory defined. Nothing to delete")
            return False

        try:
            self.client.delete_category(category_id=forum_category.category_id)
        except Exception:
            logger.exception(f"Could not delete Discourse category for course {course.token}")

        if delete_model:
            try:
                forum_category.delete()
            except Exception:
                logger.exception(f"Could not delete ForumCategory model {forum_category}")

        # If we got this far it must have been a 200, so call good. (sub)category deleted.
        return True

    def delete_forum_subcategory_for_course(self,
                                            course: Course,
                                            delete_local_model=True) -> Optional[int]:
        """
        Delete the course's (sub)category in Discourse if it exists.
        This corresponds to the ALL_ENROLLED type subcatetory.

        Args:
            course:
            delete_local_model:        Delete the KinesinLMS model for this Subcategory

        Returns:
            ID of ForumSubcategory deleted, otherwise None.
        """

        if not course:
            raise ValueError("cohort must be defined.")

        try:
            course_forum_group: CourseForumGroup = course.course_forum_group
        except CourseForumGroup.DoesNotExist:
            logger.info(f"delete_forum_subcategory_for_course() was called for course {course}, but no "
                        f"CourseForumGroup defined. Nothing to delete.")
            return None

        forum_subcategory: ForumSubcategory = getattr(course_forum_group, "forum_course_subcategory")
        if not forum_subcategory:
            logger.info(f"No forum_subcategory defined for course_forum_group {course_forum_group} ")
            return None

        try:
            self.client.delete_category(category_id=forum_subcategory.subcategory_id)
        except Exception:
            logger.exception(f"Could not delete Discourse (sub)category for course {course}")

        if delete_local_model:
            try:
                forum_subcategory.delete()
            except Exception:
                logger.exception(f"Could not delete ForumSubcategory model {forum_subcategory}")

        # If we got this far it must have been a 200, so call good. (sub)category deleted.
        return forum_subcategory.id

    def delete_forum_subcategory_for_cohort_forum_group(self,
                                                        cohort_forum_group: CohortForumGroup,
                                                        delete_all_topics=True,
                                                        delete_model=True) -> Optional[int]:
        """
        Delete the CohortForumGroup's (sub)category in Discourse if it exists.

        Args:
            cohort_forum_group: An instance of CohortForumGroup

            delete_all_topics:      Delete all the topics in this subcategory
                                    TODO: Not sure this can even be false.

            delete_model:           Delete the CohortForumGroup model for this Subcategory

        Returns:
            ID of discourse subcategory if deleted, otherwise None.

        """

        if not cohort_forum_group:
            raise ValueError("cohort must be defined.")

        try:
            forum_subcategory: ForumSubcategory = cohort_forum_group.forum_cohort_subcategory
        except ForumSubcategory.DoesNotExist:
            logger.info(f"delete_subcategory_for_cohort() was called for "
                        f"cohort_forum_group {cohort_forum_group}. "
                        f"but forum_subcategory was not defined. "
                        f"So nothing to remove there.")
            return None

        # Delete all Topics in subcategory before deleting subcategory
        if delete_all_topics:
            for forum_topic in forum_subcategory.forum_topics.all():
                self.client.delete_topic(forum_topic.topic_id)
                forum_topic.delete()

        # Now delete subcategory
        try:
            self.client.delete_category(category_id=forum_subcategory.subcategory_id)
        except Exception:
            logger.exception(f"Could not delete Discourse (sub)category "
                             f"for forum_subcategory {forum_subcategory}")

        if delete_model:
            try:
                forum_subcategory.delete()
            except Exception:
                logger.exception(f"Could not delete ForumSubcategory model {forum_subcategory}")

        return forum_subcategory.id

    def _create_subcategory(self,
                            subcategory_type: str,
                            parent_category: ForumCategory,
                            cohort_forum_group: CohortForumGroup = None,
                            subcategory_color: str = None,
                            ensure_unique_name: bool = False) -> Tuple[int, str, str, str]:
        """
        Create a subcategory limited to either ALL_ENROLLED in a course or a
        specific CohortForumGroup.

        This method creates the (sub)category in Discourse and restricts
        access to the cohort.

        IMPORTANT:
            If type is ALL_ENROLLED, the course must have a CourseForumGroup defined.
            If type is COHORT, the cohort_forum_group must be defined and provided in args.

        Args:
            subcategory_type:           Type of Subcategory to create.
            parent_category:            Parent category for this subcategory.
            cohort_forum_group:         CohortForumGroup if type is COHORT.
            subcategory_color:          A color for the subcategory. If None, the course's
                                        theme color will be used.
            ensure_unique_name:         If true, subcategory name will be made unique
                                        by adding a suffix to the name

        Returns:
            Tuple of (subcategory_id, subcategory_slug, subcategory_name, subcategory_color)
        """

        # VALIDATE ARGS
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        if not subcategory_type:
            raise ValueError("_create_subcategory() subcategory_type cannot be None")
        if subcategory_type not in [item.name for item in ForumSubcategoryType]:
            raise ValueError(f"_create_subcategory() subcategory_type {subcategory_type} is not valid.")

        if not parent_category:
            raise ValueError("_create_subcategory() parent_category cannot be None")
        if not parent_category.category_id:
            raise ValueError("_create_subcategory() parent_category must have a category_id")

        if cohort_forum_group is None and subcategory_type == ForumSubcategoryType.COHORT.name:
            raise ValueError(f"_create_subcategory() cohort must be defined for type {subcategory_type}")

        course = parent_category.course

        logger.debug(f"Creating subcategory for type: {subcategory_type} "
                     f"parent_category {parent_category} "
                     f"course {course} "
                     f"cohort_forum_group {cohort_forum_group}")

        if subcategory_color and is_valid_hex_string(subcategory_color) == False:
            raise ValueError(f"Invalid hex color : {subcategory_color} ")
        else:
            subcategory_color = course.catalog_description.hex_theme_color

        # DEFINE PERMISSIONS
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        if ensure_unique_name:
            name_suffix = cohort_forum_group.name if cohort_forum_group else course.token
        else:
            name_suffix = None
        subcategory_name = ForumSubcategory.generate_subcategory_name(subcategory_type=subcategory_type,
                                                                      name_suffix=name_suffix)
        if subcategory_type == ForumSubcategoryType.ALL_ENROLLED.name:
            subcategory_slug = ForumSubcategory.generate_subcategory_slug(subcategory_type,
                                                                          course_token=course.token,
                                                                          cohort_group_name=None)
            course_forum_group = course.course_forum_group
            group_name = course_forum_group.name
            # In generate discussion the group members can create topics (permission = 1)
            permissions = {"admins": 1, "staff": 1, group_name: 1}
        else:
            subcategory_slug = ForumSubcategory.generate_subcategory_slug(subcategory_type,
                                                                          course_token=None,
                                                                          cohort_group_name=cohort_forum_group.name)
            group_name = cohort_forum_group.name
            # In course discussion the group members can only reply to topics (permission = 2)
            permissions = {"admins": 1, "staff": 1, group_name: 2}

        # See if subcategory already exists in Discourse
        subcategory_id = None
        remote_discourse_subcategories = self._get_discourse_categories_lookup()
        for sc_id, sc_dict in remote_discourse_subcategories.items():
            sc_slug = sc_dict.get('slug', None)
            if subcategory_slug == sc_slug:
                subcategory_id = sc_id
                break

        if subcategory_id:
            logger.info(f"Subcategory already exists in Discourse (id: {subcategory_id})...no need to create.")
            # TODO: We have to update the subcategory if any permissions have changed.
        else:
            # Create a subcategory in Discourse
            try:
                result = self.client.create_category(name=subcategory_name,
                                                     slug=subcategory_slug,
                                                     parent_id=parent_category.category_id,
                                                     text_color="000000",
                                                     permissions=permissions,
                                                     color=subcategory_color)
                logger.debug(f"Result after creating (sub)category in Discourse: {result}")
                subcategory_id = result['category']['id']
            except Exception as e:
                raise ForumAPIFailed(f"_create_subcategory() Discourse API call failed. Error : {e}")

        return subcategory_id, subcategory_slug, subcategory_name, subcategory_color

    def _create_discourse_category_for_course(self,
                                              course: Course,
                                              name: str = None,
                                              description: str = None) -> Tuple[int, str, str, str]:
        """
        Create a Discourse category for course.
        If the category already exists in Discourse, return existing information.

        IMPORTANT: The correct group must already be created in Discourse for this course.
        We need this group to set permissions in the new category.

        Args:
            course:         The course to create the category for.
            name:           A name for the new course category. If None, a default name will be used.
            description:    A description for the new course category. If None, a default description will be used.

        Returns:
            Tuple of (category_id, category_slug, category_name, category_description)

        Raises:
            Exception if the course does not have a CourseForumGroup defined.
        """
        category_name = course.short_name
        if not category_name:
            category_name = course.display_name
        category_name = category_name[:50]

        category_slug = ForumCategory.generate_category_slug(course_token=course.token)
        category_color = course.catalog_description.hex_theme_color
        category_description = f"This category contains discussion topics for students " \
                               f"enrolled in the “{course.display_name}” course."

        # Set permissions in group:
        # Access only provided to admins, staff, the CohortForumGroup
        # and every CohortForumGroup that exists in the course.
        permissions = {"admins": 1, "staff": 1}

        try:
            # CourseForumGroup
            course_forum_group = CourseForumGroup.objects.get(course=course)
            permissions[course_forum_group.name] = 1
            # All FormCohortGroups...
            cohort_forum_groups = CohortForumGroup.objects.filter(course=course).all()
            for cohort_forum_group in cohort_forum_groups:
                permissions[cohort_forum_group.name] = 1
        except CourseForumGroup.DoesNotExist:
            raise ForumServiceError(f"Could not create category for course {course.token}. "
                                    f"CourseForumGroup is not defined.")
        except Exception as e:
            logger.exception(f"Could not set all permissions correctly for "
                             f"category {category_slug}. Error: {e}")

        # See if category already exists in Discourse
        category_id = None
        remote_discourse_categories = self._get_discourse_categories_lookup()
        for remote_category_id, remote_forum_category_dict in remote_discourse_categories.items():
            remote_category_slug = remote_forum_category_dict.get('slug', None)
            if category_slug == remote_category_slug:
                category_id = remote_category_id
                break

        if category_id:
            logger.info(f"Category already exists in Discourse (id: {category_id})...no need to create.")
            # TODO: We have to update the category if any permissions have changed.
        else:
            # Create a category in Discourse
            try:
                result = self.client.create_category(name=category_name,
                                                     slug=category_slug,
                                                     text_color="000000",
                                                     description=category_description,
                                                     permissions=permissions,
                                                     color=category_color)
                category_id = result['category']['id']
                category_slug = result['category'].get('slug', None)
            except Exception as e:
                raise ForumAPIFailed(f"Discourse API call failed. Error : {e}")

        return category_id, category_slug, category_name, category_description

    def _get_discourse_categories_lookup(self) -> Dict[int, dict]:
        """
        Returns a dictionary of JSON data about categories
        from Discourse, keyed by category_id.
        :return:
        """
        site_json = self.client.site()
        dcategories = site_json['categories']
        dcategories_lookup = {}
        for dcategory in dcategories:
            dcategories_lookup[int(dcategory['id'])] = dcategory
        return dcategories_lookup

    # ~~~~~~~~~~~~~~~~~~~
    # TOPICS
    # ~~~~~~~~~~~~~~~~~~~

    # IMPORTANT:
    # Remember that in Discourse, a topic is just a title. The "content" of the topic
    # is always a first post.

    def user_can_view_topic(self, forum_topic, user) -> bool:
        """
        Args:
            forum_topic:
            user:

        Returns
            Boolean
        """
        if user.is_staff or user.is_superuser:
            return True
        subcat_type = forum_topic.forum_subcategory.type
        if subcat_type == ForumSubcategoryType.ALL_ENROLLED.name:
            # make sure student is enrolled in course
            course = forum_topic.forum_subcategory.forum_category.course
            return Enrollment.objects.filter(course=course, student=user, active=True).exists()
        elif subcat_type == ForumSubcategoryType.COHORT.name:
            # make sure student is in a cohort that
            # has access to the CohortForumGroup
            cohort_forum_group = forum_topic.forum_subcategory.cohort_forum_group
            return Cohort.objects.filter(students__id=user.id, cohort_forum_group=cohort_forum_group).exists()
        else:
            return False

    def get_topic_posts(self, topic_id: int) -> List[dict]:
        topic = self.client.topic_posts(topic_id)
        post_stream = topic.get('post_stream', None)
        if post_stream:
            posts = post_stream['posts']
        else:
            posts = []

        # Always remove the first post, as it's just the top-level one
        # describing the purpose of the topic.
        if len(posts) > 0:
            posts.pop(0)

        forum_url = self.provider.forum_url
        if forum_url[-1] == '/':
            forum_url = forum_url[:-1]

        def get_avatar_url(post_dict) -> str:
            avatar_url = f"{forum_url}{post_dict['avatar_template']}"
            avatar_url = avatar_url.replace("{size}", "90")
            return avatar_url

        # Remove all except key data we need in our Discourse react component
        # At the moment we only need the id, the avatar_template and the 'cooked' content
        cleaned_posts = [
            {
                'id': p['id'],
                'avatar_template': get_avatar_url(p),
                'cooked': p['cooked']
            }
            for p in posts
        ]

        return cleaned_posts

    def topic_url(self, forum_topic: ForumTopic) -> Optional[str]:
        """
        Return the URL to the topic in Discourse.

        Args:
            forum_topic:

        Returns:
            URL to the topic in Discourse.
        """
        if forum_topic.topic_slug:
            url = f"{self.provider.forum_url}"
            if url[-1] != "/":
                url += "/"
            url += f"t/{forum_topic.topic_slug}"
        else:
            url = None
        return url

    def create_topics_for_subcategory(self,
                                      course: Course,
                                      forum_subcategory: ForumSubcategory) -> List[ForumTopic]:
        """
        Create all required topics for a course in the correct Discourse (sub)category.

        This means creating one topic in each subcategory for every discussion topic
        defined in the course.

        IF A TOPIC ALREADY EXISTS IN DISCOURSE:
        Don't create a new Discourse topic if it already exists, although
        do make sure the local ForumTopic is created the correct info.

        Args:
            course:
            forum_subcategory:

        Returns:
            A list of ForumTopic instances, across all subcategories for a course.
        """

        assert course is not None
        assert forum_subcategory is not None

        course_units = CourseUnit.objects.filter(course=course).all()
        subcategory_id = forum_subcategory.subcategory_id
        if not subcategory_id:
            raise ForumServiceError(f"create_topics_for_subcategory() Cannot create topics because"
                                    f" ForumCategory {forum_subcategory} is missing a subcategory_id.")
        logger.info(f"Calling client.category_topics with subcategory_id : {subcategory_id}")
        response = self.client.category_topics(subcategory_id)
        logger.info(f"response: {response}")
        dtopics = response['topic_list']['topics']
        dtopics_lookup = {}
        for dtopic in dtopics:
            title = dtopic['title']
            dtopics_lookup[title] = dtopic

        # Gather all discussion blocks in course
        discussion_blocks = []
        for course_unit in course_units:
            for block in course_unit.contents.all():
                if block.type == BlockType.FORUM_TOPIC.name:
                    discussion_blocks.append(block)

        # Create topics in Discourse for each discussion block,
        # as well as local ForumTopic instances to record Discourse info.
        forum_topics: List[ForumTopic] = []
        for discussion_block in discussion_blocks:
            topic_title = discussion_block.discussion_topic_title
            if not topic_title:
                logger.exception("Cannot create a Discourse topic for "
                                 f"block {discussion_block} "
                                 f"course {course} "
                                 f"because the Block does not have display_name "
                                 f"set (and therefore we have no title for the topic).")
                continue
            dtopic = dtopics_lookup.get(topic_title, None)
            logger.debug(f"Checking Discussion Block {topic_title}...")
            if dtopic:
                # Just create local model
                topic_id = dtopic['id']
                topic_slug = dtopic.get('slug', None)
                try:
                    forum_topic = ForumTopic.objects.get(block=discussion_block,
                                                         forum_subcategory=forum_subcategory)
                    forum_topic.topic_id = topic_id
                    forum_topic.topic_slug = topic_slug
                    forum_topic.save()
                    logger.info(f"Discussion topic {topic_slug} already exists in Discourse and locally. Updated local "
                                f"ForumTopic model instance topic_id and topic_slug.")
                except ForumTopic.DoesNotExist:
                    forum_topic = ForumTopic.objects.create(block=discussion_block,
                                                            forum_subcategory=forum_subcategory,
                                                            topic_id=topic_id,
                                                            topic_slug=topic_slug)
                    logger.info(f"Topic {topic_slug} already exists in Discourse but not locally. Create new local "
                                f"ForumTopic model instance {forum_topic} and setting topic_id and topic_slug.")
            else:
                try:
                    forum_topic = self.create_topic(discussion_block=discussion_block,
                                                    topic_title=topic_title,
                                                    course=course,
                                                    forum_subcategory=forum_subcategory)
                    forum_topics.append(forum_topic)
                except Exception as e:
                    logger.exception(f"Could not create Discourse topic for "
                                     f"block {discussion_block} "
                                     f"course {course} "
                                     f"error: {e}")

        return forum_topics

    def create_or_update_forum_topic(self,
                                     discussion_block: Block,
                                     course: Course) -> List[ForumTopic]:
        """
        Create or update a topic in Discourse for a given Discussion block.

        Args:
            discussion_block:
            course:

        Returns:
            ForumTopic instance
        """
        assert discussion_block is not None, "create_or_update_topic() discussion_block must be defined"
        assert course is not None, "create_or_update_topic() course must be defined"
        assert discussion_block.type == BlockType.FORUM_TOPIC.name

        # Get the subcategory for this block
        forum_subcategories = ForumSubcategory.objects.filter(forum_category__course=course,
                                                              type=ForumSubcategoryType.COHORT.name)

        forum_topics = []
        for subcat in forum_subcategories.all():
            try:
                forum_topic = ForumTopic.objects.get(block=discussion_block,
                                                     forum_subcategory=subcat)
                self.update_topic(forum_topic=forum_topic,
                                  title=discussion_block.discussion_topic_title,
                                  html_content=discussion_block.html_content)
                forum_topics.append(forum_topic)
            except ForumTopic.DoesNotExist:
                forum_topic = None

            if forum_topic is None:
                try:
                    forum_topic = self.create_topic(discussion_block=discussion_block,
                                                    course=course,
                                                    forum_subcategory=subcat)
                    forum_topics.append(forum_topic)
                except Exception as e:
                    logger.exception(f"Could not create Discourse topic for block {discussion_block} "
                                     f"course {course} "
                                     f"error: {e}")

        return forum_topics

    def update_topic(self,
                     forum_topic: ForumTopic,
                     title: str = None,
                     html_content: str = None) -> bool:
        """
        Update a topic's title and/or topic content in Discourse.

        Remember a topic in Discourse is just a title.
        The 'content' of the topic is the first post.

        Args:
            forum_topic:
            title:
            html_content:

        Returns:
            Boolean

        """

        if title is None and html_content is None:
            raise ValueError("update_topic() title and/or html_content must be defined.")

        if title is not None:
            try:
                # Update the topic's title
                response = self.client.update_topic(topic_id=forum_topic.topic_id,
                                                    title=title)
                logger.debug(f"Response from updating topic title: {response}")

            except Exception as e:
                logger.exception(f"Could not update Discourse topic title {forum_topic.topic_id} "
                                 f"for block {forum_topic.block} "
                                 f"error: {e}")
                return False

            # Discourse will change the slug to match the title, so remember the new slug...
            if "basic_topic" in response and "slug" in response['basic_topic']:
                new_topic = response['basic_topic']['slug']
                forum_topic.topic_slug = new_topic
                forum_topic.save()

        # Updating a topic's content is a bit more complicated.
        # We need to update the first post in the topic.
        # See : https://stackoverflow.com/questions/36732694/how-can-i-update-topic-content-using-discourse-api

        if html_content is not None:
            topics = self.client.topic_posts(forum_topic.topic_id)
            first_post = topics['post_stream']['posts'][0]
            try:

                # Update the first posts' content
                response = self.client.update_post(post_id=first_post['id'],
                                                   content=html_content)
                logger.debug(f"Response from updating first post in topic: {response}")

            except Exception as e:
                logger.exception(f"Could not update Discourse topic content {forum_topic.topic_id} "
                                 f"for block {forum_topic.block} "
                                 f"error: {e}")
                return False

    def create_topic(self,
                     discussion_block: Block,
                     course: Course,
                     forum_subcategory: ForumSubcategory,
                     topic_title: str = None) -> ForumTopic:
        """
        Create a topic in Discourse for a given Discussion block.

        Args:
            discussion_block:
            course:
            forum_subcategory:
            topic_title:            Override the title of the topic. If None, use the title from the block.

        Returns:
            ForumTopic instance
        """
        assert discussion_block is not None, "create_topic() discussion_block must be defined"
        assert course is not None, "create_topic() course must be defined"
        assert forum_subcategory is not None, "create_topic() forum_subcategory must be defined"
        assert discussion_block.type == BlockType.FORUM_TOPIC.name

        if topic_title is None:
            topic_title = discussion_block.discussion_topic_title

        if discussion_block.html_content:
            topic_content = discussion_block.html_content
        else:
            topic_content = f"Contribute below to the discussion topic : {topic_title}"

        # Weird API fact: when creating topics you use the /posts.json endpoint
        # and the create_post() method in pydiscourse. You leave topic_id blank
        # to indicate this is a 'topic' not a 'post.'
        response = self.client.create_post(category_id=forum_subcategory.subcategory_id,
                                           title=topic_title,
                                           content=topic_content)
        # Create local model if it doesn't already exist.
        topic_id = response['topic_id']
        topic_slug = response.get('topic_slug', None)
        logger.debug(f"Created topic {topic_id}:{topic_title} in "
                     f"Discourse for subcategory: {forum_subcategory}")
        forum_topic, created = ForumTopic.objects.get_or_create(block=discussion_block,
                                                                forum_subcategory=forum_subcategory)
        forum_topic.topic_id = topic_id
        forum_topic.topic_slug = topic_slug
        forum_topic.save()

        if created:
            logger.info(f"Created ForumTopic model for Discourse topic {topic_id}:{topic_title}")
        else:
            logger.info(f"Skipping ForumTopic model creation. Already exists.")

        return forum_topic

    def delete_topic(self, forum_topic: ForumTopic) -> bool:
        """
        Delete a topic in Discourse.

        Args:
            forum_topic:

        Returns:
            Boolean
        """
        assert forum_topic is not None, "delete_topic() forum_topic must be defined"

        topic_id = forum_topic.topic_id
        try:
            response = self.client.delete_topic(topic_id)
            logger.debug(f"Response from deleting remote topic {topic_id}: {response}")
        except Exception as e:
            logger.exception(f"Could not delete Discourse topic {topic_id} "
                             f"for block {forum_topic.block} "
                             f"error: {e}")
            return False

        forum_topic.delete()
        return True

    # ~~~~~~~~~~~~~~~~~~~
    # CALLBACKS
    # ~~~~~~~~~~~~~~~~~~~
    def read_forum_callback(self, request) -> Dict:
        """
        Reads an incoming 'callback' request from Discourse and
        decrypts and parses it. Returns the JSON body of the request.

        Note: when a user deletes a post, we get a POST event but the event
        doesn't say anything about the deletion. The only way to know it was a
        "delete" is looking in the header for X-Discourse-Event

            X-Discourse-Event: post_destroyed

        For more info see:

            https://meta.discourse.org/t/post-event-webhook-does-not-indicate-post-was-deleted/121356/4

        Args:
            request:    Callback request from Discourse

        Returns:
            Dictionary of data received by discourse callback

        JSON body of the request.

        """

        try:
            # get data passed in  headers...
            discourse_event_signature = request.headers.get('X-Discourse-Event-Signature')
            # We need these two props in case there's an error, and we need to log which event failed
            discourse_event_id = request.headers.get('X-Discourse-Event-Id')
            # TODO: watch for discourse_event_type values like 'post-destroyed' and
            # TODO: decide e.g. not to record an event
            discourse_event_type = request.headers.get('X-Discourse-Event-Type')
            logger.debug(f"discourse_event_type: {discourse_event_type}")
        except Exception:
            raise ForumServiceError("Could not load a required header. ")

        try:
            request_body = request.body
            secret_key = self.provider.forum_callback_secret.encode()

            # Remove 'sha256=' from incoming signature
            discourse_event_signature = discourse_event_signature[7:]

            # Hash body and see if it matches secret
            h = hmac.new(
                key=secret_key,
                msg=request_body,
                digestmod=hashlib.sha256
            )
            computed_signature = h.hexdigest()
        except Exception:
            error_message = f"Could not generate computed_signature"
            logger.error(f"Error processing discourse_event_id {discourse_event_id}: {error_message}")
            raise ForumServiceError(error_message)

        if computed_signature != discourse_event_signature:
            error_message = f"Computed signature does not match provided signature"
            logger.error(f"Error processing discourse_event_id {discourse_event_id}: {error_message}")
            raise ForumServiceError(error_message)

        # Callback credentials are ok. Let's get json and return it.
        try:
            if isinstance(request_body, bytes):
                request_body = request_body.decode(encoding='utf-8')
            json_data = json.loads(request_body)
        except Exception:
            error_message = f"Could not transform request_body into JSON"
            logger.error(f"Error processing discourse_event_id {discourse_event_id}: {error_message}")
            raise ForumServiceError(error_message)

        logger.info(f"Successfully parsed forum callback.")
        logger.debug(f"Data : {json_data}")
        return json_data

    def save_forum_callback(self, json_data: Dict):
        """
        Takes JSON callback data from Discourse and
        stores it in database.

        Args:
            json_data:  JSON payload from Discourse

        Returns:
            (Nothing)
        """

        post_data = json_data.get('post', {})
        topic_data = json_data.get('topic', {})
        if post_data is not None:
            activity_type = ForumActivityType.POST.name
            data = post_data
        elif topic_data is not None:
            activity_type = ForumActivityType.TOPIC.name
            data = topic_data
        else:
            error_message = "Cannot find 'post' or 'topic' object in message"
            raise ForumServiceError(error_message)

        # Read in event props we care about common to both post and topic
        logger.info(f"Discourse event data {data}")

        # Read in common data
        user_id = data.get('user_id', None)
        if not user_id:
            logger.info(f"Ignoring webhook call as it doesn't have user_id.")
            return
        username = data.get('username', None)
        if not username or username in ['kinesinlms', 'discobot', 'KinesinLMS}']:
            logger.info(f"Ignoring webhook call from username {username}")
            return

        created_at = data.get('created_at', None)
        # This is the category_id in Discourse...it doesn't tell us if this
        # is a category or subcategory. Locally, we store
        # categories and subcategories as part of our course:  course > cohort > topic structure.
        # So father down we'll actually use this category_id to look for a subcategory.
        category_id = data.get('category_id', None)
        if not category_id:
            logger.info(f"Ignoring webhook call. Category_id is None")
            return

        # Read in data based on location in different type.
        # - Unfortunately 'topic' callback only returns category_slug while
        # 'post' callback only returns category_id
        # - Discourse sends 'category_slug' regardless if topic or post
        # was in a subcategory or category. We'll assume its subcategory.

        post_type = None
        reply_to_post_number = None
        post_id = None
        if activity_type == ForumActivityType.TOPIC.name:
            logger.info("Handling Discourse TOPIC activity...")
            topic_id = data['id']
            topic_slug = data['slug']
            username = data['created_by']['username']
        elif activity_type == ForumActivityType.POST.name:
            logger.info("Handling Discourse POST activity...")
            post_id = data['id']
            topic_id = data['topic_id']
            topic_slug = data['topic_slug']
            username = data['username']
            post_type = data.get('post_type', None)
            reply_to_post_number = data.get('reply_to_post_number', None)
        else:
            error_message = "Unrecognized Discourse activity type"
            raise ForumServiceError(error_message)

        try:
            student = User.objects.get(username=username)
        except User.DoesNotExist:
            raise ForumServiceError(f"Discourse post event error. No user with username: {username}")

        try:
            forum_subcategory = ForumSubcategory.objects.get(subcategory_id=category_id)
        except ForumSubcategory.DoesNotExist:
            # Just make a note of this but don't error out.
            logger.exception(f"Could not find ForumSubcategory with subcategory_id: {category_id}")
            return

        subcategory_slug = getattr(forum_subcategory, 'subcategory_slug', None)

        course = forum_subcategory.forum_category.course
        course_unit_id = None
        course_unit_slug = None
        event_data = None
        try:
            logger.info(f"Tracking student interaction with Discourse Subcategory {forum_subcategory}")
            event_data = {
                'activity_type': activity_type,
                'created_at': created_at,
                'post_id': post_id,
                'topic_id': topic_id,
                'topic_slug': topic_slug,
                'category_id': category_id,
                'category_slug': subcategory_slug
            }
            if post_type:
                event_data['post_type'] = post_type
            if reply_to_post_number:
                # Important for analytics that we only store this field if exists.
                # Don't store a None value
                event_data['reply_to_post_number'] = reply_to_post_number

            try:
                forum_topic = ForumTopic.objects.get(topic_id=topic_id)
                block_uuid = forum_topic.block.uuid
            except Exception:
                logger.exception("Cannot determining discussion block uuid")
                block_uuid = None

            # Log event
            Tracker.track(event_type=TrackingEventType.FORUM_POST.value,
                          user=student,
                          event_data=event_data,
                          course=course,
                          unit_node_slug=None,
                          course_unit_id=course_unit_id,
                          course_unit_slug=course_unit_slug,
                          block_uuid=block_uuid)

        except Exception:
            logger.exception(f"Couldn't log Discourse post type: {TrackingEventType.FORUM_POST.value}"
                             f"event: {event_data}")
            # Fail silently in this case. We'll get a note via Sentry

    # ~~~~~~~~~~~~~~~~~~~
    # USERS
    # ~~~~~~~~~~~~~~~~~~~
    def add_user_to_group(self, group_id: int, username: str):
        """
        Add a student to a Discourse group.

        Args:
            group_id:
            username:

        Returns:
            ( nothing )
        """
        logger.info(f"add_user_to_group() Adding {username} to Discourse group_id {group_id}")
        try:
            self.client.add_group_member(groupid=group_id, username=username)
        except DiscourseClientError as dce:
            if "is already a member of this group" in str(dce):
                logger.info(f"Tried to add {username} to Discourse group_id {group_id} but user "
                            f"was already in that group.")
            else:
                logger.exception(f"Could not add {username} to Discourse group_id {group_id}.")
        except Exception:
            logger.exception(f"Could not add {username} to Discourse group_id {group_id}.")

    def remove_user_from_group(self, group_id: int, username: str):
        """
        Remove a student from a Discourse group.
        Args:
            group_id:
            username:

        """
        logger.info(f"remove_user_from_group() Removing {username} from Discourse group_id {group_id}")
        return self.client.delete_group_member(groupid=group_id, username=username)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # SSO METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def sso_validate(self, payload, signature, secret):
        """

        NOTE:
        Code below is adapted from the pydiscourse library.
        pydiscourse is licensed under MIT. More here: https://github.com/bennylope/pydiscourse/blob/master/LICENSE

        Args:
            payload: provided by Discourse HTTP call to your SSO endpoint as sso GET param
            signature: provided by Discourse HTTP call to your SSO endpoint as sig GET param
            secret: the secret key you entered into Discourse sso secret

        Returns:
            return value: The nonce used by discourse to validate the redirect URL

        """
        if None in [payload, signature]:
            raise ForumServiceError("No SSO payload or signature.")

        if not secret:
            raise ForumServiceError("Invalid secret..")

        payload = unquote(payload)
        if not payload:
            raise ForumServiceError("Invalid payload..")

        decoded = b64decode(payload.encode("utf-8")).decode("utf-8")
        if "nonce" not in decoded:
            raise ForumServiceError("Invalid payload..")

        h = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), digestmod=hashlib.sha256
        )
        this_signature = h.hexdigest()

        if this_signature != signature:
            raise ForumServiceError("Payload does not match signature.")

        # Discourse returns querystring encoded value. We only need `nonce`
        qs = parse_qs(decoded)
        return qs["nonce"][0]

    def sso_payload(self, secret, **kwargs):
        """

        NOTE:
        Code below is adapted from the pydiscourse library.
        pydiscourse is licensed under MIT. More here: https://github.com/bennylope/pydiscourse/blob/master/LICENSE

        """
        return_payload = b64encode(urlencode(kwargs).encode("utf-8"))
        h = hmac.new(secret.encode("utf-8"), return_payload, digestmod=hashlib.sha256)
        query_string = urlencode({"sso": return_payload, "sig": h.hexdigest()})
        return query_string

    def sso_redirect_url(self, nonce, secret, user, **kwargs):
        """

        NOTE:
        Code below is adapted from the pydiscourse library.
        pydiscourse is licensed under MIT. More here: https://github.com/bennylope/pydiscourse/blob/master/LICENSE


        Args:
            nonce: returned by sso_validate()
            secret: the secret key you entered into Discourse sso secret
            user: instance of the user who logged-in

        Returns:
            URL to redirect users back to discourse, now logged in as user_username
        """
        kwargs.update(
            {
                "nonce": nonce,
                "email": user.email,
                "external_id": user.id,
                "username": user.username,
                "name": user.informal_name
            }
        )

        return "/session/sso_login?%s" % self.sso_payload(secret, **kwargs)

    def sync_discourse_sso_user(self, user):
        """
        Make sure Discourse has an SSO user registered for the user.
        If one already is, the sync call will just update the student
        user passed as an arg, if email or informal_name has changed.

        Args:
            user

        Returns:
            ( nothing )
        """
        assert user is not None

        logger.info(f"Discourse Service: sync_discourse_sso_user(): calling sync_sso with user : {user}")

        try:
            site = Site.objects.get_current()
        except Site.DoesNotExist:
            logger.error("sync_discourse_sso_user() could not get current site")
            return None

        if not hasattr(site, "forum"):
            logger.error("sync_discourse_sso_user() current site has no forum")
            return None

        user_info = {
            "email": user.email,
            "external_id": user.id,
            "username": user.username,
            "sso_secret": self.provider.sso_secret
        }

        # DMcQ: Due to user privacy concerns, we decided not to share informal_name with Discourse.
        # try:
        #    user_info["name"] = user.informal_name,
        # except Exception as e:
        #    logger.warning(f"Could not set informal_name on Discourse SSO : {e}")

        try:
            response = self.client.sync_sso(**user_info)
        except Exception:
            error_message = "sync_discourse_sso_user() Could not sync_sso "
            logger.exception(error_message)
            raise ForumAPIUnsuccessful(error_message)

        logger.info(f"sync_discourse_sso_user() response from Discourse : {response}")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # COMPLETE
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def configure_forum_for_new_course(self, course: Course):
        """
        Performs all Discourse creates and updates when a new course is created in KinesinLMS,
         - in our local model instances that represent Discourse objects
         - in the actual remote Discourse service.

        This method should gracefully handle existing items on Discourse.

        NOTE: AT THE MOMENT (2023), all local cohorts use the same Discourse Cohort Group "DEFAULT."
        Cohorts are, for us, mostly about analytics and not about segmenting discussion.
        So although we allow multiple FormCohortGroups in one course, we don't tend to use
        more than one. We just dump all cohorts into one set of topics on Discourse.

        We may someday start segmenting cohorts into different subcategories in Discourse.
        The data model is set up to handle this, as many Cohorts can link to
        one CohortForumGroup, but code in some places will need to be refactored.

        Args:
            course:     An instance of the current Course to configure with Discourse

        Raises:
            Exception if any part of the setup fails.

        """
        assert course is not None, "configure_forum_for_new_course() : course argument cannot be None"
        logger.debug(f"Setting up Discourse for course {course}")

        # DISCOURSE COURSE GROUP
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # See if a course group has been created

        logger.info(f"Creating CourseForumGroup for course : {course}")
        try:
            course_forum_group, created = self.get_or_create_course_forum_group(course=course)
            logger.debug(f"CourseForumGroup set up: {course_forum_group}")
        except Exception as e:
            raise ForumServiceError(f"Could not create CourseForumGroup "
                                    f"for course: {course} Error: {e}")

        # DISCOURSE COHORT GROUP
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # IMPORTANT: We have to create a default CohortForumGroup *before* setting up categories.

        # Make sure the course has a DEFAULT cohort before we create a group in Discourse for
        # our CohortForumGroup.
        default_cohort = course.get_default_cohort()

        # Make sure we have a default cohort group in Discourse
        # for our CohortForumGroup cohort
        default_cohort_forum_group, created = self.get_or_create_cohort_forum_group(cohort=default_cohort)

        # By default, every cohort in the course will be using the same DEFAULT CohortForumGroup.
        # Assign every local cohort to use this DEFAULT cohort in Discourse.
        cohorts = Cohort.objects.filter(course=course).all()
        for cohort in cohorts:
            logger.info(f"Setting cohort {cohort.slug} to use "
                        f"the cohort_forum_group: {default_cohort_forum_group}")
            cohort.cohort_forum_group = default_cohort_forum_group
            cohort.save()

        # DISCOURSE CATEGORY FOR COURSE
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Create a category for the entire course in Discourse.
        # This will hold two subcategories, one for all enrolled and one
        # for the 'default' CohortForumGroup.
        # NOTE: This has to happen after creating the CohortForumGroup,
        # as we have to give that group permissions to this category.
        try:
            forum_category, created = self.get_or_create_forum_category(course=course)
            logger.debug(f"Created forum_category {forum_category}")
        except Exception as e:
            logger.exception(f"Could not create category and subcategory "
                             f"for course: {course} Error: {e}")
            logger.warning(f"Skipping creation of subcategories")
            return course

        # DISCOURSE ALL_ENROLLED SUBCATEGORY
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Create a subcategory for the course group in Discourse for ALL_ENROLLED students.
        try:
            forum_subcategory, created = self.get_or_create_forum_subcategory(
                forum_category=forum_category,
                subcategory_type=ForumSubcategoryType.ALL_ENROLLED.name,
                ensure_unique_name=True)
            logger.debug(f"Created forum_subcategory {forum_subcategory}")
        except Exception as e:
            logger.exception(f"Could not create course ALL_ENROLLED (sub)category "
                             f"for course: {course} Error: {e}")

        # DISCOURSE COHORT GROUP SUBCATEGORY AND TOPICS
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # We already created a CohortForumGroup to work for all
        # cohorts in our course. However, we still need to create a subcategory
        # for the group in Discourse and then add the topics for each discussion
        # in the course to that subcategory.
        cohort_forum_groups = CohortForumGroup.objects.filter(course=course).all()
        for cohort_forum_group in cohort_forum_groups:
            try:
                self.populate_cohort_forum_group_with_subcategory_and_topics(cohort_forum_group=cohort_forum_group)
            except Exception as e:
                logger.exception(f"Could not configure Discourse "
                                 f"for cohort: {default_cohort} "
                                 f"existing cohort_forum_group {cohort_forum_group} "
                                 f"Error: {e}")

    def populate_cohort_forum_group_with_subcategory_and_topics(self,
                                                                cohort_forum_group: CohortForumGroup):
        """
        Sets up the subcategory and topics in Discours for a given Discourse
        group (as represented by a CohortForumGroup instance).

        -   creates a Discourse (sub)category for the cohort
        -   creates topics for every discourse topic in the course and adds them
            to the subcategory

        Args:
            cohort_forum_group:     A CohortForumGroup representing a group
                                        on Discourse. The group should already exist
                                        on Discourse.

        Returns:
            (Nothing)
        """

        logger.info(f"Populating CohortForumGroup {cohort_forum_group} on Discourse"
                    f"with Subcategory and Topics for each discussion.")

        if cohort_forum_group.course is None:
            raise ValueError("CohortForumGroup's course property cannot be None.")

        course = cohort_forum_group.course

        # Create a Discourse Subcategory for the cohort group.
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # The create_subcategory call will also set permissions for the subcategory

        try:
            parent_category = ForumCategory.objects.get(course=cohort_forum_group.course)
            forum_subcategory, created = self.get_or_create_forum_subcategory(
                forum_category=parent_category,
                subcategory_type=ForumSubcategoryType.COHORT.name,
                cohort_forum_group=cohort_forum_group)
        except Exception as e:
            error = f"Could not create Discourse subcategory for CohortForumGroup {cohort_forum_group} " \
                    f"This also means the Discourse topics were not created."
            logger.exception(error)
            raise ForumServiceError(error) from e
        logger.debug(f"Created ForumSubcategory {forum_subcategory} for "
                     f"new CohortForumGroup {cohort_forum_group} "
                     f"in course {course}")

        # Create Discourse Topics
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Add a topic for each discussion in the course to the
        # subcategory we just created.

        try:
            forum_topics: List[ForumTopic] = self.create_topics_for_subcategory(
                course=course,
                forum_subcategory=forum_subcategory)
        except Exception as e:
            error = f"Could not create topics for Discourse subcategory {forum_subcategory}"
            logger.exception(error)
            raise ForumServiceError(error) from e

        # All done. Report success!
        topic_ids = [f"{topic.id}, " for topic in forum_topics]
        logger.debug(f"Created {len(forum_topics)} ForumTopics in {forum_subcategory} "
                     f"for new ForumCohortGroup {cohort_forum_group} "
                     f"in course {course}")
        logger.debug(f"Ids for forum_topics: {topic_ids}")
        logger.debug(f"Done configuring Discourse for ForumCohortGroup : {cohort_forum_group}")

    def delete_all_discourse_items_for_course(self, course: Course):
        """
        Delete all items in Discourse that correspond to a Course.
        This should also delete all the KinesinLMS models representing
        those items.

        Args:
            course:

        Returns:
            ( nothing )
        """
        # Delete items for FormCohortGroups subcategory
        cohort_forum_groups = CohortForumGroup.objects.filter(course=course).all()
        for cohort_forum_group in cohort_forum_groups:
            logger.debug(f"Deleting ForumCohortGroup {cohort_forum_group}")
            self.delete_forum_subcategory_for_cohort_forum_group(cohort_forum_group=cohort_forum_group)
            self.delete_cohort_forum_group(cohort_forum_group=cohort_forum_group,
                                           delete_default=True)

        # Delete items for ALL_ENROLLED subcategory
        logger.debug(f"Deleting Discourse (sub)category for course {course}")
        self.delete_forum_subcategory_for_course(course)
        logger.debug(f"Deleting Discourse group for course {course}")
        self.delete_course_forum_group(course)

        # Delete top category for course and top group for course.
        logger.debug(f"Deleting Discourse category for course {course}")
        self.delete_forum_category(course)

    # OTHER PRIVATE
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _get_discourse_groups_lookup(self) -> Dict[int, object]:
        """
        Returns a dictionary of JSON data about groups
        from Discourse, keyed by group id.

        Returns:
            Dictionary of category data, keyed by category_id.
        """
        dgroups = self.client.groups()
        dgroups_lookup = {}
        for dgroup in dgroups:
            dgroups_lookup[int(dgroup['id'])] = dgroup
        return dgroups_lookup
