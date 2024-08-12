from dataclasses import dataclass
from typing import Dict, Optional
import logging


from django.shortcuts import get_object_or_404


from django.core.exceptions import PermissionDenied
from django.core.exceptions import ObjectDoesNotExist
from kinesinlms.course.models import Course, Enrollment

from kinesinlms.users.models import User
from kinesinlms.course.utils_access import can_access_course, UnitNavInfo
from kinesinlms.course.nav import CourseNavException, get_course_nav
from kinesinlms.course.utils_access import (
    get_unit_nav_info,
    ModuleNodeDoesNotExist,
    SectionNodeDoesNotExist,
    UnitNodeDoesNotExist,
)

logger = logging.getLogger(__name__)


class AccessDenied(PermissionDenied):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    pass


class CourseAccessDenied(AccessDenied):
    pass


class ModuleAccessDenied(AccessDenied):
    pass


class SectionAccessDenied(AccessDenied):
    pass


class UnitAccessDenied(AccessDenied):
    pass


class BlockResourceAccessDenied(AccessDenied):
    pass


@dataclass
class AccessInfo:
    """
    Describes the nature of access to course content.
    """

    course: Course = None
    block_id: str = None
    is_beta_tester: bool = False
    show_admin_controls: bool = False
    enrollment_survey_required: bool = False
    course_nav: Optional[dict] = None
    unit_nav_info: Optional[UnitNavInfo] = None
    # Is something is available to admin/staff but not
    # regular students, show message alerting staff to state.
    admin_message: str = None


class AccessService:
    """
    Simple service class to manage access to something in a course.

    If access is allowed, a simple AccessInfo dataclass is returned
    to describe the nature of the access, as well as provide populated
    instances of the course nav and unit nav info (which were needed
    as part of the access logic, but should not be constructed again).
    """

    def get_access_info(
        self,
        user: User,
        course_slug: str,
        course_run: str,
        module_slug: Optional[str] = None,
        section_slug: Optional[str] = None,
        unit_slug: Optional[str] = None,
        block_id: Optional[str] = None,
    ) -> AccessInfo:
        """
        Check if a user can access course content.
        If access is allowed, build up a simple AccessInfo dataclass to describe
        the nature of the access.

        Returns:
            AccessInfo: A dataclass describing the nature of the access.

        Raises:
            CourseAccessDenied: If the user does not have access to the course.
            ModuleAccessDenied: If the user does not have access to the module.
            SectionAccessDenied: If the user does not have access to the section.
            UnitAccessDenied: If the user does not have access to the unit.
            ObjectDoesNotExist: If the course, module, section, unit or block does not exist.
        """

        if course_slug is None:
            raise ValueError("course_slug cannot be None")
        if course_run is None:
            raise ValueError("course_run cannot be None")
        if module_slug is None:
            raise ValueError("module_slug cannot be None")
        if section_slug is None:
            raise ValueError("section_slug cannot be None")
        if unit_slug is None:
            raise ValueError("unit_slug cannot be None")
        if block_id is None:
            raise ValueError("unit_slug cannot be None")

        course = get_object_or_404(Course, slug=course_slug, run=course_run)
        access_info = AccessInfo(course=course, block_id=block_id)
        if user.is_superuser or user.is_staff:
            # A superuser or staff can view a course block without being enrolled
            access_info.is_beta_tester = False
        else:
            enrollment = get_object_or_404(
                Enrollment, student=user, course=course, active=True
            )
            if not can_access_course(user, course, enrollment=enrollment):
                raise CourseAccessDenied("You do not have access to this course")
            access_info.enrollment_survey_required = (
                enrollment.enrollment_survey_required
            )
            access_info.is_beta_tester = enrollment.beta_tester

        # Generate a course nav as part of the process for
        # determining granular access
        try:
            course_nav: Dict = get_course_nav(
                course, is_beta_tester=access_info.is_beta_tester
            )
        except CourseNavException as cne:
            logger.exception(
                f"unit_page():  Could not generate course {course} navigation with "
                f"call to get_course_nav()"
            )
            raise Exception("Internal error. Please contact support for help.") from cne

        # Create unit nav info and determine granular access
        try:
            unit_nav_info: UnitNavInfo = get_unit_nav_info(
                course_nav,
                module_node_slug=module_slug,
                section_node_slug=section_slug,
                unit_node_slug=unit_slug,
                self_paced=course.self_paced,
                is_staff=user.is_staff,
                is_superuser=user.is_superuser,
            )
        except ModuleNodeDoesNotExist:
            raise ObjectDoesNotExist("Module does not exist")
        except SectionNodeDoesNotExist:
            raise ObjectDoesNotExist("Section does not exist")
        except UnitNodeDoesNotExist:
            raise ObjectDoesNotExist("Unit does not exist")
        except Exception as e:
            logger.exception("Could not build nav info")
            raise e

        if not unit_nav_info.unit_node_released:
            if user.is_superuser or user.is_staff:
                access_info.admin_message = (
                    "The unit for this block is not yet available "
                    "to students (Unit not released)."
                )
            else:
                raise UnitAccessDenied(
                    f"Unit is not yet released. "
                    f"Release date: {unit_nav_info.module_release_datetime}"
                )
        if not unit_nav_info.section_released:
            if user.is_superuser or user.is_staff:
                access_info.admin_message = (
                    "The unit for this block is not yet available "
                    "to students (Section not released)."
                )
            else:
                raise SectionAccessDenied(
                    f"Section is not yet released. "
                    f"Release date: {unit_nav_info.module_release_datetime}"
                )
        if not unit_nav_info.module_released:
            if user.is_superuser or user.is_staff:
                access_info.admin_message = (
                    "The unit for this block is not yet available "
                    "to students (Module not released)."
                )
            else:
                raise ModuleAccessDenied(
                    f"Module is not yet released. "
                    f"Release date: {unit_nav_info.module_release_datetime}"
                )

        return access_info
