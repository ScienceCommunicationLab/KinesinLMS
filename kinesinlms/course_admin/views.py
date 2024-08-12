from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import FormView

from django.utils.translation import gettext as _

from django.http import Http404

from kinesinlms.assessments.utils import (
    delete_submitted_answers,
    rescore_submitted_answers,
)
from kinesinlms.core.decorators import course_staff_required
from kinesinlms.core.mixins import EducatorCourseStaffMixin
from kinesinlms.course_admin.forms import SelectSubmittedAnswersForm
from kinesinlms.course.models import Course
from kinesinlms.educator_resources.utils import get_course_module_resources
from kinesinlms.course.models import CourseResource


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW CLASSES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class DeleteSubmittedAnswersView(EducatorCourseStaffMixin, FormView):
    form_class = SelectSubmittedAnswersForm
    template_name = "course_admin/assessments/delete_submitted_answers.html"
    hx_template_name = "course_admin/assessments/delete_submitted_answers_hx.html"
    page_title = "Delete Submitted Answers"

    def get_course(self):
        """
        Return the current course.

        Raises 404 if not found.
        """
        course_slug = self.kwargs["course_slug"]
        course_run = self.kwargs["course_run"]
        return get_object_or_404(Course, run=course_run, slug=course_slug)

    def get_form_kwargs(self):
        """
        Pass current course to the form.
        """
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "course": self.get_course(),
            }
        )
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Return context data used in all views.
        """
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "current_course_tab": "course_admin",
                "course": self.get_course(),
                "course_admin_page_title": self.page_title,
            }
        )
        return context

    def form_invalid(self, form):
        """
        Render the hx_template to show errors on an invalid form submission.

        Returns:
            hx snippet showing form errors
        """
        context = self.get_context_data()
        return render(self.request, self.hx_template_name, context)

    def form_valid(self, form):
        """
        Runs delete_submitted_answers on the valid form data.

        Returns:
            hx snippet showing form success.
        """
        context = self.get_context_data()
        course = context["course"]

        student = form.cleaned_data.get("student")
        assessment = form.cleaned_data.get("assessment")

        count_deleted = delete_submitted_answers(
            course=course, student=student, assessment=assessment
        )

        context = self.get_context_data()
        additional_context = {
            "student": student,
            "assessment": assessment,
            "count_deleted": count_deleted,
            "success": True,
        }
        context.update(additional_context)

        return render(self.request, self.hx_template_name, context)


class RescoreSubmittedAnswersView(DeleteSubmittedAnswersView):
    template_name = "course_admin/assessments/rescore_submitted_answers.html"
    hx_template_name = "course_admin/assessments/rescore_submitted_answers_hx.html"
    page_title = "Re-score Assessments"

    def form_valid(self, form):
        """
        Runs delete_submitted_answers on the valid form data.

        Returns:
            hx snippet showing form success.
        """
        context = self.get_context_data()
        course = context["course"]

        student = form.cleaned_data.get("student")
        assessment = form.cleaned_data.get("assessment")
        count_rescored = rescore_submitted_answers(
            course=course, student=student, assessment=assessment
        )

        context = self.get_context_data()
        additional_context = {
            "current_course_tab": "course_admin",
            "student": student,
            "assessment": assessment,
            "count_rescored": count_rescored,
            "success": True,
        }
        context.update(additional_context)

        return render(self.request, self.hx_template_name, context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@course_staff_required
def index(request, course_run: str, course_slug: str):
    """
    Main view for Course Admin section in course.
    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    # We don't have anything for the index page just yet,
    # so just redirect to course analytics
    reverse_url = reverse(
        "course:course_admin:course_analytics:index",
        kwargs={"course_run": course.run, "course_slug": course.slug},
    )
    return redirect(reverse_url)


@course_staff_required
def assessments_index(request, course_run: str, course_slug: str):
    """
    Main view for Course Admin Assessments section.
    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    template = "course_admin/assessments/index.html"

    context = {
        "course": course,
        "current_course_tab": "course_admin",
        "course_admin_page_title": "Course Assessments",
        "current_course_admin_tab": "course_assessments",
    }

    return render(request, template, context)


@course_staff_required
def resources_index(request, course_run: str, course_slug: str):
    """
    Main view for Course Admin Resources section.
    """

    course = get_object_or_404(Course, run=course_run, slug=course_slug)

    template = "course_admin/resources/index.html"

    course_module_resources = get_course_module_resources(course)

    context = {
        "course": course,
        "current_course_tab": "course_admin",
        "course_admin_page_title": "Resources",
        "current_course_admin_tab": "resources",
        "course_module_resources": course_module_resources,
    }

    return render(request, template, context)


@course_staff_required
def resource_detail(request, course_run: str, course_slug: str, pk: int):
    """
    Provides a detailed view of a course "resource".

    This view should focus on making all the metadata about the resource available
    to the course admin, in a form that's immediately useful to them in other contexts.

    Args:
        request
        course_run
        course_slug
        pk

    """
    course = get_object_or_404(
        Course,
        run=course_run,
        slug=course_slug,
    )
    try:
        course_resource = course.course_resources.get(id=pk)
    except CourseResource.DoesNotExist:
        raise Http404(_("Course resource does not exist."))

    template = "course_admin/resources/resource_detail.html"

    course_module_resources = get_course_module_resources(course)

    context = {
        "course": course,
        "course_resource": course_resource,
        "current_course_tab": "course_admin",
        "course_admin_page_title": "Resources",
        "current_course_admin_tab": "resources",
        "course_module_resources": course_module_resources,
    }

    return render(request, template, context)
