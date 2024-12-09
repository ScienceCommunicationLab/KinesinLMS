import logging
from typing import Dict, Optional, Tuple

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render

from kinesinlms.course.models import Course, Enrollment
from kinesinlms.course.nav import CourseNavException, get_course_nav
from kinesinlms.course.utils_access import (
    ModuleNodeDoesNotExist,
    ModuleNodeNotReleased,
    SectionNodeDoesNotExist,
    SectionNodeNotReleased,
    UnitNavInfo,
    UnitNodeDoesNotExist,
    can_access_course,
    get_unit_nav_info,
)

logger = logging.getLogger(__name__)


def access_denied_hx(
    request,
    course_slug: str = None,
    course_run: str = None,
    message: str = None,
) -> HttpResponse:
    """
    Show access denied message for an HTMx request.
    The assumption is just a small portion of the screen will be updated
    so the message might be styled slightly different.
    """
    display_name = None
    about_page_url = None
    if course_slug and course_run:
        try:
            course = Course.objects.get(slug=course_slug, run=course_run)
            display_name = course.display_name
            about_page_url = course.catalog_description.about_page_url
        except Course.DoesNotExist:
            pass

    context = {
        "display_name": display_name,
        "about_page_url": about_page_url,
        "denied_message": message,
    }
    return render(request, "course/hx/access_denied_hx.html", context, status=403)


def access_denied_page(
    request,
    course_slug: str = None,
    course_run: str = None,
    message: str = None,
) -> HttpResponse:
    """
    Show access denied message for a full page request.
    """
    display_name = None
    about_page_url = None
    if course_slug and course_run:
        try:
            course = Course.objects.get(slug=course_slug, run=course_run)
            display_name = course.display_name
            about_page_url = course.catalog_description.about_page_url
        except Course.DoesNotExist:
            pass

    context = {
        "display_name": display_name,
        "about_page_url": about_page_url,
        "denied_message": message,
    }
    return render(request, "course/access_denied.html", context, status=403)


def process_course_hx_request(
    request,
    course_slug=None,
    course_run=None,
    module_slug=None,
    section_slug=None,
    unit_slug=None,
) -> Tuple[Course, Enrollment, Dict, Optional[UnitNavInfo]]:
    """
    Do the basic checks and such for the typical HTMx request within a course.

    If module, section and unit are provided, this method will check student has access
    to that particular unit. It will return the unit nav info for that unit if it exists
    and the student has access to it.

    Otherwise, it just checks whether student has access to the course.

    Args:
        request:
        course_slug:
        course_run:
        module_slug:
        section_slug:
        unit_slug:

    Returns:
        Tuple[Course, Enrollment, Dict, UnitNavInfo]:  A tuple with the Course instance, Enrollment instance, a course nav dictionary
        and a UnitNavInfo instance. Note that UnitNavInfo is None if module, section and unit are not provided.



    """
    if course_slug is None:
        raise ValueError("course_slug cannot be None")
    if course_run is None:
        raise ValueError("course_run cannot be None")

    course: Course = Course.objects.get(slug=course_slug, run=course_run)
    enrollment: Enrollment = Enrollment.objects.get(student=request.user, course=course, active=True)
    if not can_access_course(request.user, course, enrollment=enrollment):
        raise PermissionDenied("You do not have access to this course.")
    if enrollment.enrollment_survey_required_url:
        raise PermissionDenied("User has not completed enrollment survey yet.")

    is_beta_tester = enrollment.beta_tester

    # Get dictionary for nav
    try:
        course_nav: Dict = get_course_nav(course, is_beta_tester=is_beta_tester)
    except CourseNavException:
        logger.exception(
            f"unit_page():  Could not generate course {course} navigation with " f"call to get_course_nav()"
        )
        raise Exception("Internal error. Please contact support for help.")

    if module_slug is None and section_slug is None and unit_slug is None:
        # We're just checking whether student has access to the course,
        # so nothing else to do here. No unit nav info to return.
        return course, enrollment, course_nav, None

    # Otherwise, get unit nav info to check things like if the unit is released.
    try:
        unit_nav_info: UnitNavInfo = get_unit_nav_info(
            course_nav,
            module_node_slug=module_slug,
            section_node_slug=section_slug,
            unit_node_slug=unit_slug,
            self_paced=course.self_paced,
        )
    except ModuleNodeDoesNotExist:
        raise Exception("Module does not exist")
    except SectionNodeDoesNotExist:
        raise Exception("Section does not exist")
    except UnitNodeDoesNotExist:
        raise Exception("Unit does not exist")
    except ModuleNodeNotReleased as mnr:
        raise Exception(f"Module is not yet released. Release date: {mnr.node['release_datetime']}")
    except SectionNodeNotReleased as snr:
        raise Exception(f"Section is not yet released. Release date: {snr.node['release_datetime']}")
    except Exception:
        logger.exception("Could not build nav info")
        raise Exception("No unit found.")

    return course, enrollment, course_nav, unit_nav_info
