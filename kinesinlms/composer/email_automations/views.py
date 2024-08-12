import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import UpdateView

from kinesinlms.composer.email_automations.forms import CourseEmailAutomationSettingsForm
from kinesinlms.composer.view_helpers import get_course_edit_tabs
from kinesinlms.course.models import Course
from kinesinlms.email_automation.models import CourseEmailAutomationSettings
from kinesinlms.users.mixins import SuperuserRequiredMixin

logger = logging.getLogger(__name__)


class CourseEmailAutomationsSettingsUpdateView(SuperuserRequiredMixin, UpdateView):
    model = CourseEmailAutomationSettings
    template_name = 'composer/email_automations/course_email_automations_settings_update.html'
    context_object_name = 'course_email_automations_settings'
    form_class = CourseEmailAutomationSettingsForm

    def get_object(self, queryset=...):
        course_id = self.kwargs['pk']
        settings, created = CourseEmailAutomationSettings.objects.get_or_create(course_id=course_id)
        return settings

    def get_success_url(self):
        success_url = reverse_lazy('composer:course_email_automations_settings_edit',
                                   kwargs={
                                       'pk': self.kwargs['pk']
                                   })
        return success_url

    def form_valid(self, form):
        messages.success(self.request, "Course email automation settings updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs['pk'])
        section_tabs = get_course_edit_tabs(current_course=course,
                                            active_section='email_automations')
        extra_context = {
            "section_breadcrumbs": None,
            "course": course,
            "section": "email_automations",
            "title": "Edit Course Email Automation Settings",
            "description": f"",
            "section_tabs": section_tabs
        }
        context.update(extra_context)
        return context
