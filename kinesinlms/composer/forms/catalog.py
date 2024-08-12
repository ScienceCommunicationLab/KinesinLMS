import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_bootstrap5.bootstrap5 import Switch
from django import forms
from tinymce.widgets import TinyMCE

from django.utils.translation import gettext_lazy as _

from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.composer.constants import HTMLEditMode

logger = logging.getLogger(__name__)


#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Basic Forms
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~


class CourseCatalogDescriptionForm(forms.ModelForm):
    overview = forms.CharField(
        widget=TinyMCE(attrs={"cols": 80, "rows": 10}), required=False
    )
    about_content = forms.CharField(
        widget=TinyMCE(attrs={"cols": 80, "rows": 10}), required=False
    )
    sidebar_content = forms.CharField(
        widget=TinyMCE(attrs={"cols": 80, "rows": 30}), required=False
    )

    class Meta:
        model = CourseCatalogDescription
        fields = [
            "visible",
            "title",
            "blurb",
            "overview",
            "sidebar_content",
            "about_content",
            "thumbnail",
            "hex_theme_color",
            "hex_title_color",
            "custom_stylesheet",
            "trailer_video_url",
            "syllabus",
            "effort",
            "duration",
            "features",
            "order",
        ]

    def __init__(self, *args, html_edit_mode=HTMLEditMode.RAW.name, **kwargs):
        super().__init__(*args, **kwargs)

        if html_edit_mode not in [item.name for item in HTMLEditMode]:
            raise ValueError(
                f"html_edit_mode must be one of: {[item.name for item in HTMLEditMode]}"
            )

        self.fields["overview"].help_text += _(
            "This text appears: 1) in the 'Course Overview' "
            "block on the course about page 2)next to the course "
            "thumbnail in the user's dashboard."
        )
        self.helper = FormHelper()
        self.helper.form_id = "course-catalog-description-form"
        self.helper.form_method = "post"
        self.helper.form_action = ""

        self.helper.layout = Layout(
            Switch('visible', css_class='custom-control-input'),
            'title',
            'blurb',
            'overview',
            'sidebar_content',
            'about_content',
            'thumbnail',
            'hex_theme_color',
            'hex_title_color',
            'custom_stylesheet',
            'trailer_video_url',
            'syllabus',
            'effort',
            'duration',
            'features',
            'order',
        )

        # if html_edit_mode == HTMLEditMode.RAW.name:
        #    self.fields["about_content"].widget = forms.Textarea()
        #    self.fields["sidebar_content"].widget = forms.Textarea()
