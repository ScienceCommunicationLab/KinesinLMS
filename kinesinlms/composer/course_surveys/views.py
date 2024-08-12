import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, UpdateView, CreateView

from kinesinlms.composer.course_surveys.forms import CourseSurveyForm
from kinesinlms.composer.view_helpers import get_course_edit_tabs
from kinesinlms.course.models import Course
from kinesinlms.survey.models import Survey, SurveyProvider
from kinesinlms.users.mixins import SuperuserRequiredMixin

logger = logging.getLogger(__name__)


class CourseSurveysListView(SuperuserRequiredMixin, ListView):
    model = Survey
    template_name = 'composer/surveys/course_surveys_list.html'
    context_object_name = 'course_surveys'

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        course = get_object_or_404(Course, id=course_id)
        return course.surveys.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_id = self.kwargs['course_id']
        course = get_object_or_404(Course, id=course_id)

        course_name = course.display_name
        if not course_name:
            course_name = "( no name )"

        section_tabs = get_course_edit_tabs(current_course=course,
                                            active_section='course_surveys')
        extra_context = {
            "course": course,
            "name": course_name,
            "title": f"Edit Course : {course.display_name}",
            "survey_providers_exist": SurveyProvider.objects.exists(),
            "section_breadcrumbs": None,
            "section": "course_surveys",
            "section_tabs": section_tabs
        }
        context.update(extra_context)

        return context


class CourseSurveyCreateView(SuperuserRequiredMixin, CreateView):
    model = Survey
    template_name = 'composer/surveys/course_survey_create.html'
    context_object_name = 'course_survey'
    form_class = CourseSurveyForm

    def get_initial(self):
        initial = super().get_initial()
        course = get_object_or_404(Course, id=self.kwargs['course_id'])
        initial['course'] = course
        return initial

    def get_success_url(self):
        success_url = reverse_lazy('composer:course_surveys_list',
                                   kwargs={'course_id': self.kwargs['course_id']})
        return success_url

    def form_valid(self, form):
        instance = form.save(commit=False)
        course = get_object_or_404(Course, id=self.kwargs['course_id'])
        instance.course = course
        instance.save()
        messages.success(self.request, "Course survey created successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs['course_id'])
        section_tabs = get_course_edit_tabs(current_course=course,
                                            active_section='course_surveys')
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": [
                {
                    "label": "Course surveys",
                    "url": reverse('composer:course_surveys_list',
                                   kwargs={'course_id': course.id})
                }
            ],
            "section": "course_surveys",
            "section_title": "Create Course surveys",
            "section_description": None,
            "section_tabs": section_tabs
        }
        context.update(extra_context)
        return context


class CourseSurveyUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Survey
    template_name = 'composer/surveys/course_survey_update.html'
    context_object_name = 'course_survey'
    form_class = CourseSurveyForm

    def get_object(self, queryset=...):
        course_id = self.kwargs['course_id']
        course = get_object_or_404(Course, id=course_id)
        course_survey_id = self.kwargs['pk']
        course_survey = get_object_or_404(Survey, id=course_survey_id, course=course)
        return course_survey

    def get_success_url(self):
        success_url = reverse_lazy('composer:course_survey_update',
                                   kwargs={
                                       'course_id': self.kwargs['course_id'],
                                       'pk': self.kwargs['pk']
                                   })
        return success_url

    def form_valid(self, form):
        messages.success(self.request, "Course survey updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs['course_id'])
        section_tabs = get_course_edit_tabs(current_course=course,
                                            active_section='course_surveys')
        extra_context = {
            "course": course,
            "title": f"Edit Course : {course.display_name}",
            "section_breadcrumbs": [
                {
                    "label": "Course surveys",
                    "url": reverse('composer:course_surveys_list',
                                   kwargs={'course_id': course.id})
                }
            ],
            "section": "course_surveys",
            "section_title": "Edit Course Survey",
            "desction_description": f"Edit course survey '{self.object.name}'",
            "section_tabs": section_tabs
        }
        context.update(extra_context)
        return context


def course_survey_delete_hx(request,
                              course_id: int,
                              pk: int):
    """
    Delete a course survey from this course.
    """
    course = get_object_or_404(Course, id=course_id)
    course_survey = course.surveys.get(id=pk)
    course_survey.delete()

    context = {
        "course_surveys": course.surveys.all(),
        "course": course
    }

    return render(request, 'composer/surveys/hx/course_surveys_table.html', context)
