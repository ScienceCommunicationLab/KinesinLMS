import dataclasses
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, OrderedDict, Tuple

from django.core.exceptions import ObjectDoesNotExist
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now

from kinesinlms.course.constants import NodeType

logger = logging.getLogger(__name__)


def can_access_course(user, course, enrollment=None) -> bool:
    """
    Determine whether user can access a particular course.
    We allow enrollment to be passed in here as the caller
    might have already pulled it from the database for
    other purposes...so no need to look it up again here.

    Args:

     user:
     course:
     enrollment:    Enrollment for this user in this course
                    (optional...if not provided we look for it
                    in this method.)

    Returns:


    """
    if user is None:
        raise ValueError("user cannot be None")
    if course is None:
        raise ValueError("course cannot be None")

    if user.is_superuser or user.is_staff:
        return True

    if enrollment:
        # Sanity check...
        if enrollment.course != course or enrollment.student != user:
            raise ValueError(f"Wrong enrollment for course {course} and user {user}")
    else:
        try:
            enrollment = course.enrollments.get(student=user, active=True)
        except ObjectDoesNotExist:
            # I've seen errors in the logs where user was not shown as enrolled,
            # but I can see an enrollment in the event stream, which leads me to
            # believe a transaction might still be underway when this request was made.
            # So let's wait a sec and then try again before giving up and saying
            # student isn't enrolled.
            logger.warning(f"User {user.username} wants to view course ID {course.id} and cannot "
                           f"because not enrolled. WAITING A SECOND AND TRYING AGAIN.")
            time.sleep(1)
            try:
                enrollment = course.enrollments.get(student=user, active=True)
            except ObjectDoesNotExist:
                logger.warning(f"User {user.username} wants to view course ID {course.id} and cannot "
                               f"because not enrolled")
                return False

    if not course.has_started:
        if enrollment.beta_tester:
            # User is enrolled and is a beta tester, so check if we're in the beta timeframe...
            today = datetime.now(tz=timezone.utc)
            course_start = course.start_date
            beta_start = course_start - timedelta(days=course.days_early_for_beta)
            return today > beta_start
        else:
            logger.info("User {} wants to view course ID {} and cannot "
                        "because course has not started: ".format(user.username, course.id))
            return False

    return True


def can_access_course_unit_in_course(course_unit,
                                     user,
                                     course_nav) -> bool:
    """
    Determine whether a student can view a course unit.
    This includes checking release times for the course and
    the course unit.
    """

    course = course_unit.course

    try:
        enrollment = course.enrollments.get(student=user, course=course)
    except ObjectDoesNotExist:
        logger.debug("can_access_course_unit_in_course() student is not enrolled in course.")
        return False

    # First check if the student can access this course....
    # and if the course unit is actually in the course passed
    # into this method.
    result = can_access_course(user=user, course=course)
    if not result:
        return False

    # Now start the process of looking at the cached version of the MPTT tree to
    # see if the course unit has been released

    current_time = now()
    # accommodate beta test if present
    if enrollment.beta_tester and course.days_early_for_beta and course.days_early_for_beta > 0:
        beta_offset = timedelta(days=course.days_early_for_beta)
        current_time += beta_offset

    # Now check whether student can access this CourseUnit.
    # Remember that release times are stored in the CourseNode
    # MPTT tree used for navigation.
    #
    # Therefore, use the cached MPTT tree to check course node release
    # times. We look for the first instance of a CourseNode
    # that refers to this CourseUnit, and use that CourseNode's
    # release date and dates of all its ancestors for the check.
    course_nodes = course_nav['children']
    node_lineage: List[OrderedDict] = get_course_node_lineage(course_unit=course_unit,
                                                              course_nodes=course_nodes)
    if not node_lineage:
        logger.warning(f"can_access_course_unit_in_course() couldn't find "
                       f"course_unit {course_unit} in course nav dictionary.")
        return False

    for node_dict in node_lineage:
        release_dt_utc = node_dict.get('release_datetime_utc', None)
        if release_dt_utc:
            date = parse_datetime(release_dt_utc)
            if date > current_time:
                return False
        else:
            continue

    return True


def get_course_node_lineage(course_unit,
                            course_nodes: List[OrderedDict]) -> List[OrderedDict]:
    """
    Finds the first CourseNode that contains the given CourseUnit
    in the cached version of the course nav.
    This is a recursive function that walks the nav dictionary.
    Returns a list of all ancestor nodes (each as a dictionary)

    If course_unit can't be found, returns empty list.

    Args:
        course_unit:        An instance of the CourseUnit we're looking for.
        course_nodes:       List of dictionaries

    Returns:
        A list of dictionaries representing the CourseNode and its ancestors.
        Otherwise, an empty list.
    """
    for current_node in course_nodes:
        node_type = current_node.get('type', None)
        if node_type == NodeType.UNIT.name:
            unit = current_node.get('unit', None)
            if unit:
                unit_id = unit.get('id', None)
                if unit_id and unit_id == course_unit.id:
                    return [current_node]
        elif current_node['children']:
            children_nodes = current_node['children']
            results = get_course_node_lineage(course_unit, children_nodes)
            if results:
                results.append(current_node)
                return results
        else:
            # Node is not a Unit node, but also does not have children,
            # so skip it.
            pass


class NodeNotReleased(Exception):
    def __init__(self, node):
        self.node = node
        super().__init__()


class ModuleNodeNotReleased(NodeNotReleased):
    pass


class SectionNodeNotReleased(NodeNotReleased):
    pass


class NodeDoesNotExist(Exception):
    pass


class ModuleNodeDoesNotExist(NodeDoesNotExist):
    pass


class SectionNodeDoesNotExist(NodeDoesNotExist):
    pass


class UnitNodeDoesNotExist(NodeDoesNotExist):
    pass


@dataclasses.dataclass
class UnitNavInfo:
    module_node_id: Optional[int] = None
    module_node_slug: Optional[str] = None
    module_node_display_name: Optional[str] = None
    module_content_index: Optional[int] = None
    module_released: bool = True
    module_release_datetime: Optional[datetime] = None

    section_node_id: Optional[int] = None
    section_node_slug: Optional[str] = None
    section_node_display_name: Optional[str] = None
    section_content_index: Optional[int] = None
    section_released: bool = True
    section_release_datetime: Optional[datetime] = None

    unit_node_id: Optional[int] = None
    unit_node_slug: Optional[str] = None
    unit_node_released: bool = False
    unit_node_release_datetime: Optional[datetime] = None
    unit_content_index: Optional[int] = None

    prev_unit_node_url: Optional[str] = None
    prev_unit_node_name: Optional[str] = None
    next_unit_node_url: Optional[str] = None
    next_unit_node_name: Optional[str] = None

    # Indicates whether one or more modules
    # or sections that are still unreleased.
    # (Not units, we don't worry about that
    # because we don't limit navigation based
    # on unit released status).
    unreleased_content: bool = False

    def full_content_index(self) -> str:
        if self.module_content_index is None:
            return ""
        try:
            return f"{self.module_content_index}.{self.section_content_index}.{self.unit_content_index}"
        except Exception as e:
            logger.exception(f"UnitNavInfo: Could not generate full_content_index: {e}")
        return ""


def get_node(nodes: List,
             slug: Optional[str]) -> Optional[OrderedDict]:
    """
    Get a navigation node, given a list of nodes and a slug.
    Attach 'parent' information to the node to make it easier to find
    next and prev nodes.

    IMPORTANT: As part of this process, update the is_released property on
    every node to a current value.


    Args:
        nodes:                      List of nodes to search
        slug:                       Search for node with this slug.

    Returns:
        Node if a match is found

    Raises:
        NodeDoesNotExist    if node not found
    """
    if not nodes:
        raise ValueError("nodes cannot be None")
    if not slug:
        # return the first node
        return nodes[0]
    for node in nodes:
        if node['slug'] == slug:
            return node
    else:
        raise NodeDoesNotExist()


def get_prev_released_node(course_nav: Dict,
                           current_node: OrderedDict,
                           ignore_release_date: bool = False) -> Optional[Dict]:
    """
    Find the previous node by iterating from the start and keeping
    hold of the last unit before we find the current unit.
    We don't look at Modules or Sections that are unreleased,
    but an unreleased Unit Node is fine to link to (since the UI
    will handle that with a 'content not released' type message).
    """
    previous_released_node: Optional[OrderedDict] = None
    module_nodes = course_nav.get('children', [])
    for module_node in module_nodes:
        if module_node['is_released'] or ignore_release_date:
            section_nodes = module_node.get('children', [])
            for section_node in section_nodes:
                if section_node['is_released'] or ignore_release_date:
                    unit_nodes = section_node.get('children', [])
                    for unit_node in unit_nodes:
                        if unit_node['id'] == current_node['id']:
                            return previous_released_node
                        else:
                            # Does not matter if node is released
                            # or not...both states are valid for previous node.
                            previous_released_node = unit_node
    return previous_released_node


def get_next_released_node(course_nav: Dict,
                           current_node: OrderedDict,
                           ignore_release_date: bool = False) -> Tuple[Optional[Dict], bool]:
    """
    Find the next node by iterating from the end and keeping
    hold of the last unit before we find the current unit.
    We don't look at Modules or Sections that are unreleased,
    but an unreleased Unit Node is fine to link to (since the UI
    will handle that with a 'content not released' type message).
    """
    next_released_node: Optional[OrderedDict] = None
    module_nodes = course_nav.get('children', [])
    unreleased_content = False
    for module_node in reversed(module_nodes):
        if module_node['is_released'] or ignore_release_date:
            section_nodes = module_node.get('children', [])
            for section_node in reversed(section_nodes):
                if section_node['is_released'] or ignore_release_date:
                    unit_nodes = section_node.get('children', [])
                    for unit_node in reversed(unit_nodes):
                        if unit_node['id'] == current_node['id']:
                            return next_released_node, unreleased_content
                        else:
                            # Does not matter if node is released
                            # or not...both states are valid for previous node.
                            # because we allow navigation to unreleased nodes
                            # (we just show a 'coming soon' type message)
                            next_released_node = unit_node
                else:
                    unreleased_content = True
        else:
            unreleased_content = True
    return next_released_node, unreleased_content


def get_unit_nav_info(course_nav: Dict,
                      module_node_slug: Optional[str] = None,
                      section_node_slug: Optional[str] = None,
                      unit_node_slug: Optional[str] = None,
                      self_paced: bool = True,
                      is_superuser: bool = False,
                      is_staff: bool = False) -> UnitNavInfo:
    """
    Determine the current unit and whether it is released.
    Also determine the previous and next unit url and name.

    This method assumes the is_released property on each node
    has been updates to accommodate any beta test
    'days early' information.

    Args:
        course_nav:             List of dictionaries derived from
                                MPTT course node structure.
        module_node_slug:       Look for module with this slug. If None
                                get first available module.
        section_node_slug:      Look for section with this slug. If None
                                get first available section in this module.
        unit_node_slug:         Look for unit with this slug. If None
                                get first available unit in this section.
        self_paced:             This is a self-paced course (affects whether we care about
                                computed updated release dates).
        is_superuser:
        is_staff:

    Returns:
        A dataclass with current unit id and release status,
        as well as prev and next links and names.

    Raises:
        ModuleNodeDoesNotExist exception if module does not exist.
        SectionNodeDoesNotExist exception if module does not exist.
        UnitNodeDoesNotExist exception if unit node does not exist
        ModuleNodeNotReleased exception if module is not yet released.
        SectionNodeNotReleased exception if section is not yet released.

    """

    if not course_nav:
        raise ValueError(f"get_unit_nav_info() course_nav was None")

    info: UnitNavInfo = UnitNavInfo()
    module_nodes = course_nav.get('children', [])

    try:
        module_node = get_node(nodes=module_nodes,
                               slug=module_node_slug)
        info.module_display_name = module_node.get('display_name', None)
        info.module_id = int(module_node['id'])
        info.module_slug = module_node_slug
        info.module_content_index = module_node.get('content_index', None)
        info.module_released = module_node.get('is_released', True)
        info.module_release_datetime = module_node.get('release_datetime', True)

    except NodeDoesNotExist:
        raise ModuleNodeDoesNotExist()
    except Exception as e:
        logger.exception(f"Could not get node: {e}")
        raise Exception from e

    try:
        section_nodes = module_node.get('children', [])
        section_node = get_node(nodes=section_nodes,
                                slug=section_node_slug)
        info.section_slug = section_node_slug
        info.section_display_name = section_node.get('display_name', None)
        info.section_id = int(section_node['id'])
        info.section_content_index = section_node.get('content_index', None)
        info.section_released = section_node.get('is_released', True)
        info.section_release_datetime = section_node.get('release_datetime', True)
    except NodeDoesNotExist:
        raise SectionNodeDoesNotExist()
    except Exception as e:
        logger.exception(f"Could not get node: {e}")
        raise Exception from e

    unit_nodes = section_node.get('children', [])
    try:
        unit_node = get_node(nodes=unit_nodes,
                             slug=unit_node_slug)
        # We don't raise an exception if UnitNode is not yet released.
        # We're going to show same unit page but with 'not released' message.
        info.unit_node_released = unit_node.get('is_released', True)
        info.unit_node_id = int(unit_node['id'])
        info.unit_node_slug = unit_node['slug']
        info.unit_content_index = unit_node.get('content_index', None)
        info.unit_node_released = unit_node.get('is_released', True)
        info.unit_node_release_datetime = unit_node.get('release_datetime', None)
    except NodeDoesNotExist:
        raise UnitNodeDoesNotExist()
    except Exception as e:
        logger.exception(f"Could not get node: {e}")
        raise Exception from e

    prev_node = get_prev_released_node(course_nav=course_nav,
                                       current_node=unit_node,
                                       ignore_release_date=is_staff or is_superuser)
    if prev_node:
        info.prev_unit_node_name = prev_node.get('display_name', None)
        info.prev_unit_node_url = prev_node.get('node_url', None)
    else:
        info.prev_unit_node_name = None
        info.prev_unit_node_url = None

    # We capture a boolean indicating whether there is unreleased content
    # in the future, since we might use that flag to change up what kind of
    # text we show in the UI navigation controls.
    next_node, unreleased_content = get_next_released_node(course_nav=course_nav,
                                                           current_node=unit_node,
                                                           ignore_release_date=is_staff or is_superuser)

    if next_node:
        info.next_unit_node_name = next_node.get('display_name', None)
        info.next_unit_node_url = next_node.get('node_url', None)
    else:
        info.next_unit_node_name = None
        info.next_unit_node_url = None

    info.unreleased_content = unreleased_content

    return info
