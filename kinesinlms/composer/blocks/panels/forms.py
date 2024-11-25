"""
Definitions for forms to be used in panels.
These are simply Django forms and should be relatively straightforward and
easy to understand.

Most forms target a subset of fields directly on the Block model.
But sometimes a Block's properties are defined in other, closely related models,
such as the Assessment model or the ExternalTooView model, which is in a
one-to-one relationship with a Block and handles saving domain-specific information.

In this case, the form may target that helper model. For example, in
the cases of assessments, that's the Assessment model, and in the case
of forum topics, the ForumTopic model.
"""

import copy
import json
import logging
from typing import Dict, List, Optional

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Row
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import transaction
from django.forms import BaseFormSet, HiddenInput, ModelForm, Textarea, formset_factory
from django.utils.translation import gettext as _
from tinymce.widgets import TinyMCE

from kinesinlms.assessments.models import Assessment
from kinesinlms.composer.blocks.panels.utils import get_jupyter_wrapper_html
from kinesinlms.composer.forms.fields import LearningObjectivesField
from kinesinlms.composer.forms.helpers import save_learning_objectives
from kinesinlms.composer.models import ComposerSettings
from kinesinlms.course.models import Course, CourseNode
from kinesinlms.course.tasks import rescore_assessment_milestone_progress
from kinesinlms.external_tools.models import ExternalToolView
from kinesinlms.forum.service.base_service import BaseForumService
from kinesinlms.forum.utils import get_forum_service
from kinesinlms.learning_library.constants import BlockType, ResourceType
from kinesinlms.learning_library.models import Block, BlockResource, Resource, UnitBlock
from kinesinlms.sits.models import SimpleInteractiveTool
from kinesinlms.survey.models import Survey, SurveyBlock

logger = logging.getLogger(__name__)


class BasePanelModelForm(ModelForm):
    """
    Base form class for editing one or more properties of a Block or item
    related to a Block (e.g. Assessment).

    This class expects the subclass to decide which model to use for the
    form (Block or e.g. Assessment), and which fields to include.

    """

    def __init__(
        self,
        *args,
        course: Course = None,
        block: Block = None,
        unit_block: UnitBlock = None,
        unit_node: CourseNode = None,
        user=None,
        **kwargs,
    ):
        """
        Initialize the base class that informs all panel forms.
        We might be a little excessive to require course, block,
        unit_block and user, but it's a good way to ensure that
        we have all the necessary information to initialize and
        support the form.
        """
        if not course:
            raise ValueError("course cannot be None")
        if not block:
            raise ValueError("block cannot be None")
        if not unit_block:
            raise ValueError("unit_block cannot be None")
        if not unit_node:
            raise ValueError("unit_node cannot be None")
        if not user:
            raise ValueError("user cannot be None")
        if "instance" not in kwargs:
            raise ValueError("Subclass should have declared 'instance' in kwargs")
        self.course = course
        self.block: Block = block
        self.render_html_content: Course = course
        self.unit_block: UnitBlock = unit_block
        self.unit_node: CourseNode = unit_node
        self.user = user
        self.settings = ComposerSettings.objects.get_or_create(user=user)[0]
        self.panel_id = block.id
        super().__init__(*args, **kwargs)

    @property
    def has_file_upload(self):
        return False


class HTMLBlockPanelForm(BasePanelModelForm):
    """
    Form for editing HTML content portion of an HTML block.
    """

    html_content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"cols": 80, "rows": 30}),
    )

    # TODO:
    #   Add support for HTML content type, including Markdown.
    #   This will require dynamically toggling the wysiwyg editor.
    #   Therefore, at the moment we're only supporting HTML and handling
    #   toggle of editor at higher level before this form is shown.

    # html_content_type = forms.ChoiceField(
    #    choices=[(item.name, item.value) for item in ContentFormatType],
    #    required=True,
    #    widget=forms.RadioSelect(attrs={"class": "btn-check"}),
    #    help_text="The format of the content in this block."
    # )

    class Meta:
        model = Block
        fields = [
            "display_name",
            "html_content",
        ]

    def __init__(self, *args, **kwargs):
        block = kwargs["block"]
        kwargs["instance"] = block

        super().__init__(*args, **kwargs)

        self.fields["display_name"].label = "Block header"
        self.fields["html_content"].label = "Content"

        if self.instance.type == BlockType.ASSESSMENT.name:
            extra_help = _(
                "Since this block is an assessment, this HTML content "
                "will appear above the actual assessment content."
            )
            self.fields["html_content"].help_text += extra_help
        elif self.instance.type != BlockType.HTML_CONTENT.name:
            extra_help = _("This HTML content will appear at the top of the block.")
            self.fields["html_content"].help_text += extra_help

        composer_settings, created = ComposerSettings.objects.get_or_create(
            user=self.user
        )
        if composer_settings.wysiwyg_active:
            self.fields["html_content"].widget = TinyMCE(attrs={"cols": 80, "rows": 30})
            self.fields["html_content"].help_text = _(
                "Enter html content here. (If you want to enter raw HTML, close this "
                "form and disable this editor with the WYSIWYG toggle in the "
                "contents nav bar)."
            )
        else:
            self.fields["html_content"].help_text = _(
                "Enter html content here. (If you want a WYSIWYG editor, close this "
                "form and enable WYSIWYG with the toggle button in the "
                "contents nav bar)."
            )

        self.helper = FormHelper()
        self.helper.form_method = "post"

        # Construct a drop zone element to wrap the 'html_content' form control.
        # This div will handle the user dragging image onto the html_content textarea.
        # When this happens, we'll try to do an auto-upload and insert the image URL
        # into the text.
        drop_zone_div = Div(
            "html_content",
            id="image_drop_zone",
            data_course_id=self.course.id,
            data_block_id=self.block.id,
            hx_encoding="multipart/form-data",
        )

        self.helper.layout = Layout(
            "display_name",
            drop_zone_div,
        )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class JupyterPanelForm(BasePanelModelForm):
    """
    Form for editing Jupyter content and either selecting an existing Jupyter
    resource or uploading a new one. Ensures only one Jupyter can be associated
    with a block.
    """

    html_content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"cols": 80, "rows": 5}),
        help_text=_("This content will appear above the link to open the notebook."),
    )

    class Meta:
        model = Block
        fields = [
            "display_name",
            "html_content",
        ]

    @property
    def has_file_upload(self):
        return True

    def __init__(self, *args, **kwargs):
        block = kwargs["block"]
        kwargs["instance"] = block
        super().__init__(*args, **kwargs)

        self.fields["display_name"].label = _("Block header")

        # Get current notebook BlockResource if it exists
        try:
            block_resource = BlockResource.objects.get(
                block=block, resource__type=ResourceType.JUPYTER_NOTEBOOK.name
            )
            resource: Resource = block_resource.resource
        except BlockResource.DoesNotExist:
            block_resource = None
            resource = None

        composer_settings, created = ComposerSettings.objects.get_or_create(
            user=self.user
        )
        if composer_settings.wysiwyg_active:
            self.fields["html_content"].widget = TinyMCE(attrs={"cols": 80, "rows": 10})
            self.fields["html_content"].help_text = _(
                "Enter html content here. (If you want to enter raw HTML, close this "
                "form and disable this editor with the WYSIWYG toggle in the "
                "contents nav bar)."
            )
        else:
            self.fields["html_content"].help_text = _(
                "Enter html content here. (If you want a WYSIWYG editor, close this "
                "form and enable WYSIWYG with the toggle button in the "
                "contents nav bar)."
            )

        jupyter_wrapper_html = get_jupyter_wrapper_html(
            resource=resource,
            course=self.course,
            block=block,
            block_resource=block_resource,
        )

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.layout = Layout(
            HTML(jupyter_wrapper_html),
            "display_name",
            "html_content",
        )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        """
        Save the block and update its resource association through BlockResource.
        If a new notebook is uploaded, creates a new Resource first.
        Uses transaction.atomic to ensure data consistency.
        """
        block = super().save(commit=False)
        block.type = BlockType.JUPYTER_NOTEBOOK.name

        if commit:
            block.save()

            new_notebook = self.cleaned_data.get("new_notebook")
            selected_resource = self.cleaned_data.get("notebook_resource")

            try:
                # Remove any existing notebook resource associations
                BlockResource.objects.filter(
                    block=block, resource__type=ResourceType.JUPYTER_NOTEBOOK.name
                ).delete()

                if new_notebook:
                    # Create new Resource for uploaded file
                    resource = Resource.objects.create(
                        resource_file=new_notebook,
                        type=ResourceType.JUPYTER_NOTEBOOK.name,
                        description=self.cleaned_data.get("description", ""),
                    )
                    selected_resource = resource

                # Create new BlockResource association
                if selected_resource:
                    BlockResource.objects.create(
                        block=block, resource=selected_resource
                    )

                block.save()

            except ValidationError as e:
                transaction.set_rollback(True)
                raise e

        return block


class ExternalToolViewPanelForm(BasePanelModelForm):
    target_link_uri = forms.CharField(
        label="Target Link URI",
        required=False,
        widget=forms.TextInput(
            attrs={"readonly": "readonly", "class": "form-control-plaintext"}
        ),
        help_text=(
            "This field shows the target link URI for this external tool view. "
            "It is constructed using the custom launch URI and/or the default "
            "launch URI from the ExternalToolProvider, depending on the settings."
        ),
    )

    class Meta:
        model = ExternalToolView
        fields = [
            "external_tool_provider",
            "resource_link_id",
            "launch_type",
            "custom_target_link_uri",
        ]

    def __init__(self, *args, **kwargs):
        block = kwargs["block"]
        if not block.external_tool_view:
            raise ValueError("Block must have an external_tool_view")
        kwargs["instance"] = block.external_tool_view

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = "post"

        # Define form layout
        self.helper.layout = Layout(
            "external_tool_provider",
            "resource_link_id",
            "launch_type",
            "custom_target_link_uri",
            HTML(
                f"""
                    <div class="form-group mb-5">
                    <label for="id_target_link_uri">Target Link URI</label>
                    <div class="alert alert-info mt-2">
                    {self.instance.target_link_uri or ''}
                    </div>
                    <small class="form-text text-muted">
                    This field shows the "target 
                    link URI" for this external tool view. 
                    It defaults to the "Launch URL" defined in the External Tool 
                    Provider. But you can override it using
                    the 'Custom Target Link URI' field above.
                    </small>
                    </div>
                """
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class SITDetailsPanelForm(BasePanelModelForm):
    definition = forms.CharField(
        label="Definition JSON",
        help_text="Add json to define this SIT.",
        required=True,
        widget=forms.Textarea,
    )

    instructions = forms.CharField(
        label=_("Instructions"),
        help_text=_(
            "Detailed instructions for this SIT, if any. "
            "(More general information can go in the 'HTML Content' field.)"
        ),
        required=False,
        widget=forms.Textarea,
    )

    class Meta:
        model = SimpleInteractiveTool
        fields = [
            "name",
            "tool_type",
            "slug",
            "graded",
            "max_score",
            "instructions",
            "definition",
        ]

    def clean_definition(self) -> Dict:
        definition = self.cleaned_data["definition"]
        try:
            definition_json = json.loads(definition)
        except json.JSONDecodeError as e:
            raise forms.ValidationError("Invalid JSON format: {}".format(e))

        # Don't worry about validating against SCHEMA for now

        return definition_json

    def __init__(self, *args, **kwargs):
        block = kwargs["block"]
        if not block.simple_interactive_tool:
            raise ValueError("Block must have a simple_interactive_tool")
        kwargs["instance"] = block.simple_interactive_tool
        super().__init__(*args, **kwargs)
        self.fields["slug"].help_text = (
            "A unique identifier for this SIT "
            "(A slug is usually letters, numbers, underscores and hyphens)."
        )


class VideoContentPanelForm(BasePanelModelForm):
    """
    Form for editing Video content.
    """

    video_id = forms.CharField(
        max_length=20,
        required=True,
        help_text="The YouTube video ID. This is the part of the URL after 'v='. ",
    )

    header = forms.CharField(
        widget=Textarea(),
        required=False,
        help_text="Content that will appear in the styled header box above the video. "
        "Try to keep this content succinct ... only two or three lines.",
    )

    class Meta:
        model = Block
        fields = ["display_name", "video_id", "header"]

    def __init__(self, *args, **kwargs):
        block = kwargs["block"]
        kwargs["instance"] = block
        if block.json_content is None:
            block.json_content = {}

        # Extract values from json_content
        initial_video_id = block.json_content.get("video_id", None)
        initial_header = block.json_content.get("header", None)

        # Pass initial values to the superclass
        kwargs["initial"] = {"video_id": initial_video_id, "header": initial_header}

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Update json_content with form data
        instance.json_content = {
            "video_id": self.cleaned_data["video_id"],
            "header": self.cleaned_data["header"],
        }

        if commit:
            instance.save()

        return instance


class RescoreAssessmentsFormMixin:
    """
    Triggers rescoring when grading-related changes are made to Assessments.
    """

    rescore_on_changed_fields = {"max_score", "graded", "join_type", "choices"}

    def post_save(self):
        """
        Trigger a rescore of this assessment if:

        1. We've changed one or more rescore_on_changed_fields, and
        1. The containing CourseNode has been released.
        """
        form_changed = self.has_changed()
        form_changed_fields = set(self.changed_data)
        assessment = self.instance

        if (
            form_changed
            and self.rescore_on_changed_fields & form_changed_fields
            and self.unit_node.is_released
        ):
            rescore_assessment_milestone_progress.apply_async(
                args=[],
                kwargs={
                    "course_id": self.course.id,
                    "assessment_id": assessment.id,
                },
            )


class BaseAssessmentPanelForm(RescoreAssessmentsFormMixin, BasePanelModelForm):
    """
    Logic common to all Assessment forms.
    """

    QUESTION_FIELDS = ["label", "question"]
    OPTIONS_FIELDS = ["graded", "max_score", "attempts_allowed", "complete_mode"]

    class Meta:
        model = Assessment
        fields = []

    def __init__(self, *args, **kwargs):
        block = kwargs["block"]
        if not block.assessment:
            raise ValueError("Block must have an assessment")

        kwargs["instance"] = block.assessment

        super().__init__(*args, **kwargs)

        self.customize_field_widgets()

    def customize_field_widgets(self):
        """
        Customizes the widgets and attributes used to construct the form fields.
        """

        if "question" in self.fields:
            self.fields["question"].widget.attrs["cols"] = "80"
            self.fields["question"].widget.attrs["rows"] = "3"

        if "attempts_allowed" in self.fields:
            self.fields["attempts_allowed"].widget.attrs["placeholder"] = _("unlimited")
            self.fields["attempts_allowed"].help_text = _(
                "Provide a number or leave empty for 'unlimited'"
            )
            self.fields["attempts_allowed"].widget.attrs["min"] = "1"

    def clean(self):
        cleaned_data = super().clean()

        # Null/empty/zero "attempts_allowed" means "unlimited"
        if not cleaned_data["attempts_allowed"]:
            cleaned_data["attempts_allowed"] = None

        return cleaned_data


class DoneIndicatorAssessmentPanelForm(BaseAssessmentPanelForm):
    done_indicator_label = forms.CharField(max_length=100, required=True)

    class Meta:
        model = Assessment
        fields = (
            BaseAssessmentPanelForm.QUESTION_FIELDS
            + ["done_indicator_label"]
            + BaseAssessmentPanelForm.OPTIONS_FIELDS
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_done_indicator_label = _("I have completed this assessment.")

        if not self.instance.definition_json:
            self.instance.definition_json = {}
        if "done_indicator_label" not in self.instance.definition_json:
            self.instance.definition_json["done_indicator_label"] = (
                self.default_done_indicator_label
            )

        self.fields["question"].label = _("Assessment label")
        self.fields["question"].help_text = _(
            "Text, if any, to appear to the right of the 'Assessment:' header. "
        )
        self.fields["question"].label = _("Assessment task description")
        self.fields["question"].help_text = _(
            "Task information shown just above the done indicator."
        )
        self.fields["done_indicator_label"].help_text = _(
            "The label to the right of the done indicator."
        )

        self.fields["done_indicator_label"].initial = self.default_done_indicator_label

        self.helper = FormHelper()

    def save(self, commit=True):
        """
        Take the validated data from the choices formset and build up
        the correct definition_json and solution_json for the assessment.
        """
        definition_json = self.instance.definition_json or {}
        if "done_indicator_label" not in definition_json:
            definition_json["done_indicator_label"] = self.default_done_indicator_label
        done_indicator_label = self.cleaned_data["done_indicator_label"]
        if done_indicator_label:
            definition_json["done_indicator_label"] = done_indicator_label

        self.instance.definition_json = definition_json
        if commit:
            self.instance.save()
        return self.instance


class BlockMetaForm(BasePanelModelForm):
    """
    Form for editing 'meta' information about a block, e.g.
    anything not directly related to its purpose.
    """

    slug = forms.CharField(
        max_length=100,
        required=False,
        help_text=(
            "A unique identifier for this block (A slug is usually lowercase "
            "letters, numbers, and hyphens). Students don't usually see this "
            "identifier, but it's still good to customize it to be more "
            "descriptive, as that can make analytics data more intelligible."
        ),
    )

    block_learning_objectives = LearningObjectivesField()

    enable_template_tags = forms.BooleanField(
        required=False,
        help_text="Enables a limited number of template tags in "
        "this model's html_content field.",
    )

    class Meta:
        model = Block
        fields = ["slug", "block_learning_objectives"]

    def __init__(self, *args, **kwargs):
        block = kwargs["block"]
        kwargs["instance"] = block

        super().__init__(*args, **kwargs)

        if hasattr(self.instance, "block_learning_objectives"):
            lo_slugs: List[str] = [
                item.learning_objective.slug
                for item in self.instance.block_learning_objectives.all()
            ]
            self.fields["block_learning_objectives"].initial = ",".join(lo_slugs)

    def save(self, *args, **kwargs):
        self.instance.version += 1
        save_learning_objectives(
            los_input=self.cleaned_data["block_learning_objectives"],
            block=self.instance,
        )
        return super().save(*args, **kwargs)


class LongFormTextAssessmentPanelForm(BaseAssessmentPanelForm):
    class Meta:
        model = Assessment
        fields = (
            BaseAssessmentPanelForm.QUESTION_FIELDS
            + BaseAssessmentPanelForm.OPTIONS_FIELDS
        )


class SurveyPanelForm(BasePanelModelForm):
    """
    Form for editing a SURVEY block.
    """

    survey = forms.ChoiceField(
        choices=[],  # choices will be dynamically populated in __init__
        required=True,
        help_text="Select a survey to display in this block.",
    )

    class Meta:
        model = Block
        fields = [
            "display_name",
            "html_content",
            "survey",
        ]

    def __init__(self, *args, **kwargs):
        block = kwargs["block"]
        kwargs["instance"] = block
        if hasattr(block, "survey_block"):
            initial_survey = block.survey_block
        else:
            initial_survey = None

        super().__init__(*args, **kwargs)

        # Get surveys for the current course
        surveys_for_course = Survey.objects.filter(course=self.course)

        # Update choices for the survey field
        self.fields["survey"].choices = [
            (survey.id, str(survey)) for survey in surveys_for_course
        ]

        self.initial["survey"] = initial_survey

        self.helper = FormHelper()

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        survey = self.cleaned_data["survey"]

        if not hasattr(instance, "survey_block"):
            survey_block = SurveyBlock.objects.create(block=instance, survey_id=survey)
        else:
            survey_block = instance.survey_block

        survey_block.survey_id = survey

        if commit:
            instance.save()
            survey_block.save()

        return instance


class ForumTopicPanelForm(BasePanelModelForm):
    """
    Form for editing information related to forum topic block.
    When a block is type FORUM_TOPIC, the Block's html_content
    should be used as the topic text in the remote forum provider.
    """

    is_course_forum_configured = False
    forum_service: Optional[BaseForumService] = None

    class Meta:
        model = Block
        fields = ["display_name", "html_content"]

    def __init__(self, *args, **kwargs):
        block = kwargs["block"]
        kwargs["instance"] = block
        super().__init__(*args, **kwargs)
        self.fields["display_name"].label = "Topic title"
        self.fields["display_name"].help_text = _(
            "This will appear as the title of the topic in the remote forum."
        )
        self.fields["html_content"].label = "Topic description"
        self.fields["html_content"].help_text = _(
            "The content here will appear as the topic " "in the remote forum."
        )
        self.helper = FormHelper()

        self.forum_service = get_forum_service()
        self.is_course_forum_configured = self.forum_service.is_course_forum_configured(
            self.course
        )

    def display_name(self):
        html_content = self.cleaned_data["html_content"]
        if len(html_content) <= 15:
            raise forms.ValidationError(
                _("The topic title must be at least 15 characters long.")
            )
        return html_content

    def clean_html_content(self):
        html_content = self.cleaned_data["html_content"]
        if len(html_content) <= 20:
            raise forms.ValidationError(
                _("The topic description must be at least 20 characters long.")
            )
        return html_content

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)

        self.forum_service.create_or_update_forum_topic(instance, self.course)

        return instance


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# CHOICES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# The poll and multiple choice assessment panel forms are a bit more complicated than
# the other panel forms because they have to deal with a formset for the choices.
# TODO: Probably a way to make this a bit more streamlined...this is first cut.


class BaseChoiceDefinitionForm(forms.Form):
    """
    Base form to add/edit/delete a single "choice".
    """

    text = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    choice_key = forms.CharField(
        max_length=2,
        validators=[
            MaxLengthValidator(
                limit_value=2, message="Choice key must be at most 2 characters."
            )
        ],
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "style": "width: 3rem",
                "maxlength": "2",
                "size": "2",
            }
        ),
    )

    DELETE = forms.BooleanField(
        required=False, initial=False, widget=forms.HiddenInput()
    )

    class Meta:
        fields = ["text", "choice_key"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["text"].widget.attrs["class"] = "form-control"
        self.fields["choice_key"].widget.attrs["class"] = "form-control"
        self._init_form_helper()

    def _init_form_helper(self):
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Row(
                Column("choice_key", css_class="col-1"),
                Column("text", css_class="col-9"),
                Column(
                    Field("DELETE", css_class="input-small hidden"),
                    HTML(
                        "<button type='button' "
                        "class='btn btn-danger btn-sm btn-remove-choice'>"
                        "Delete"
                        "</button>"
                    ),
                    css_class="col-1",
                ),
            )
        )

    def index(self) -> Optional[int]:
        if self.prefix:
            return int(self.prefix.split("-")[-1])
        else:
            return None

    def clean(self):
        cleaned_data = super().clean()
        if "DELETE" in cleaned_data and cleaned_data["DELETE"] is False:
            cleaned_data.pop("DELETE")

        return cleaned_data


class BaseChoiceFormSet(RescoreAssessmentsFormMixin, BaseFormSet):
    """
    Base choice formset which handles validating the submitted set of choices.

    Instantiate this using the formset_factory.
    """

    deletion_widget = HiddenInput

    min_choices = 2

    def clean(self):
        """
        Check that the choice keys are unique, and at least `min_choices` were provided.
        """
        cleaned_data = super().clean()

        if any(self.errors):
            return

        choice_keys = []
        total_choices = 0
        for form in self.forms:
            if not any(form.cleaned_data.values()):
                self.forms.remove(form)

            if self.can_delete and form.cleaned_data.get("DELETE", False):
                continue
            else:
                total_choices += 1

            choice_key = form.cleaned_data["choice_key"]
            if choice_key in choice_keys:
                raise forms.ValidationError(
                    "Choices cannot have the same key: %s" % choice_key
                )
            choice_keys.append(choice_key)

        if total_choices < self.min_choices:
            raise forms.ValidationError(
                f"At least {self.min_choices} choices must be provided."
            )

        return cleaned_data


class ChoiceAssessmentPanelFormMixin:
    """
    Shared logic between the AssessmentPanelForms with a "choices" formset.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up choice formset...
        if not self.instance.definition_json:
            self.instance.definition_json = {}
        if "choices" not in self.instance.definition_json:
            self.instance.definition_json["choices"] = []

        if args:
            post_data = args[0]
        else:
            post_data = None

        self._init_formset(post_data)

    @classmethod
    def _choice_formset_class(cls):
        """
        Return the FormSet subclass to use for the `choices` attribute.
        """
        raise NotImplementedError

    def _initial_choices(self):
        """
        Return a list of the initial choices from the instance definition.
        """
        return self.instance.definition_json["choices"]

    def _init_formset(self, post_data=None):
        initial_choices = self._initial_choices()
        choices_class = self._choice_formset_class()
        self.choices = choices_class(
            data=post_data,
            prefix="question-definition",
            initial=initial_choices,
        )

    def is_valid(self):
        choices_valid = self.choices.is_valid()
        if not choices_valid:
            return False
        return super().is_valid()

    def clean(self):
        cleaned_data = super().clean()

        # Record that the choices have changed, in case we need to trigger a re-score.
        if self.choices.has_changed():
            self.changed_data.append("choices")

        # Update the instance definition_json / solution_json
        self._update_instance_json()

        return cleaned_data

    def _update_instance_json(self):
        definition_json = self.instance.definition_json or {}

        # Update the choices
        if self.choices.is_valid():
            new_choices = []
            for choice_data in self.choices.cleaned_data:
                delete = choice_data.pop("DELETE", False)
                if delete:
                    continue

                # Remember choices
                new_choices.append(choice_data)

            definition_json["choices"] = new_choices

        self.instance.definition_json = definition_json

    def save(self, commit=True):
        """
        Take the validated data from the choices formset and build up
        the correct definition_json for the assessment.
        """
        super().save(commit=commit)

        # Re-init formset since it works off a copy of definition_json
        self._init_formset(post_data=None)

        return self.instance


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# POLL
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PollChoiceFormSet = formset_factory(
    BaseChoiceDefinitionForm,
    formset=BaseChoiceFormSet,
    min_num=1,
    max_num=20,
    can_delete=True,
    extra=0,
)


class PollAssessmentPanelForm(ChoiceAssessmentPanelFormMixin, BaseAssessmentPanelForm):
    choices: Optional[BaseFormSet] = None

    class Meta:
        model = Assessment
        fields = (
            BaseAssessmentPanelForm.QUESTION_FIELDS
            + BaseAssessmentPanelForm.OPTIONS_FIELDS
        )

    @classmethod
    def _choice_formset_class(cls):
        """
        Return the FormSet subclass to use for the `choices` attribute.
        """
        return PollChoiceFormSet


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# MULTIPLE CHOICE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class MultipleChoiceAnswerDefinitionForm(BaseChoiceDefinitionForm):
    correct = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-control"})
    )

    class Meta:
        fields = ["text", "choice_key", "correct"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["correct"].widget.attrs["class"] = "form-control"

    def _init_form_helper(self):
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Row(
                Column("choice_key", css_class="col-1"),
                Column("text", css_class="col-9"),
                Column("correct", css_class="col-1"),
                Column(
                    Field("DELETE", css_class="input-small hidden"),
                    HTML(
                        '<button type="button" '
                        'class="btn btn-danger btn-sm btn-remove-choice">'
                        "Delete"
                        "</button>"
                    ),
                    css_class="col-1",
                ),
            )
        )


class BaseMultipleChoiceAnswerFormSet(BaseChoiceFormSet):
    def clean(self):
        """
        Check that at least one selection is marked as correct.
        """
        if any(self.errors):
            return

        super().clean()

        at_least_one_correct = False
        for form in self.forms:
            if form.cleaned_data["correct"]:
                at_least_one_correct = True

        if not at_least_one_correct:
            raise forms.ValidationError(
                "At least one choice must be marked as correct."
            )


MultipleChoiceAnswerFormSet = formset_factory(
    MultipleChoiceAnswerDefinitionForm,
    formset=BaseMultipleChoiceAnswerFormSet,
    min_num=1,
    max_num=20,
    can_delete=True,
    extra=0,
)


class MultipleChoiceAssessmentPanelForm(
    ChoiceAssessmentPanelFormMixin, BaseAssessmentPanelForm
):
    choices: Optional[BaseFormSet] = None

    join_type = forms.ChoiceField(
        choices=[
            ("AND", "AND"),
            ("OR", "OR"),
        ],
        widget=forms.RadioSelect(attrs={"class": "inline-radio"}),
        help_text=(
            "If there are multiple correct options, "
            "'AND' means all are required, "
            "'OR' means at least one is required."
        ),
        initial="AND",  # Set the initial join type
    )

    class Meta:
        model = Assessment
        fields = (
            BaseAssessmentPanelForm.QUESTION_FIELDS
            + ["join_type"]
            + BaseAssessmentPanelForm.OPTIONS_FIELDS
        )

    @classmethod
    def _choice_formset_class(cls):
        """
        Return the FormSet subclass to use for the `choices` attribute.
        """
        return MultipleChoiceAnswerFormSet

    def _initial_choices(self):
        """
        Return a list of the initial choices from the instance definition.
        """
        initial_choices: List[Dict] = copy.deepcopy(super()._initial_choices())
        solution_json = self.instance.solution_json or {}
        correct_choices = solution_json.get("correct_choice_keys", [])
        for choice in initial_choices:
            choice["correct"] = choice["choice_key"] in correct_choices

        return initial_choices

    def _update_instance_json(self):
        # Update the choices with the submitted data.

        definition_json = self.instance.definition_json or {}
        solution_json = self.instance.solution_json or {}

        if self.choices.is_valid():
            new_correct_choice_keys = set()
            join_type = self.cleaned_data["join_type"]
            new_choices = []
            for choice_data in self.choices.cleaned_data:
                delete = choice_data.pop("DELETE", False)
                if delete:
                    continue

                is_correct = choice_data.pop("correct", None)
                # Remember that this was marked correct
                if is_correct:
                    new_correct_choice_keys.add(choice_data["choice_key"])

                # Remember choices
                new_choices.append(choice_data)

            definition_json["choices"] = new_choices
            solution_json = {
                "correct_choice_keys": list(new_correct_choice_keys),
                "join": join_type,
            }

        self.instance.definition_json = definition_json
        self.instance.solution_json = solution_json
