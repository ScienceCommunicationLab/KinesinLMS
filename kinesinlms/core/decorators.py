from functools import wraps

from django.http import HttpResponseForbidden
from kinesinlms.course.models import Course

from kinesinlms.users.models import GroupTypes
import logging

logger = logging.getLogger(__name__)


def composer_author_required(view_func):
    """
    Decorator to require a user to be an AUTHOR in the composer.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # assume false and set to true otherwise.
        allow = False
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                allow = True
            elif request.user.groups.filter(name=GroupTypes.AUTHOR.name).exists():
                allow = True

        if allow:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("Author access required")

    return _wrapped_view


def educator_required(view_func):
    """
    Decorator to require a user's is_educator field to be True before executing a view method.
    (or a user is staff or a superuser)
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # assume false and set to true otherwise.
        if request.user.is_authenticated and (
            request.user.is_educator
            or request.user.is_staff
            or request.user.is_superuser
        ):
            allow = True
        else:
            allow = False

        if allow:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("Educator access required")

    return _wrapped_view


def course_staff_required(view_func):
    """
    Decorator to require a user to be course staff for the given course.
    This decorator expects the request to have a course_slug and course_run in the URL kwargs.
    If the user is a staff or super they don't need to be an educator or registered course staff.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # assume false and set to true otherwise.
        allow = False
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                allow = True
            else:
                # You need to be an educator...
                if request.user.is_educator:
                    # Even if you're an educator, need to have permission to view for this particular course.
                    course_slug = kwargs.get("course_slug", None)
                    course_run = kwargs.get("course_run", None)
                    if course_slug and course_run:
                        # Check if the user is in the CourseStaff model for this course
                        try:
                            course = Course.objects.get(
                                run=course_run, slug=course_slug
                            )
                            allow = course.can_view_course_admin(request.user)
                        except Exception as e:
                            logger.exception(
                                f"course_staff_required() decorator error: {e}"
                            )
                            pass

        if allow:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("Course staff access required")

    return _wrapped_view
