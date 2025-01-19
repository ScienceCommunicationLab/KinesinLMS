import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Fieldset, Layout, Submit
from django import forms
from django.utils.translation import gettext_lazy as _

from kinesinlms.composer.forms.base import ComposerModelForm
from kinesinlms.course.constants import CourseUnitType
from kinesinlms.course.models import Course, CourseUnit
from kinesinlms.learning_library.constants import ContentFormatType

logger = logging.getLogger(__name__)


#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Basic Forms
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~


class AddCourseForm(forms.Form):
    course_json = forms.CharField(
        label="Course JSON",
        help_text="Add json to create or update course.",
        widget=forms.Textarea,
    )

    create_forum_items = forms.BooleanField(label="Create forum items", initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()


class DeleteCourseForm(forms.Form):
    delete_block_resources = forms.BooleanField(
        label="Delete unused block resources.",
        required=False,
    )


class ImportCourseFromArchiveForm(forms.Form):
    file = forms.FileField(
        label="Select course archive .klms file",
        required=True,
        widget=forms.ClearableFileInput(attrs={"accept": [".klms", ".ibioarchive"], "multiple": False}),
    )

    create_forum_items = forms.BooleanField(
        label="Create forum items",
        initial=False,
        required=False,
        help_text="If checked, the importer will attempt to set up forum items in the remote forum service for any forum topics defined in the course. You must have a ForumProvider configured to use this option.",
    )

    display_name = forms.CharField(
        max_length=400,
        help_text="This is the course name that students will see.",
        label="Course name",
        widget=forms.TextInput(attrs={"required": False, "title": "Course name"}),
    )

    course_slug = forms.SlugField(
        max_length=200,
        help_text="A slug for the course (usually all caps). For example, DEMO for a demo course.",
        widget=forms.TextInput(attrs={"required": False, "title": "Course slug"}),
    )

    course_run = forms.SlugField(
        max_length=200,
        help_text="A run for the course (usually all caps). For example, '2024' for the year of the run, or maybe 'SP' for self-paced.",
        widget=forms.TextInput(attrs={"required": False, "title": "Course run"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["display_name"].required = False
        self.fields["course_slug"].required = False
        self.fields["course_run"].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "file",
            "create_forum_items",
            Fieldset(
                "These fields are optional. Use them if you want to override the name, slug, or run provided in the archive",
                "display_name",
                "course_slug",
                "course_run",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data["display_name"] == "":
            cleaned_data["display_name"] = None
        if cleaned_data["course_slug"] == "":
            cleaned_data["course_slug"] = None
        if cleaned_data["course_run"] == "":
            cleaned_data["course_run"] = None
        return cleaned_data


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Model Forms
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~


class CourseForm(forms.ModelForm):
    enrollment_start_date = forms.DateTimeField(
        required=False,
        input_formats=["%m/%d/%Y, %H:%M"],
        widget=forms.widgets.DateTimeInput(format="%m/%d/%Y, %H:%M", attrs={"placeholder": "MM/DD/YY, HH:MM "}),
    )
    enrollment_end_date = forms.DateTimeField(
        required=False,
        input_formats=["%m/%d/%Y, %H:%M"],
        widget=forms.widgets.DateTimeInput(format="%m/%d/%Y, %H:%M", attrs={"placeholder": "MM/DD/YY, HH:MM "}),
    )

    start_date = forms.DateTimeField(
        required=False,
        input_formats=["%m/%d/%Y, %H:%M"],
        widget=forms.widgets.DateTimeInput(format="%m/%d/%Y, %H:%M", attrs={"placeholder": "MM/DD/YY, HH:MM "}),
    )

    end_date = forms.DateTimeField(
        required=False,
        input_formats=["%m/%d/%Y, %H:%M"],
        widget=forms.widgets.DateTimeInput(format="%m/%d/%Y, %H:%M", attrs={"placeholder": "MM/DD/YY, HH:MM "}),
    )

    class Meta:
        model = Course
        fields = [
            "display_name",
            "slug",
            "run",
            "short_name",
            "enable_certificates",
            "enable_badges",
            "enable_surveys",
            "enable_email_automations",
            "enable_forum",
            "enable_course_outline",
            "enrollment_start_date",
            "enrollment_end_date",
            "start_date",
            "end_date",
            "advertised_start_date",
            "self_paced",
            "days_early_for_beta",
            "playlist_url",
            "course_home_html_content",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "course-form"
        self.helper.form_method = "post"
        self.helper.form_action = ""
        self.helper.add_input(Submit("submit", "Submit"))


class EditCourseHeaderForm(ComposerModelForm):
    display_name = forms.CharField(required=False)

    html_content_type = forms.ChoiceField(
        choices=[(item.name, item.value) for item in ContentFormatType],
        required=True,
        help_text="The format of the content in this block.",
    )

    class Meta:
        model = CourseUnit
        fields = [
            "display_name",
            "slug",
            "type",
            "enable_template_tags",
            "html_content",
            "html_content_type",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].default = CourseUnitType.STANDARD.name

        self.fields["display_name"].label = "Unit Title"
        self.fields["display_name"].help_text = _(
            "The title of this unit. This is the text that will appear in the unit header."
        )

        self.fields["slug"].help_text = _(
            "A slug for this unit (must be unique across the site). "
            "This slug is meant more for internal use by authors and staff, "
            "and is not really used by students. "
            "If you leave this blank, a slug will be generated from the unit title."
        )

        self.fields["type"].help_text = _("The type of unit. (This is usually left as " "'Standard'.)")

        self.fields["html_content"].help_text = _(
            "HTML text to be shown after the unit header but before any blocks. (This "
            "is usually left blank. Use blocks for HTML code.)"
        )
