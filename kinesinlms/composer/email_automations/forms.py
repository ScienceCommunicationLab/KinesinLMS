from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from django import forms
from django.forms import ModelForm, CheckboxSelectMultiple
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from kinesinlms.email_automation.models import CourseEmailAutomationSettings, TRACKING_EVENTS_FOR_EMAIL_AUTOMATION
from kinesinlms.tracking.event_types import NON_PREFIXED_EVENTS, TRACKING_EVENT_HELP_TEXT, TrackingEventType


class CourseEmailAutomationSettingsForm(ModelForm):
    send_event_as_tag = forms.MultipleChoiceField(
        label=_("Send Tracking Event as Tag"),
        choices=[
            (item.name, item.value) for item in TRACKING_EVENTS_FOR_EMAIL_AUTOMATION
        ],
        initial='option_one',
        widget=forms.CheckboxSelectMultiple,
        help_text=_("<div class='mt-1'>Select the tracking events that should be "
                    "sent to the email automation service "
                    "as a tag for a particular contact.<br/>"
                    "(This is useful if your service allows you to trigger email automations for a contact when the tag is set.)</div>"),
        required=False
    )

    class Meta:
        model = CourseEmailAutomationSettings
        fields = [
            'active',
            'send_event_as_tag'
        ]
        widgets = {
            'send_event_as_tag': CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        helper = FormHelper(self)

        if self.instance and self.instance.course:
            course_token = self.instance.course.token
            choices = []
            for choice in TRACKING_EVENTS_FOR_EMAIL_AUTOMATION:

                if choice.name == TrackingEventType.USER_REGISTRATION.name:
                    # User doesn't configure this on a per-course basis
                    continue

                help_text = TRACKING_EVENT_HELP_TEXT.get(choice.name, "")
                if help_text:
                    help_text = f"<span class='small text-muted'>{help_text}</span>"

                if choice.value in NON_PREFIXED_EVENTS:
                    choices.append((choice.name, mark_safe(
                        f"<div class='d-flex flex-column mb-3'><div >{choice.value}</div><div>{help_text}</div></div>")))
                else:
                    choices.append((choice.name, mark_safe(
                        f"<div class='d-flex flex-column mb-3'><div >{course_token}:{choice.value}</div><div>{help_text}</div></div>")))

            self.fields['send_event_as_tag'].choices = choices

        helper.layout = Layout(
            'active',
            'send_event_as_tag'
        )
        self.helper = helper
