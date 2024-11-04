import logging
from typing import List

from django import template
from django.utils.translation import gettext_lazy as _

from kinesinlms.composer.models import ComposerSettings
from kinesinlms.learning_library.constants import AssessmentType, BlockType
from kinesinlms.sits.constants import SimpleInteractiveToolType

register = template.Library()
logger = logging.getLogger(__name__)


@register.simple_tag(takes_context=True)
def is_wysiwyg_active(context) -> bool:
    """
    Indicates whether WYSIWYG is active or not.
    """
    # Our HTMx method will set the state in the context. If it has, use that
    # Otherwise get directly from the database.
    if "is_wysiwyg_active" in context:
        return getattr(context, "wysiwyg_active", False)
    user = context.request.user
    composer_settings, created = ComposerSettings.objects.get_or_create(user=user)
    return composer_settings.wysiwyg_active


@register.simple_tag
def add_block_button_groups() -> List:
    """

    Get a list of info that will let us write out the different
    "add block" buttons we want to display in the 'Add block' dialog.

    TODO: This is hardcoded for now but should reflect the available blocks.

    """

    groups = [
        {
            "group_name": _("Basic"),
            "buttons": [
                {
                    "name": _(BlockType.HTML_CONTENT.value),
                    "bi_icon_class": "bi bi-list",
                    "description": _("A simple HTML block"),
                    "block_type": BlockType.HTML_CONTENT.name,
                    "block_subtype": None,
                    "block_type_classes": "btn-primary add-block-basic",
                },
                {
                    "name": _(BlockType.VIDEO.value),
                    "bi_icon_class": "bi  bi-person-video",
                    "description": _("A basic video block"),
                    "block_type": BlockType.VIDEO.name,
                    "block_subtype": None,
                    "block_type_classes": "btn-primary add-block-basic",
                },
                {
                    "name": _(BlockType.FILE_RESOURCE.value),
                    "bi_icon_class": "bi bi-file-earmark-arrow-down",
                    "description": _("A simple resource display"),
                    "block_type": BlockType.FILE_RESOURCE.name,
                    "block_subtype": None,
                    "block_type_classes": "btn-primary add-block-basic",
                },
                {
                    "name": _(BlockType.FORUM_TOPIC.value),
                    "bi_icon_class": "bi  bi-person-video",
                    "description": _("A basic forum topic block"),
                    "block_type": BlockType.FORUM_TOPIC.name,
                    "block_subtype": None,
                    "block_type_classes": "btn-primary add-block-basic",
                },
            ],
        },
        {
            "group_name": _("Assessments"),
            "buttons": [
                {
                    "name": _(AssessmentType.LONG_FORM_TEXT.value),
                    "bi_icon_class": "bi bi-card-text",
                    "description": _("Long-form text assessment"),
                    "block_type": BlockType.ASSESSMENT.name,
                    "block_subtype": AssessmentType.LONG_FORM_TEXT.name,
                    "block_type_classes": "btn-info add-block-assessment",
                },
                {
                    "name": _(AssessmentType.MULTIPLE_CHOICE.value),
                    "bi_icon_class": "bi bi-card-checklist",
                    "description": _("Multiple choice assessment"),
                    "block_type": BlockType.ASSESSMENT.name,
                    "block_subtype": AssessmentType.MULTIPLE_CHOICE.name,
                    "block_type_classes": "btn-info add-block-assessment",
                },
                {
                    "name": _(AssessmentType.POLL.value),
                    "bi_icon_class": "bi bi-check2-circle",
                    "description": _("Poll assessment"),
                    "block_type": BlockType.ASSESSMENT.name,
                    "block_subtype": AssessmentType.POLL.name,
                    "block_type_classes": "btn-info add-block-assessment",
                },
                {
                    "name": _(AssessmentType.DONE_INDICATOR.value),
                    "bi_icon_class": "bi bi-check2-square",
                    "description": _(
                        "Simple indicator for when a user has completed a task"
                    ),
                    "block_type": BlockType.ASSESSMENT.name,
                    "block_subtype": AssessmentType.DONE_INDICATOR.name,
                    "block_type_classes": "btn-info add-block-assessment",
                },
            ],
        },
        {
            "group_name": _("Other"),
            "buttons": [
                {
                    "name": _(SimpleInteractiveToolType.DIAGRAM.value),
                    "bi_icon_class": "bi bi-list",
                    "description": _("An interactive diagram block"),
                    "block_type": BlockType.SIMPLE_INTERACTIVE_TOOL.name,
                    "block_subtype": SimpleInteractiveToolType.DIAGRAM.name,
                    "block_type_classes": "btn-success add-block-sit",
                },
                {
                    "name": _(SimpleInteractiveToolType.TABLETOOL.value),
                    "bi_icon_class": "bi  bi-person-video",
                    "description": _("A interactive table block"),
                    "block_type": BlockType.SIMPLE_INTERACTIVE_TOOL.name,
                    "block_subtype": SimpleInteractiveToolType.TABLETOOL.name,
                    "block_type_classes": "btn-success add-block-sit",
                },
                {
                    "name": _(BlockType.SURVEY.value),
                    "bi_icon_class": "bi bi-card-checklist",
                    "description": _("Survey"),
                    "block_type": BlockType.SURVEY.name,
                    "block_type_classes": "btn-danger add-external-survey",
                },
                {
                    "name": _("Notebook"),
                    "bi_icon_class": None,
                    "icon_filename": "jupyter_white.svg",
                    "description": _("Jupyter Notebook"),
                    "block_type": BlockType.JUPYTER_NOTEBOOK.name,
                    "block_type_classes": "btn-danger add-external-tool-view",
                },
                {
                    "name": _(BlockType.EXTERNAL_TOOL_VIEW.value),
                    "bi_icon_class": "bi bi-boxes",
                    "description": _("External tool (LTI)"),
                    "block_type": BlockType.EXTERNAL_TOOL_VIEW.name,
                    "block_type_classes": "btn-danger add-external-tool-view",
                },
            ],
        },
    ]

    return groups
