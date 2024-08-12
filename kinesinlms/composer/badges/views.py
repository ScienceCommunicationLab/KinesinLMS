import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, UpdateView, CreateView

from kinesinlms.badges.models import BadgeClass
from kinesinlms.composer.badges.forms import BadgeClassForm
from kinesinlms.composer.view_helpers import get_course_edit_tabs
from kinesinlms.course.models import Course
from kinesinlms.users.mixins import SuperuserRequiredMixin

logger = logging.getLogger(__name__)


class CourseBadgeClassListView(SuperuserRequiredMixin, ListView):
    model = BadgeClass
    template_name = "composer/badges/course_badge_classes_list.html"
    context_object_name = "badge_classes"

    def get_queryset(self):
        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)
        return course.badge_classes.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)

        course_name = course.display_name
        if not course_name:
            course_name = "( no name )"

        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="badges"
        )
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course_name}",
            "section": "badges",
            "breadcrumbs": [],
            "section_tabs": section_tabs,
        }
        context.update(extra_context)

        return context


class CourseBadgeClassCreateView(SuperuserRequiredMixin, CreateView):
    model = BadgeClass
    template_name = "composer/badges/course_badge_class_create.html"
    context_object_name = "badge_class"
    form_class = BadgeClassForm

    def get_initial(self):
        initial = super().get_initial()
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        initial["course"] = course
        return initial

    def get_success_url(self):
        success_url = reverse_lazy(
            "composer:course_badge_classes_list",
            kwargs={"course_id": self.kwargs["course_id"]},
        )
        return success_url

    def form_valid(self, form):
        instance = form.save(commit=False)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        instance.course = course
        instance.save()
        messages.success(self.request, "Course badge class created successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="badges"
        )
        badge_class_list_url = reverse(
            "composer:course_badge_classes_list", kwargs={"course_id": course.id}
        )
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": [
                {"label": "Course Badge Classes", "url": badge_class_list_url}
            ],
            "section": "badges",
            "section_title": "Create Course Badges",
            "description": None,
            "section_tabs": section_tabs,
        }
        context.update(extra_context)
        return context


class CourseBadgeClassUpdateView(SuperuserRequiredMixin, UpdateView):
    model = BadgeClass
    template_name = "composer/badges/course_badge_class_update.html"
    context_object_name = "badge_class"
    form_class = BadgeClassForm

    def get_object(self, queryset=...):
        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)
        badge_class_id = self.kwargs["pk"]
        badge_class = get_object_or_404(BadgeClass, id=badge_class_id, course=course)
        return badge_class

    def get_success_url(self):
        success_url = reverse_lazy(
            "composer:course_badge_class_update",
            kwargs={"course_id": self.kwargs["course_id"], "pk": self.kwargs["pk"]},
        )
        return success_url

    def form_valid(self, form):
        messages.success(self.request, "Badge class updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="badges"
        )
        badge_class_list_url = reverse(
            "composer:course_badge_classes_list", kwargs={"course_id": course.id}
        )
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": [
                {
                    "label": "Course Badge Classes",
                    "url": badge_class_list_url,
                }
            ],
            "section": "badges",
            "section_title": "Edit Course Badge Classes",
            "section_tabs": section_tabs,
        }
        context.update(extra_context)
        return context


# ~~~~~~~~~~~~
# HTMx views
# ~~~~~~~~~~~~


def course_badge_class_delete_hx(request, course_id: int, pk: int):
    """
    Delete a BadgeClass from this course.
    """
    course = get_object_or_404(Course, id=course_id)
    bc = course.badge_classes.get(id=pk)

    bc.delete()

    context = {"badge_classes": course.badge_classes.all(), "course": course}

    return render(request, "composer/badges/hx/badge_classes_table.html", context)
