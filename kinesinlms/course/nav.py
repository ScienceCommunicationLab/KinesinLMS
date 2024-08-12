from datetime import timedelta
from typing import Dict, Tuple

from django.shortcuts import resolve_url
from django.utils.timezone import now

from django.conf import settings
from django.core.cache import cache
import logging

from kinesinlms.course.models import Course, CourseNode
from kinesinlms.course.serializers import CourseNodeSimpleSerializer
from kinesinlms.course.utils import update_node_time


logger = logging.getLogger(__name__)


class CourseNavException(Exception):
    pass


def get_course_nav(course: Course, is_beta_tester: bool = False) -> Dict:
    """
    Return a dictionary representing course nav
    (ostensibly to be sent to a template). This method's main
    purpose is to provide a mechanism for caching the nav.

    This method also updates the is_released information for
    timed courses, taking into account whether the user is a beta
    tester and how many days early the course is meant to be released
    to beta-testers.

    Args:
        course:
        is_beta_tester:

    Returns:
        Dict representing course navigation
    """
    try:
        course_nav_cache_name = f"{course.token}_nav"
        course_nav = None
        # Don't get if CACHES isn't set.
        # (Having to make this explicit for tests.)
        if settings.CACHES:
            course_nav = cache.get(course_nav_cache_name)
        if not course_nav:
            course_nav = CourseNodeSimpleSerializer(course.course_root_node).data
            # Cache for one day. We'll bust the cache if the nav is updated by an admin...
            if settings.TEST_RUN:
                time_to_cache = 0
            else:
                time_to_cache = 86400
            cache.set(course_nav_cache_name, course_nav, time_to_cache)
    except Exception:
        logger.exception("Could not generate course nav")
        raise CourseNavException()

    # Update is_released if necessary
    if is_beta_tester and course.days_early_for_beta > 0:
        current_time = now() + timedelta(days=course.days_early_for_beta)
    else:
        current_time = now()

    # Add links to 'parent' on each section and unit node
    # Update 'is_released' using latest time and beta test info, if any.
    for module_node in course_nav.get("children"):
        module_release_datetime = module_node.get("release_datetime", None)
        if not course.self_paced and module_release_datetime:
            update_node_time(module_node, current_time)
        for section_node in module_node.get("children", []):
            section_release_datetime = section_node.get("release_datetime", None)
            section_node["parent"] = module_node
            if not course.self_paced and section_release_datetime:
                update_node_time(section_node, current_time)
            for unit_node in section_node.get("children", []):
                unit_release_datetime = unit_node.get("release_datetime", None)
                unit_node["parent"] = section_node
                if not course.self_paced and unit_release_datetime:
                    update_node_time(unit_node, current_time)

    return course_nav


def get_previous_unit_url(unit_node: CourseNode) -> Tuple[str, str]:
    """
    Return the URL and display name of the previous node.

    Args:
        unit_node: CourseNode

    Returns:
        Tuple[str, str]: URL and display name of the previous node
    """

    assert unit_node is not None

    prev_unit = unit_node.get_previous_sibling()
    if prev_unit is None:
        section = unit_node.parent
        prev_section = section.get_previous_sibling()
        if prev_section is None:
            module = section.parent
            prev_module = module.get_previous_sibling()
            if prev_module is None:
                return "#", ""
            prev_section = prev_module.get_children().last()
        prev_unit = prev_section.get_children().last()

    prev_unit_node_url = prev_unit.node_url
    prev_unit_node_display_name = prev_unit.unit.display_name

    return prev_unit_node_url, prev_unit_node_display_name


def get_next_unit_node_url(unit_node: CourseNode) -> Tuple[str, str]:
    """
    Return the URL and display name of the next node.

    Args:
        unit_node: CourseNode

    Returns:
        Tuple[str, str]: URL and display name of the next node
    """
    assert unit_node is not None

    next_unit = unit_node.get_next_sibling()
    if next_unit is None:
        section = unit_node.parent
        next_section = section.get_next_sibling()
        if next_section is None:
            module = section.parent
            next_module = module.get_next_sibling()
            if next_module is None:
                return "#", ""
            next_section = next_module.get_children().first()
            if next_section is None:
                return "#", ""
        next_unit = next_section.get_children().first()

    next_unit_node_url = next_unit.node_url
    next_unit_node_display_name = next_unit.unit.display_name

    return next_unit_node_url, next_unit_node_display_name


def get_first_course_page_url(course: Course):
    assert course is not None
    url = resolve_url(
        "course:course_page", course_slug=course.slug, course_run=course.run
    )
    return url


def get_course_progress_url(course: Course):
    assert course is not None

    url = resolve_url(
        "course:progress_page", course_slug=course.slug, course_run=course.run
    )

    return url
