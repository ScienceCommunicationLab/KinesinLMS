import logging

from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from kinesinlms.learning_library.models import Block, Resource, ResourceType

logger = logging.getLogger(__name__)


class ResourceForm(ModelForm):
    name = forms.CharField(
        max_length=400,
        required=False,
        help_text=_(
            "A name for this resource. This name is used in the admin "
            "interface and in the learning library.",
        ),
    )

    description = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text=_(
            "A short description of the resource. If this is an image, "
            "the description will be used as the alt text."
        ),
    )

    resource_file = forms.FileField(
        label="Select resource file", widget=forms.FileInput()
    )

    class Meta:
        model = Resource
        fields = [
            "name",
            "resource_file",
            "type",
            "description",
        ]

    def __init__(self, *args, block: Block = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.block = block
        self.fields["description"].widget.attrs["style"] = "height: 3rem;"

        # Set initial name if not provided
        if not self.initial.get("name") and self.instance and self.instance.file_name:
            self.initial["name"] = self.instance.file_name

    def clean(self) -> dict:
        cleaned_data = super().clean()
        resource_type = cleaned_data.get("type")

        # Check Jupyter notebook constraint if we have a block
        if self.block and resource_type == ResourceType.JUPYTER_NOTEBOOK.name:
            existing_notebook_query = self.block.resources.filter(
                type=ResourceType.JUPYTER_NOTEBOOK.name
            )

            # If this is an update, exclude the current instance
            if self.instance.pk:
                existing_notebook_query = existing_notebook_query.exclude(
                    pk=self.instance.pk
                )

            if existing_notebook_query.exists():
                self.add_error(
                    "type",
                    "Only one Jupyter notebook resource can be associated with a block.",
                )

        # Validate file extension based on resource type
        resource_file = cleaned_data.get("resource_file")
        if resource_file and resource_type == ResourceType.JUPYTER_NOTEBOOK.name:
            extension = resource_file.name.split(".")[-1].lower()
            if extension != "ipynb":
                self.add_error(
                    "resource_file",
                    "Jupyter notebook resources must have .ipynb extension",
                )

        return cleaned_data

    def save(self, commit=True):
        resource = super().save(commit=commit)

        # If we have a block, create the relationship
        if commit and self.block:
            self.block.resources.add(resource)

        return resource
