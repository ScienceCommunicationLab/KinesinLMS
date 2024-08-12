import logging
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from django import forms
from django.forms import HiddenInput

from kinesinlms.course.models import Course
from kinesinlms.survey.models import Survey, SurveyProvider

logger = logging.getLogger(__name__)


class CourseSurveyForm(forms.ModelForm):
    """
    This form is for creating "Survey" instances that represent surveys
    created in the external survey provider.

    This form *does not* handle attaching a survey to a course via a block,
    that is handled by the SurveyPanelForm.

    Args:
        forms (_type_): _description_

    Returns:
        _type_: _description_
    """
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        widget=HiddenInput(),
    )

    provider = forms.ModelChoiceField(
        queryset=SurveyProvider.objects.all(),
    )

    class Meta:
        model = Survey
        fields = [
            "course",
            "provider",
            "type",
            "name",
            "send_reminder_email",
            "days_delay",
            "include_uid",
            "survey_id",
            "url"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        helper = FormHelper(self)
        self.helper = helper
        helper.form_tag = False
        helper.layout = Layout(
            "course",
            "provider",
            "type",
            "name",
            "survey_id",
            "url",
            "include_uid",
            HTML("""
                <h3>Reminder Email</h3>
                 <hr/>
                 """),
            "send_reminder_email",
            HTML("""
                 <div class="alert alert-light">
                 <p>If "Send reminder email" is selected, the event that triggers KinesinLMS to schedule the email reminder
                 depends on the type of survey.</p>
                    <ul>          
                        <li><strong>pre-course:</strong> Reminder email is scheduled when a student enrolls in a course.</li>
                        <li><strong>basic:</strong>        Reminder email is scheduled when student first views a unit with the survey.</li>
                        <li><strong>post-course:</strong>   Reminder email is scheduled when a student completes a course.</li>
                        <li><strong>follow-up:</strong>     Reminder email is scheduled when a student completes a course.</li>
                    </ul>
                 <p>Furthermore, if "days delay" is also defined, the reminder email will be sent after the specified number of days after the email is scheduled.</p>
                 </div>
                 """),
            "days_delay",
        )
        self.helper = helper

    def clean(self):
        cleaned_data = super().clean()
        # TODO: Cleans...

        return cleaned_data
