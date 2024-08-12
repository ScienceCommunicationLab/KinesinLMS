import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, UpdateView, CreateView

from kinesinlms.badges.models import BadgeClass
from kinesinlms.composer.milestones.forms import MilestoneForm
from kinesinlms.composer.view_helpers import get_course_edit_tabs
from kinesinlms.course.models import Course, Milestone
from kinesinlms.users.mixins import SuperuserRequiredMixin

logger = logging.getLogger(__name__)


class CourseMilestonesListView(SuperuserRequiredMixin, ListView):
    model = BadgeClass
    template_name = "composer/milestones/course_milestones_list.html"
    context_object_name = "milestones"

    def get_queryset(self):
        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)
        return course.milestones.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)

        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="milestones"
        )
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": None,
            "section": "milestones",
            "section_tabs": section_tabs,
        }
        context.update(extra_context)

        return context


class CourseMilestoneCreateView(SuperuserRequiredMixin, CreateView):
    model = Milestone
    template_name = "composer/milestones/course_milestone_create.html"
    context_object_name = "milestone"
    form_class = MilestoneForm

    def get_initial(self):
        initial = super().get_initial()
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        initial["course"] = course
        return initial

    def get_success_url(self):
        success_url = reverse_lazy(
            "composer:course_milestones_list",
            kwargs={"course_id": self.kwargs["course_id"]},
        )
        return success_url

    def form_valid(self, form):
        instance = form.save(commit=False)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        instance.course = course
        instance.save()
        messages.success(self.request, "Course milestone created successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="milestones"
        )

        milestones_list_url = reverse(
            "composer:course_milestones_list", kwargs={"course_id": course.id}
        )
        extra_context = {
            "title": f"Edit Course : {course.display_name}",
            "section": "milestones",
            "section_breadcrumbs": [
                {"label": "Milestones", "url": milestones_list_url}
            ],
            "section_title": "Create Course Milestone",
            "course": course,
            "description": None,
            "section_tabs": section_tabs,
        }
        context.update(extra_context)
        return context


class CourseMilestoneUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Milestone
    template_name = "composer/milestones/course_milestone_update.html"
    context_object_name = "milestone"
    form_class = MilestoneForm

    def get_object(self, queryset=...):
        course_id = self.kwargs["course_id"]
        course = get_object_or_404(Course, id=course_id)
        milestone_id = self.kwargs["pk"]
        milestone = get_object_or_404(Milestone, id=milestone_id, course=course)
        return milestone

    def get_success_url(self):
        success_url = reverse_lazy(
            "composer:course_milestone_update",
            kwargs={"course_id": self.kwargs["course_id"], "pk": self.kwargs["pk"]},
        )
        return success_url

    def form_valid(self, form):
        messages.success(self.request, "Milestone updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs["course_id"])
        section_tabs = get_course_edit_tabs(
            current_course=course, active_section="milestones"
        )
        milestones_list_url = reverse(
            "composer:course_milestones_list", kwargs={"course_id": course.id}
        )
        extra_context = {
            "title": f"Edit Course : {course.display_name}",
            "course": course,
            "section": "milestones",
            "section_breadcrumbs": [
                {"label": "Milestones", "url": milestones_list_url}
            ],
            "section_title": "Edit Course Milestone",
            "section_description": f"Edit milestone '{self.object.name}'",
            "section_tabs": section_tabs,
        }
        context.update(extra_context)
        return context


def course_milestone_delete_hx(request, course_id: int, pk: int):
    """
    Delete a milestone from this course.
    """
    course = get_object_or_404(Course, id=course_id)
    milestone = course.milestones.get(id=pk)

    milestone.delete()

    context = {"milestones": course.milestones.all(), "course": course}

    return render(request, "composer/milestones/hx/milestones_table.html", context)
