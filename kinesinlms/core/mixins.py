from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import UserPassesTestMixin
from kinesinlms.course.models import Course

from django.http import HttpRequest


class EducatorCourseStaffMixin(UserPassesTestMixin):
    """
    Mixin to require a user to be an educator **and** course staff for the given course.
    Expects the request to have 'course_slug' and 'course_run' in the URL kwargs.
    If the user is a staff or super they don't need to be an educator or registered course staff.
    """

    request: HttpRequest
    kwargs: dict

    def test_func(self):
        # Check if user is authenticated and an educator
        if not self.request.user.is_authenticated:
            return False

        if self.request.user.is_staff or self.request.user.is_superuser:
            return True

        # You must be an educator...
        if not self.request.user.is_educator:  # noqa
            return False

        # Even if you're an educator, need to have permission to view for this particular course.
        course_slug = self.kwargs.get("course_slug")
        course_run = self.kwargs.get("course_run")

        if course_slug and course_run:
            # Check if the user is in the CourseStaff model for this course
            try:
                course = Course.objects.get(run=course_run, slug=course_slug)
                return course.can_view_course_admin(self.request.user)
            except Exception:
                pass

        return False

    def handle_no_permission(self):
        return HttpResponseForbidden("Course staff access required")
