import logging

from django import forms
from django.forms import ModelForm
from django.forms.widgets import Select
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


class ResourceSelectorWidget(Select):  
    template_name = "composer/blocks/widgets/resource_selector.html"
    
    def __init__(self, type_filter=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_filter = type_filter
        
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["resources"] = self.choices.queryset
        context["type_filter"] = self.type_filter
        return context

class SelectResourceForBlockResourceForm(forms.Form):
    """
    Select one resource for a BlockResource from a list of
    available resources.
    """

    resource = forms.ModelChoiceField(
        queryset=Resource.objects.all(),
        label=_("Select a resource"),
        help_text=_(
            "Select a resource from the list below to associate with this block."
        ),
        widget=ResourceSelectorWidget(type_filter=None),
    )

    def __init__(self, *args, block: Block = None, type_filter: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_filter = type_filter
        self.block = block

        if type_filter:
            type_filter_name = ResourceType[type_filter].value
            select_msg = _("Select a {type} resource").format(type=type_filter_name)
        else:
            select_msg = _("Select a resource")

        self.fields["resource"].label = select_msg
        # Update the existing widget's type_filter
        self.fields["resource"].widget.type_filter = type_filter

        # Filter the queryset based on type if specified
        queryset = Resource.objects.all()
        if type_filter:
            queryset = queryset.filter(type=type_filter)

        # Exclude resources already associated with this block
        if self.block:
            existing_resource_ids = self.block.resources.values_list("id", flat=True)
            queryset = queryset.exclude(id__in=existing_resource_ids)

        self.fields["resource"].queryset = queryset

    def clean(self):
        cleaned_data = super().clean()
        resource = cleaned_data.get("resource")

        if resource and self.block:
            # Check if this resource type is allowed
            if resource.type == ResourceType.JUPYTER_NOTEBOOK.name:
                existing_notebook = self.block.resources.filter(
                    type=ResourceType.JUPYTER_NOTEBOOK.name
                ).exists()
                if existing_notebook:
                    err_msg = _(
                        "Only one Jupyter notebook resource can be "
                        "associated with a block."
                    )
                    raise forms.ValidationError(err_msg)

        return cleaned_data

    def save(self, commit=True):
        """Create the BlockResource relationship."""
        if not self.block or not self.cleaned_data.get("resource"):
            raise ValueError("Both block and resource are required")

        self.block.resources.add(self.cleaned_data["resource"])
        return self.cleaned_data["resource"]


class JupyterNotebookResourceForm(ResourceForm):
    """
    Extends the default Resource form to provide some fields
    specific to Jupyter notebook resources.

    Args:
        ModelForm (_type_): _description_

    Returns:
        _type_: _description_
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].help_text = _(
            "A name for this Jupyter notebook resource. This name "
            "is used in the admin interface and in the learning library."
        )
        self.fields["resource_file"].label = "Select Jupyter notebook file"
        self.fields["type"].widget = forms.HiddenInput()
        self.fields["type"].initial = ResourceType.JUPYTER_NOTEBOOK.name

    def clean_resource_file(self):
        """Validate that the uploaded file is a Jupyter notebook."""
        resource_file = self.cleaned_data.get("resource_file")
        if resource_file:
            extension = resource_file.name.split(".")[-1].lower()
            if extension != "ipynb":
                raise forms.ValidationError(
                    _("Only Jupyter notebook files (.ipynb) are allowed.")
                )
        return resource_file

    def clean(self) -> dict:
        """
        Validate the form data.

        Returns:
            dict: _description_
        """
        cleaned_data = super().clean()
        return cleaned_data
