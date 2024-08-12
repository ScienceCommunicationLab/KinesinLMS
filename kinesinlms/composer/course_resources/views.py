import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import UpdateView, CreateView

from kinesinlms.composer.course_resources.forms import (
    CourseResourceForm,
    EducatorCourseResourceForm,
)
from django.views.generic import TemplateView

from kinesinlms.composer.view_helpers import get_course_edit_tabs
from kinesinlms.course.models import Course, CourseResource
from kinesinlms.users.mixins import ComposerAuthorRequiredMixin
from kinesinlms.educator_resources.models import EducatorResource

logger = logging.getLogger(__name__)


class ResourcesListView(ComposerAuthorRequiredMixin, TemplateView):
    """
    Provides a list of course resources and educator resources for a course.
    """

    template_name = "composer/course_resources/resources_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)

        section_tabs = get_course_edit_tabs(
            current_course=course, 
            active_section="resources"
        )
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": None,
            "section": "course_resources",
            "section_tabs": section_tabs,
        }
        context.update(extra_context)

        return context


class CourseResourceCreateView(ComposerAuthorRequiredMixin, CreateView):
    model = CourseResource
    template_name = "composer/course_resources/course_resource_create.html"
    context_object_name = "course_resource"
    form_class = CourseResourceForm

    def get_initial(self):
        initial = super().get_initial()
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        initial["course"] = course
        return initial

    def get_success_url(self):
        success_url = reverse_lazy(
            "composer:resources_list",
            kwargs={"course_id": self.kwargs["course_id"]},
        )
        return success_url

    def form_valid(self, form):
        instance = form.save(commit=False)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        instance.course = course
        instance.save()
        messages.success(self.request, "Course resource created successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="resources"
        )
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": [
                {
                    "label": "Resources",
                    "url": reverse(
                        "composer:resources_list",
                        kwargs={"course_id": course.id},
                    ),
                }
            ],
            "section": "course_resources",
            "section_title": "Create Course Resources",
            "section_description": None,
            "section_tabs": section_tabs,
        }
        context.update(extra_context)
        return context


class CourseResourceUpdateView(ComposerAuthorRequiredMixin, UpdateView):
    model = CourseResource
    template_name = "composer/course_resources/course_resource_update.html"
    context_object_name = "course_resource"
    form_class = CourseResourceForm

    def get_object(self, queryset=...):
        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)
        course_resource_id = self.kwargs["pk"]
        course_resource = get_object_or_404(
            CourseResource, id=course_resource_id, course=course
        )
        return course_resource

    def get_success_url(self):
        success_url = reverse_lazy(
            "composer:course_resource_update",
            kwargs={"course_id": self.kwargs["course_id"], "pk": self.kwargs["pk"]},
        )
        return success_url

    def form_valid(self, form):
        messages.success(self.request, "Course resource updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="resources"
        )
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": [
                {
                    "label": "Resources",
                    "url": reverse(
                        "composer:resources_list",
                        kwargs={"course_id": course.id},
                    ),
                }
            ],
            "section_title": "Edit Course Resource",
            "section_description": f"Edit course resource '{self.object.name}'",
            "section_tabs": section_tabs,
        }
        context.update(extra_context)
        return context


class EducatorCourseResourceCreateView(ComposerAuthorRequiredMixin, CreateView):
    model = CourseResource
    template_name = "composer/course_resources/educator_course_resource_create.html"
    context_object_name = "educator_course_resource"
    form_class = EducatorCourseResourceForm

    def get_initial(self):
        initial = super().get_initial()
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        initial["course"] = course
        return initial

    def get_success_url(self):
        success_url = reverse_lazy(
            "composer:resources_list",
            kwargs={"course_id": self.kwargs["course_id"]},
        )
        return success_url

    def form_valid(self, form):
        instance = form.save(commit=False)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        instance.course = course
        instance.save()
        messages.success(self.request, "Course resource created successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="resources"
        )
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": [
                {
                    "label": "Resources",
                    "url": reverse(
                        "composer:resources_list",
                        kwargs={"course_id": course.id},
                    ),
                }
            ],
            "section_title": "Create Educator Course Resources",
            "description": None,
            "section_tabs": section_tabs,
        }
        context.update(extra_context)
        return context


class EducatorCourseResourceUpdateView(ComposerAuthorRequiredMixin, UpdateView):
    model = CourseResource
    template_name = "composer/course_resources/educator_course_resource_update.html"
    context_object_name = "educator_course_resource"
    form_class = EducatorCourseResourceForm

    def get_object(self, queryset=...):
        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)
        course_resource_id = self.kwargs["pk"]
        course_resource = get_object_or_404(
            EducatorResource,
            id=course_resource_id,
            course=course,
        )
        return course_resource

    def get_success_url(self):
        success_url = reverse_lazy(
            "composer:educator_course_resource_update",
            kwargs={"course_id": self.kwargs["course_id"], "pk": self.kwargs["pk"]},
        )
        return success_url

    def form_valid(self, form):
        messages.success(self.request, "Educator course resource updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="resources"
        )
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": [
                {
                    "label": "Resources",
                    "url": reverse(
                        "composer:resources_list",
                        kwargs={"course_id": course.id},
                    ),
                }
            ],
            "section_title": "Edit Educator Course Resource",
            "section_description": f"Edit course resource '{self.object.name}'",
            "section_tabs": section_tabs,
        }
        context.update(extra_context)
        return context


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMX views
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def course_resource_delete_hx(request, course_id: int, pk: int):
    """
    Delete a course resource from this course.
    """
    course = get_object_or_404(Course, id=course_id)
    course_resource = course.course_resources.get(id=pk)
    course_resource.delete()

    context = {
        "course_resources": course.course_resources.all(),
        "course": course,
    }

    return render(
        request, "composer/course_resources/hx/course_resources_table.html", context
    )


def educator_course_resource_delete_hx(request, course_id: int, pk: int):
    """
    Delete an educator course resource from this course.
    """
    course = get_object_or_404(Course, id=course_id)
    educator_course_resource = course.educator_resources.get(id=pk)
    educator_course_resource.delete()

    context = {
        "educator_course_resources": course.educator_resources.all(),
        "course": course,
    }

    return render(
        request,
        "composer/course_resources/hx/educator_course_resources_table.html",
        context,
    )
